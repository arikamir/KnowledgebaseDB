#!/usr/bin/env bash
set -euo pipefail

source_revision=""
baseline_revision=""
output_path=""
missing_baseline=false
rebuild_all=false
recovery=false
recovery_operator=""
platform_approver=""
dry_run=false

fail() {
  printf 'detect-changes: %s\n' "$1" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --source) source_revision="${2:-}"; shift 2 ;;
    --baseline) baseline_revision="${2:-}"; shift 2 ;;
    --missing-baseline) missing_baseline=true; shift ;;
    --output) output_path="${2:-}"; shift 2 ;;
    --rebuild-all) rebuild_all=true; shift ;;
    --recovery) recovery=true; shift ;;
    --recovery-operator) recovery_operator="${2:-}"; shift 2 ;;
    --platform-approver) platform_approver="${2:-}"; shift 2 ;;
    --dry-run) dry_run=true; shift ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[[ -n "$source_revision" ]] || fail "--source is required"
[[ -n "$output_path" ]] || fail "--output is required"
command -v git >/dev/null || fail "git is required"
command -v jq >/dev/null || fail "jq is required"

resolved_source=$(git rev-parse --verify "${source_revision}^{commit}" 2>/dev/null) || fail "source revision is not resolvable"

if [[ "$missing_baseline" == true ]]; then
  [[ -z "$baseline_revision" ]] || fail "--baseline and --missing-baseline are mutually exclusive"
  resolved_baseline=""
else
  [[ "$baseline_revision" =~ ^[0-9a-fA-F]{40}$ ]] || fail "baseline must be a full 40-character Git object ID"
  resolved_baseline=$(git rev-parse --verify "${baseline_revision}^{commit}" 2>/dev/null) || fail "baseline revision is not resolvable"
  [[ "$resolved_baseline" == "$baseline_revision" ]] || fail "baseline must resolve exactly"
  git merge-base --is-ancestor "$resolved_baseline" "$resolved_source" || fail "baseline is not an ancestor of source"
fi

if [[ "$rebuild_all" == true || "$recovery" == true ]]; then
  [[ -n "$recovery_operator" && -n "$platform_approver" ]] || fail "audited rebuild/recovery requires both approvers"
  [[ "$recovery_operator" != "$platform_approver" ]] || fail "recovery operator and platform approver must be distinct"
fi

ui=false
bff=false
core=false
contract_integrity=false
readiness_scenarios=false
performance_profile=false
infrastructure=false
reason_file=$(mktemp "${TMPDIR:-/tmp}/change-plan-reasons.XXXXXX")
changed_file=$(mktemp "${TMPDIR:-/tmp}/change-plan-paths.XXXXXX")
trap 'rm -f "$reason_file" "$changed_file"' EXIT

all_services() {
  ui=true
  bff=true
  core=true
}

all_lanes() {
  contract_integrity=true
  readiness_scenarios=true
  performance_profile=true
  infrastructure=true
}

if [[ "$missing_baseline" == true ]]; then
  all_services
  all_lanes
  printf '%s\n' "missing-baseline" > "$reason_file"
elif [[ "$rebuild_all" == true ]]; then
  all_services
  all_lanes
  printf '%s\n' "audited-rebuild-all" > "$reason_file"
elif [[ "$recovery" == true ]]; then
  all_services
  all_lanes
  printf '%s\n' "audited-recovery" > "$reason_file"
else
  git diff --name-only --diff-filter=ACDMRTUXB "$resolved_baseline" "$resolved_source" > "$changed_file"
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    printf '%s\n' "$path" >> "$reason_file"
    case "$path" in
      specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml)
        ui=true; bff=true ;;
      specs/003-develop-ui/contracts/core-api-v1.openapi.yaml)
        bff=true; core=true ;;
      specs/003-develop-ui/contracts/supported-guidance-topics-v1.yaml)
        all_services ;;
      specs/003-develop-ui/contracts/implementation-readiness-contract.md)
        all_services; all_lanes ;;
      specs/003-develop-ui/requirements-traceability.md)
        all_services; infrastructure=true ;;
      tests/fixtures/readiness-scenario-manifest-v1.yaml)
        all_services; readiness_scenarios=true; infrastructure=true ;;
      tests/performance/performance-profile-v1.json|tests/performance/interaction-performance-profile-v1.json|tests/performance/interaction-performance-fixtures-v1.json)
        all_services; performance_profile=true ;;
      .agents/skills/provision-azure-app-resources/*|.agents/skills/teardown-azure-app-resources/*)
        all_services; infrastructure=true ;;
      specs/003-develop-ui/contracts/*)
        all_services ;;
      ui/*)
        ui=true ;;
      bff/*)
        bff=true ;;
      src/*|alembic/*|pyproject.toml)
        core=true ;;
      scripts/ci/*|Dockerfile|compose.yaml|Jenkinsfile|.github/*)
        all_services ;;
      infra/*|deploy/*)
        all_services; infrastructure=true ;;
      docs/*|README.md|specs/*/quickstart.md|specs/*/research.md|specs/*/plan.md|specs/*/tasks.md)
        : ;;
      tests/*)
        core=true ;;
      *)
        all_services; infrastructure=true ;;
    esac
  done < "$changed_file"
fi

# Every ref runs the canonical authored-contract/catalog/traceability gate.
contract_integrity=true

reasons=$(jq -R -s 'split("\n") | map(select(length > 0)) | unique | sort' "$reason_file")
mkdir -p "$(dirname "$output_path")"
temporary_output=$(mktemp "$(dirname "$output_path")/.change-plan.XXXXXX")
trap 'rm -f "$reason_file" "$changed_file" "$temporary_output"' EXIT

if [[ "$missing_baseline" == true ]]; then
  baseline_args=(--argjson baseline null)
else
  baseline_args=(--arg baseline "$resolved_baseline")
fi

jq -n \
  --arg source "$resolved_source" \
  "${baseline_args[@]}" \
  --argjson ui "$ui" --argjson bff "$bff" --argjson core "$core" \
  --argjson contract "$contract_integrity" \
  --argjson readiness "$readiness_scenarios" \
  --argjson performance "$performance_profile" \
  --argjson infrastructure "$infrastructure" \
  --argjson dryRun "$dry_run" \
  --argjson reason "$reasons" \
  '{
    sourceRevision: $source,
    baselineRevision: $baseline,
    services: {ui: $ui, bff: $bff, core: $core},
    validationLanes: {
      contractIntegrity: $contract,
      readinessScenarios: $readiness,
      performanceProfile: $performance,
      infrastructure: $infrastructure
    },
    dryRun: $dryRun,
    reason: $reason
  }' > "$temporary_output"

chmod 0444 "$temporary_output"
mv -f "$temporary_output" "$output_path"
printf '%s\n' "$output_path"
