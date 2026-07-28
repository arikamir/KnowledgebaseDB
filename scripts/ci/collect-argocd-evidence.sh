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
AUTOMATED_REVIEW_EVIDENCE=""
APPROVED_REVIEWERS="${AI_REVIEW_APPROVED_LOGINS:-chatgpt-codex-connector[bot]}"
EXPECTED_REVIEW_PR=""
EXPECTED_REVIEW_HEAD=""
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
MIGRATION_JOB=""
MIGRATION_LOG_OUTPUT=""

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
    --automated-review-evidence) AUTOMATED_REVIEW_EVIDENCE="${2:-}"; shift 2 ;;
    --review-pull-request) EXPECTED_REVIEW_PR="${2:-}"; shift 2 ;;
    --review-head-revision) EXPECTED_REVIEW_HEAD="${2:-}"; shift 2 ;;
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
    --migration-job) MIGRATION_JOB="${2:-}"; shift 2 ;;
    --migration-log-output) MIGRATION_LOG_OUTPUT="${2:-}"; shift 2 ;;
    *) fail "unknown argument: $1" ;;
  esac
done
[[ -f "$RELEASE" && -n "$OUTPUT" ]] || fail "--release and --output are required"
if [[ "$MIGRATION_JOB" == "not-created" ]]; then
  [[ "$SYNC_STATUS" != "Synced" ]] ||
    fail "--migration-job not-created is valid only when sync did not succeed"
  MIGRATION_JOB=""
elif [[ ! "$MIGRATION_JOB" =~ ^core-migration-[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]]; then
  fail "--migration-job must identify the retained Argo migration Job or not-created"
fi
[[ -n "$MIGRATION_LOG_OUTPUT" && "$MIGRATION_LOG_OUTPUT" != "$OUTPUT" ]] ||
  fail "--migration-log-output must be distinct from --output"
[[ -f "$AUTOMATED_REVIEW_EVIDENCE" ]] || fail "--automated-review-evidence must be a receipt produced by the current-head gate"
[[ "$EXPECTED_REVIEW_PR" =~ ^[1-9][0-9]*$ ]] || fail "--review-pull-request must identify the release or rollback pull request"
[[ "$EXPECTED_REVIEW_HEAD" =~ ^[0-9a-f]{40}$ ]] || fail "--review-head-revision must identify the independently recorded reviewed head"
[[ "$ACTOR_TYPE" == automation || "$ACTOR_TYPE" == human ]] || fail "actor type is invalid"
[[ "$EVENT_TYPE" == release || "$EVENT_TYPE" == sync || "$EVENT_TYPE" == rollback ]] || fail "event type is invalid"
command -v gh >/dev/null 2>&1 || fail "gh CLI is required to authenticate automated review evidence"
if [[ -n "$MIGRATION_JOB" ]]; then
  command -v kubectl >/dev/null 2>&1 || fail "kubectl is required to authenticate migration evidence"
fi
if ! jq -e --arg repository "$REPOSITORY" --arg approvedReviewers "$APPROVED_REVIEWERS" \
  --argjson expectedPullRequest "$EXPECTED_REVIEW_PR" --arg expectedHead "$EXPECTED_REVIEW_HEAD" '
  ($approvedReviewers | split(",")) as $approved |
  keys == ["headRevision","observedAt","proof","proofCommentId","pullRequest","repository","reviewer","schemaVersion","status","statusCheck"] and
  .schemaVersion == 1 and .repository == $repository and
  .pullRequest == $expectedPullRequest and
  (.proofCommentId | type == "number" and . > 0) and
  .headRevision == $expectedHead and
  (.reviewer | type == "string" and length > 0) and
  (.reviewer as $reviewer | $approved | index($reviewer) != null) and
  .status == "passed" and .statusCheck == "ai/review" and
  (.proof == "approved-review" or .proof == "no-findings-reaction" or .proof == "no-findings-comment") and
  (.observedAt | type == "string" and length > 0)
' "$AUTOMATED_REVIEW_EVIDENCE" >/dev/null; then
  fail "automated review evidence is not a valid successful gate receipt for this repository"
fi
AUTOMATED_REVIEWER="$(jq -r '.reviewer' "$AUTOMATED_REVIEW_EVIDENCE")"
AUTOMATED_REVIEW_CHECK="$(jq -r '.statusCheck' "$AUTOMATED_REVIEW_EVIDENCE")"
AUTOMATED_REVIEW_OBSERVED_AT="$(jq -r '.observedAt' "$AUTOMATED_REVIEW_EVIDENCE")"
AUTOMATED_REVIEW_HEAD="$(jq -r '.headRevision' "$AUTOMATED_REVIEW_EVIDENCE")"
AUTOMATED_REVIEW_PR="$(jq -r '.pullRequest' "$AUTOMATED_REVIEW_EVIDENCE")"
AUTOMATED_REVIEW_PROOF="$(jq -r '.proof' "$AUTOMATED_REVIEW_EVIDENCE")"
AUTOMATED_REVIEW_COMMENT_ID="$(jq -r '.proofCommentId' "$AUTOMATED_REVIEW_EVIDENCE")"

CURRENT_REVIEW_HEAD="$(gh api "repos/$REPOSITORY/pulls/$EXPECTED_REVIEW_PR" --jq '.head.sha')" ||
  fail "unable to authenticate the reviewed pull-request head"
[[ "$CURRENT_REVIEW_HEAD" == "$EXPECTED_REVIEW_HEAD" ]] ||
  fail "authenticated pull-request head does not match the retained review scope"
STATUS_STATE="$(gh api "repos/$REPOSITORY/commits/$EXPECTED_REVIEW_HEAD/status" --jq \
  '.statuses | map(select(.context == "ai/review")) | first | .state // empty')" ||
  fail "unable to authenticate the automated-review status"
[[ "$STATUS_STATE" == "success" ]] ||
  fail "authenticated ai/review status is not successful"

if [[ "$AUTOMATED_REVIEW_PROOF" == "approved-review" ]]; then
  AUTHENTICATED_REVIEWER="$(gh api --paginate --slurp "repos/$REPOSITORY/pulls/$EXPECTED_REVIEW_PR/reviews?per_page=100" | jq -r \
    --arg approvedReviewers "$APPROVED_REVIEWERS" --arg head "$EXPECTED_REVIEW_HEAD" \
    '($approvedReviewers | split(",")) as $approved | [.[][] | select((.user.login as $login | $approved | index($login)) != null and .commit_id == $head and (.state == "COMMENTED" or .state == "APPROVED" or .state == "CHANGES_REQUESTED" or .state == "DISMISSED")) | {reviewer:.user.login,state}] | last | select(.state == "APPROVED") | .reviewer // empty')"
elif [[ "$AUTOMATED_REVIEW_PROOF" == "no-findings-reaction" ]]; then
  EXPECTED_MARKER="@codex review

<!-- ai-review-head:$EXPECTED_REVIEW_HEAD -->"
  COMMENT_BODY="$(gh api "repos/$REPOSITORY/issues/comments/$AUTOMATED_REVIEW_COMMENT_ID" --jq '.body')" ||
    fail "unable to authenticate the automated-review request comment"
  [[ "$COMMENT_BODY" == "$EXPECTED_MARKER" ]] ||
    fail "authenticated review request does not match the retained head"
  AUTHENTICATED_REVIEWER="$(gh api --paginate --slurp "repos/$REPOSITORY/issues/comments/$AUTOMATED_REVIEW_COMMENT_ID/reactions?per_page=100" | jq -r \
    --arg approvedReviewers "$APPROVED_REVIEWERS" \
    '($approvedReviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
else
  RESULT_COMMENT="$(gh api "repos/$REPOSITORY/issues/comments/$AUTOMATED_REVIEW_COMMENT_ID")" ||
    fail "unable to authenticate the no-findings result comment"
  RESULT_COMMENT_REVIEWER="$(jq -r '.user.login' <<<"$RESULT_COMMENT")"
  RESULT_COMMENT_BODY="$(jq -r '.body' <<<"$RESULT_COMMENT")"
  ISSUE_REACTION_REVIEWER="$(gh api --paginate --slurp "repos/$REPOSITORY/issues/$EXPECTED_REVIEW_PR/reactions?per_page=100" | jq -r \
    --arg approvedReviewers "$APPROVED_REVIEWERS" \
    '($approvedReviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
  if [[ "$RESULT_COMMENT_REVIEWER" == "$ISSUE_REACTION_REVIEWER" &&
        "$RESULT_COMMENT_BODY" == *"Codex Review: Didn't find any major issues."* &&
        "$RESULT_COMMENT_BODY" == *"**Reviewed commit:** \`${EXPECTED_REVIEW_HEAD:0:10}\`"* ]]; then
    AUTHENTICATED_REVIEWER="$RESULT_COMMENT_REVIEWER"
  else
    AUTHENTICATED_REVIEWER=""
  fi
fi
[[ "$AUTHENTICATED_REVIEWER" == "$AUTOMATED_REVIEWER" ]] ||
  fail "GitHub does not authenticate the reviewer and proof in the gate receipt"
if [[ "$ACTOR_TYPE" == human ]]; then
  [[ -n "$HUMAN_TENANT" && -n "$HUMAN_SUBJECT" ]] || fail "human evidence requires Entra tenant and subject"
fi
if [[ ! "$DESIRED_STATE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  DESIRED_STATE_REVISION="$(jq -r '.sourceRevision' "$RELEASE")"
fi

EXPECTED_CORE_IMAGE="$(jq -r '.services.core.image' "$RELEASE")"
EXPECTED_SOURCE_REVISION="$(jq -r '.sourceRevision' "$RELEASE")"
MIGRATION_STATUS="not-created"
if [[ -n "$MIGRATION_JOB" ]]; then
  MIGRATION_REASON="migration Job was not created or is no longer observable"
else
  MIGRATION_REASON="migration Job was not created"
fi
MIGRATION_LOGS=""
if [[ -n "$MIGRATION_JOB" ]] &&
    MIGRATION_JOB_JSON="$(kubectl -n career-migrations get job "$MIGRATION_JOB" -o json 2>/dev/null)"; then
  if ! jq -e --arg name "$MIGRATION_JOB" --arg image "$EXPECTED_CORE_IMAGE" \
      --arg revision "$EXPECTED_SOURCE_REVISION" '
    .metadata.name == $name and
    .metadata.namespace == "career-migrations" and
    .metadata.annotations["argocd.argoproj.io/hook"] == "PreSync" and
    .metadata.annotations["gitops.knowledgebase.io/source-revision"] == $revision and
    (.spec.template.spec.containers | length) == 1 and
    .spec.template.spec.containers[0].name == "core-migration" and
    .spec.template.spec.containers[0].image == $image and
    ([.spec.template.spec.containers[0].env[]? | select(.name == "MIGRATION_TARGET") | .value] == ["009_merge_learning_progress"])
  ' <<<"$MIGRATION_JOB_JSON" >/dev/null; then
    fail "migration Job is not an authenticated hook for this release"
  fi
  if jq -e 'any(.status.conditions[]?; .type == "Failed" and .status == "True")' \
      <<<"$MIGRATION_JOB_JSON" >/dev/null; then
    MIGRATION_STATUS="failed"
    MIGRATION_REASON="migration Job reported a failed terminal condition"
  elif jq -e 'any(.status.conditions[]?; .type == "Complete" and .status == "True")' \
      <<<"$MIGRATION_JOB_JSON" >/dev/null; then
    MIGRATION_STATUS="succeeded"
    MIGRATION_REASON="migration Job completed"
  else
    MIGRATION_STATUS="incomplete"
    MIGRATION_REASON="migration Job did not reach a terminal condition"
  fi
  MIGRATION_LOGS="$(kubectl -n career-migrations logs "job/$MIGRATION_JOB" -c core-migration 2>/dev/null || true)"
fi
if [[ "$SYNC_STATUS" == "Synced" && "$MIGRATION_STATUS" != "succeeded" ]]; then
  fail "a successful sync requires a completed migration Job"
fi
MIGRATION_BEFORE="$(sed -n 's/^MIGRATION_BEFORE_HEADS=//p' <<<"$MIGRATION_LOGS" | tail -1)"
MIGRATION_AFTER="$(sed -n 's/^MIGRATION_AFTER_HEADS=//p' <<<"$MIGRATION_LOGS" | tail -1)"
if [[ -n "$MIGRATION_BEFORE" && ! "$MIGRATION_BEFORE" =~ ^[a-z0-9_]+(,[a-z0-9_]+)*$ ]]; then
  fail "migration before-head evidence is malformed"
fi
if [[ -n "$MIGRATION_AFTER" && "$MIGRATION_AFTER" != "009_merge_learning_progress" ]]; then
  fail "migration after-head evidence is malformed"
fi
if [[ "$MIGRATION_STATUS" == "succeeded" ]]; then
  [[ "$MIGRATION_BEFORE" =~ ^[a-z0-9_]+(,[a-z0-9_]+)*$ ]] ||
    fail "successful migration before-head evidence is missing"
  [[ "$MIGRATION_AFTER" == "009_merge_learning_progress" ]] ||
    fail "migration did not reach the approved target"
fi
mkdir -p "$(dirname "$MIGRATION_LOG_OUTPUT")"
umask 077
{
  printf 'MIGRATION_STATUS=%s\n' "$MIGRATION_STATUS"
  [[ -z "$MIGRATION_BEFORE" ]] || printf 'MIGRATION_BEFORE_HEADS=%s\n' "$MIGRATION_BEFORE"
  [[ -z "$MIGRATION_AFTER" ]] || printf 'MIGRATION_AFTER_HEADS=%s\n' "$MIGRATION_AFTER"
  printf 'MIGRATION_SAFE_REASON=%s\n' "$MIGRATION_REASON"
} > "$MIGRATION_LOG_OUTPUT"
if command -v sha256sum >/dev/null 2>&1; then
  MIGRATION_LOG_SHA256="$(sha256sum "$MIGRATION_LOG_OUTPUT" | awk '{print $1}')"
else
  MIGRATION_LOG_SHA256="$(shasum -a 256 "$MIGRATION_LOG_OUTPUT" | awk '{print $1}')"
fi

base="$(jq -c --arg observed "$OBSERVED_AT" --arg revision "$DESIRED_STATE_REVISION" \
  --arg repository "$REPOSITORY" --arg branch "$BRANCH" --arg status "$SYNC_STATUS" --arg health "$HEALTH" \
  --arg reviewer "$AUTOMATED_REVIEWER" --arg reviewCheck "$AUTOMATED_REVIEW_CHECK" --arg reviewObserved "$AUTOMATED_REVIEW_OBSERVED_AT" \
  --arg reviewHead "$AUTOMATED_REVIEW_HEAD" --argjson reviewPr "$AUTOMATED_REVIEW_PR" --arg reviewProof "$AUTOMATED_REVIEW_PROOF" \
  --arg readiness "$READINESS_STATUS" --arg event "$EVENT_TYPE" --arg migrationJob "$MIGRATION_JOB" \
  --arg migrationImage "$EXPECTED_CORE_IMAGE" --arg migrationTarget "009_merge_learning_progress" \
  --arg migrationStatus "$MIGRATION_STATUS" --arg migrationReason "$MIGRATION_REASON" \
  --arg migrationBefore "$MIGRATION_BEFORE" --arg migrationAfter "$MIGRATION_AFTER" \
  --arg migrationLog "$MIGRATION_LOG_OUTPUT" --arg migrationLogSha256 "$MIGRATION_LOG_SHA256" \
  '{schemaVersion:3,environment:"nonprod",ciRunId:.ciRun.id,sourceTag:.sourceTag,releaseVersion:.releaseVersion,sourceRevision:.sourceRevision,desiredStateRevision:$revision,applicationName:"career-agent-nonprod",repository:$repository,branch:$branch,actorType:"automation",eventType:$event,automationIdentity:"",imageDigests:{ui:.services.ui.image,bff:.services.bff.image,core:.services.core.image},automatedReview:{reviewer:$reviewer,status:"passed",statusCheck:$reviewCheck,headRevision:$reviewHead,pullRequest:$reviewPr,proof:$reviewProof,observedAt:$reviewObserved},validationEvidence:.validationEvidence,readiness:{status:$readiness,observedAt:$observed},migration:{jobName:(if ($migrationJob|length) == 0 then null else $migrationJob end),namespace:"career-migrations",status:$migrationStatus,safeReason:$migrationReason,image:$migrationImage,target:$migrationTarget,beforeHeads:(if ($migrationBefore|length) == 0 then [] else ($migrationBefore|split(",")) end),afterHeads:(if ($migrationAfter|length) == 0 then [] else ($migrationAfter|split(",")) end),logs:{path:$migrationLog,sha256:$migrationLogSha256},observedAt:$observed},sync:{status:$status,health:$health,observedAt:$observed},timing:{mergedAt:$observed,syncStartedAt:$observed}}' "$RELEASE")"

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
