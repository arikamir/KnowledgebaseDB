#!/usr/bin/env bash
set -euo pipefail

RELEASE=""
OUTPUT=""
EVENT_TYPE="release"
ACTOR_TYPE="automation"
SYNC_STATUS="Synced"
HEALTH="Healthy"
AUTOMATION_IDENTITY="github-actions/application-release"
DESIRED_STATE_REVISION=""
REPOSITORY="${GITHUB_REPOSITORY:-arikamir/KnowledgebaseDB}"
BRANCH="${GITHUB_REF_NAME:-main}"
AUTOMATED_REVIEWER="chatgpt-codex-connector[bot]"
AUTOMATED_REVIEW_STATUS="passed"
AUTOMATED_REVIEW_CHECK="ai/review"
READINESS_STATUS="ready"
OBSERVED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HUMAN_TENANT=""
HUMAN_SUBJECT=""
HUMAN_ROLE="application-release"
HUMAN_AUTH="passed"
ROLLBACK_FROM=""
ROLLBACK_TO=""
ROLLBACK_REASON=""
ROLLBACK_ACTOR=""
ROLLBACK_APPROVAL="passed"
ROLLBACK_OUTCOME="reconciled"

fail() { printf 'argocd evidence: %s\n' "$1" >&2; exit 2; }
while (($#)); do
  case "$1" in
    --release) RELEASE="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    --event-type) EVENT_TYPE="${2:-}"; shift 2 ;;
    --actor-type) ACTOR_TYPE="${2:-}"; shift 2 ;;
    --sync-status) SYNC_STATUS="${2:-}"; shift 2 ;;
    --health) HEALTH="${2:-}"; shift 2 ;;
    --automation-identity) AUTOMATION_IDENTITY="${2:-}"; shift 2 ;;
    --desired-state-revision) DESIRED_STATE_REVISION="${2:-}"; shift 2 ;;
    --repository) REPOSITORY="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --automated-reviewer) AUTOMATED_REVIEWER="${2:-}"; shift 2 ;;
    --automated-review-status) AUTOMATED_REVIEW_STATUS="${2:-}"; shift 2 ;;
    --automated-review-check) AUTOMATED_REVIEW_CHECK="${2:-}"; shift 2 ;;
    --readiness-status) READINESS_STATUS="${2:-}"; shift 2 ;;
    --human-tenant) HUMAN_TENANT="${2:-}"; shift 2 ;;
    --human-subject) HUMAN_SUBJECT="${2:-}"; shift 2 ;;
    --human-role) HUMAN_ROLE="${2:-}"; shift 2 ;;
    --human-authentication) HUMAN_AUTH="${2:-}"; shift 2 ;;
    --rollback-from) ROLLBACK_FROM="${2:-}"; shift 2 ;;
    --rollback-to) ROLLBACK_TO="${2:-}"; shift 2 ;;
    --rollback-reason) ROLLBACK_REASON="${2:-}"; shift 2 ;;
    --rollback-actor) ROLLBACK_ACTOR="${2:-}"; shift 2 ;;
    --rollback-approval) ROLLBACK_APPROVAL="${2:-}"; shift 2 ;;
    --rollback-outcome) ROLLBACK_OUTCOME="${2:-}"; shift 2 ;;
    *) fail "unknown argument: $1" ;;
  esac
done
[[ -f "$RELEASE" && -n "$OUTPUT" ]] || fail "--release and --output are required"
[[ "$ACTOR_TYPE" == automation || "$ACTOR_TYPE" == human ]] || fail "actor type is invalid"
[[ "$EVENT_TYPE" == release || "$EVENT_TYPE" == sync || "$EVENT_TYPE" == rollback ]] || fail "event type is invalid"
if [[ "$ACTOR_TYPE" == human ]]; then
  [[ -n "$HUMAN_TENANT" && -n "$HUMAN_SUBJECT" ]] || fail "human evidence requires Entra tenant and subject"
fi
if [[ ! "$DESIRED_STATE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  DESIRED_STATE_REVISION="$(jq -r '.sourceRevision' "$RELEASE")"
fi

base="$(jq -c --arg observed "$OBSERVED_AT" --arg revision "$DESIRED_STATE_REVISION" \
  --arg repository "$REPOSITORY" --arg branch "$BRANCH" --arg status "$SYNC_STATUS" --arg health "$HEALTH" \
  --arg reviewer "$AUTOMATED_REVIEWER" --arg reviewStatus "$AUTOMATED_REVIEW_STATUS" --arg reviewCheck "$AUTOMATED_REVIEW_CHECK" --arg readiness "$READINESS_STATUS" --arg event "$EVENT_TYPE" \
  '{schemaVersion:2,environment:"nonprod",ciRunId:.ciRun.id,sourceTag:.sourceTag,releaseVersion:.releaseVersion,sourceRevision:.sourceRevision,desiredStateRevision:$revision,applicationName:"career-agent-nonprod",repository:$repository,branch:$branch,actorType:"automation",eventType:$event,automationIdentity:"",imageDigests:{ui:.services.ui.image,bff:.services.bff.image,core:.services.core.image},automatedReview:{reviewer:$reviewer,status:$reviewStatus,statusCheck:$reviewCheck,observedAt:$observed},validationEvidence:.validationEvidence,readiness:{status:$readiness,observedAt:$observed},sync:{status:$status,health:$health,observedAt:$observed},timing:{mergedAt:$observed,syncStartedAt:$observed}}' "$RELEASE")"

if [[ "$ACTOR_TYPE" == human ]]; then
  base="$(jq --arg tenant "$HUMAN_TENANT" --arg subject "$HUMAN_SUBJECT" --arg role "$HUMAN_ROLE" --arg auth "$HUMAN_AUTH" --arg observed "$OBSERVED_AT" \
    '.actorType="human" | del(.automationIdentity) | .humanAction={tenant:$tenant,subject:$subject,role:$role,authentication:$auth,timestamp:$observed}' <<<"$base")"
else
  base="$(jq --arg identity "$AUTOMATION_IDENTITY" '.automationIdentity=$identity' <<<"$base")"
fi

if [[ "$EVENT_TYPE" == rollback ]]; then
  [[ "$ROLLBACK_FROM" =~ ^[0-9a-f]{40}$ && "$ROLLBACK_TO" =~ ^[0-9a-f]{40}$ ]] || fail "rollback source and target revisions are required"
  base="$(jq --arg from "$ROLLBACK_FROM" --arg to "$ROLLBACK_TO" --arg reason "$ROLLBACK_REASON" --arg actor "$ROLLBACK_ACTOR" --arg approval "$ROLLBACK_APPROVAL" --arg outcome "$ROLLBACK_OUTCOME" --arg observed "$OBSERVED_AT" \
    '.eventType="rollback" | .rollback={fromRevision:$from,toRevision:$to,reason:$reason,actor:$actor,approvalResult:$approval,outcome:$outcome,recordedAt:$observed}' <<<"$base")"
fi

if [[ "$SYNC_STATUS" == OutOfSync || "$SYNC_STATUS" == Unknown || "$SYNC_STATUS" == Failed ]]; then
  base="$(jq --arg observed "$OBSERVED_AT" '.sync += {affectedService:(env.GITOPS_AFFECTED_SERVICE // "unknown"),reason:(env.GITOPS_FAILURE_REASON // "reconciliation did not reach the desired state"),nextAction:(env.GITOPS_NEXT_ACTION // "inspect Argo CD events and revert through a reviewed Git change")} | .timing += {failedAt:$observed,diagnosedAt:$observed,nextActionVisibleAt:$observed,failureDiagnosisSeconds:0}' <<<"$base")"
fi

if jq -e 'tostring | test("(?i)(password|secret|token|private[_-]?key|client[_-]?secret|kubeconfig|connectionstring)")' <<<"$base" >/dev/null; then
  fail "credential-shaped content is forbidden in evidence"
fi
mkdir -p "$(dirname "$OUTPUT")"
printf '%s\n' "$base" | jq . > "$OUTPUT"
printf 'argocd evidence: wrote %s\n' "$OUTPUT"
