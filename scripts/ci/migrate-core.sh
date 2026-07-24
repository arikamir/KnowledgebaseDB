#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAMESPACE="career-migrations"
TEMPLATE="$ROOT/deploy/k8s/base/migration/job-template.yaml"
CORE_IMAGE_REPOSITORY="${CORE_IMAGE_REPOSITORY:?CORE_IMAGE_REPOSITORY is required}"
CORE_MIGRATION_IMAGE="${CORE_MIGRATION_IMAGE:?CORE_MIGRATION_IMAGE is required}"
MIGRATION_TARGET="${MIGRATION_TARGET:?MIGRATION_TARGET is required}"
MIGRATION_CLASSIFICATION="${MIGRATION_CLASSIFICATION:?MIGRATION_CLASSIFICATION is required}"
MIGRATION_DATABASE_URL="${MIGRATION_DATABASE_URL:?MIGRATION_DATABASE_URL is required}"
MIGRATION_EVIDENCE_DIR="${MIGRATION_EVIDENCE_DIR:?MIGRATION_EVIDENCE_DIR is required}"
MUTATION_JOURNAL="${MUTATION_JOURNAL:?MUTATION_JOURNAL is required}"
BUILD_ID="${BUILD_ID:-manual}"
failure_reason=""

fail() {
  failure_reason="$1"
  printf 'core migration rejected: %s\n' "$1" >&2
  exit 1
}

[[ "$MIGRATION_CLASSIFICATION" == "expand-only" ]] || fail "classification must be expand-only"
case "$MIGRATION_TARGET" in
  learning@head|progress@head|009_merge_learning_progress) ;;
  *) fail "target is not approved" ;;
esac
[[ "$CORE_IMAGE_REPOSITORY" =~ ^[a-z0-9.-]+/[a-z0-9._/-]+$ ]] || fail "repository is malformed"
image_prefix="${CORE_IMAGE_REPOSITORY}@sha256:"
[[ "$CORE_MIGRATION_IMAGE" == "$image_prefix"* ]] ||
  fail "image must be an immutable digest in the approved repository"
image_digest="${CORE_MIGRATION_IMAGE#"$image_prefix"}"
[[ "$image_digest" =~ ^[0-9a-f]{64}$ ]] || fail "image digest must be 64 lowercase hexadecimal characters"
[[ "$MIGRATION_DATABASE_URL" =~ ^postgresql\+psycopg://[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+(:[0-9]+)?/[A-Za-z0-9_-]+$ ]] ||
  fail "database URL must be a passwordless PostgreSQL Entra endpoint"
[[ "$BUILD_ID" =~ ^[A-Za-z0-9._-]+$ ]] || fail "build ID is malformed"
command -v kubectl >/dev/null 2>&1 || fail "kubectl is required"
command -v jq >/dev/null 2>&1 || fail "jq is required"

safe_build_id="$(printf '%s' "$BUILD_ID" | tr '[:upper:]_.' '[:lower:]--' | sed 's/[^a-z0-9-]/-/g; s/^-*//; s/-*$//' | cut -c1-40 | sed 's/-*$//')"
[[ -n "$safe_build_id" ]] || fail "build ID has no Kubernetes-safe characters"
job_name="core-migration-${safe_build_id}"
work_dir="$(mktemp -d)"
job_file="$work_dir/job.yaml"
log_file="$MIGRATION_EVIDENCE_DIR/migration.log"
evidence_file="$MIGRATION_EVIDENCE_DIR/migration-evidence.json"
created=false
cleanup_state="not-created"
evidence_active=false
mkdir -p "$MIGRATION_EVIDENCE_DIR" "$(dirname "$MUTATION_JOURNAL")"

finalize() {
  exit_code=$?
  trap - EXIT
  if [[ "$created" == true ]]; then
    if kubectl delete job "$job_name" -n "$NAMESPACE" --wait=true --ignore-not-found=true >/dev/null; then
      cleanup_state="deleted"
    else
      cleanup_state="delete-failed"
    fi
  fi
  if ((exit_code != 0)) && [[ "$evidence_active" == true ]]; then
    jq -n \
      --arg buildId "$BUILD_ID" \
      --arg namespace "$NAMESPACE" \
      --arg serviceAccount "core-migrator" \
      --arg image "$CORE_MIGRATION_IMAGE" \
      --arg target "$MIGRATION_TARGET" \
      --arg reason "${failure_reason:-unexpected-command-failure}" \
      --arg cleanup "$cleanup_state" \
      '{schemaVersion:1,buildId:$buildId,status:"failed",namespace:$namespace,serviceAccount:$serviceAccount,databaseRole:"core_migrator_ddl_backfill",image:$image,target:$target,safeReason:$reason,timeoutSeconds:900,backoffLimit:1,cleanup:$cleanup}' \
      > "$evidence_file"
  fi
  rm -rf "$work_dir"
  exit "$exit_code"
}
trap finalize EXIT

sed \
  -e "s|\${BUILD_ID}|${safe_build_id}|g" \
  -e "s|\${CORE_MIGRATION_IMAGE}|${CORE_MIGRATION_IMAGE}|g" \
  -e "s|\${MIGRATION_TARGET}|${MIGRATION_TARGET}|g" \
  -e "s|\${MIGRATION_DATABASE_URL}|${MIGRATION_DATABASE_URL}|g" \
  "$TEMPLATE" > "$job_file"

evidence_active=true
kubectl create -f "$job_file" >/dev/null
created=true

deadline=$((SECONDS + 900))
phase=""
while ((SECONDS < deadline)); do
  phase="$(kubectl get job "$job_name" -n "$NAMESPACE" -o jsonpath='{.status.conditions[-1:].type}' 2>/dev/null || true)"
  case "$phase" in
    Complete) break ;;
    Failed) fail "migration Job failed" ;;
  esac
  sleep 2
done
[[ "$phase" == "Complete" ]] || fail "migration Job exceeded its 900-second deadline"

pod_name="$(kubectl get pods -n "$NAMESPACE" -l "job-name=$job_name" -o jsonpath='{.items[0].metadata.name}')"
[[ -n "$pod_name" ]] || fail "migration Pod was not found"
kubectl logs "$pod_name" -n "$NAMESPACE" > "$log_file"

before_heads="$(sed -n 's/^MIGRATION_BEFORE_HEADS=//p' "$log_file" | tail -1)"
after_heads="$(sed -n 's/^MIGRATION_AFTER_HEADS=//p' "$log_file" | tail -1)"
[[ -n "$before_heads" && -n "$after_heads" ]] || fail "migration head evidence is missing"

kubectl delete job "$job_name" -n "$NAMESPACE" --wait=true --ignore-not-found=true >/dev/null
created=false
cleanup_state="deleted"
log_sha256="$(shasum -a 256 "$log_file" | awk '{print $1}')"

jq -n \
  --arg buildId "$BUILD_ID" \
  --arg namespace "$NAMESPACE" \
  --arg serviceAccount "core-migrator" \
  --arg image "$CORE_MIGRATION_IMAGE" \
  --arg target "$MIGRATION_TARGET" \
  --arg before "$before_heads" \
  --arg after "$after_heads" \
  --arg logs "$log_file" \
  --arg logSha256 "$log_sha256" \
  --arg cleanup "$cleanup_state" \
  '{schemaVersion:1,buildId:$buildId,status:"succeeded",admission:"accepted",namespace:$namespace,serviceAccount:$serviceAccount,databaseRole:"core_migrator_ddl_backfill",image:$image,target:$target,beforeHeads:($before|split(",")),afterHeads:($after|split(",")),logs:{path:$logs,sha256:$logSha256},timeoutSeconds:900,backoffLimit:1,cleanup:$cleanup}' \
  > "$evidence_file"

journal_schema='{"reversible":false,"compensation":null}'
jq -cn \
  --argjson base "$journal_schema" \
  --arg buildId "$BUILD_ID" \
  --arg image "$CORE_MIGRATION_IMAGE" \
  --arg target "$MIGRATION_TARGET" \
  --arg before "$before_heads" \
  --arg after "$after_heads" \
  '$base + {type:"core-schema-migration",buildId:$buildId,image:$image,target:$target,beforeHeads:($before|split(",")),afterHeads:($after|split(",")),status:"succeeded"}' \
  >> "$MUTATION_JOURNAL"

printf 'core migration succeeded: %s\n' "$MIGRATION_TARGET"
