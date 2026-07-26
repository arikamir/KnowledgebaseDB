#!/usr/bin/env bash
set -euo pipefail

repository="${1:-${GITHUB_REPOSITORY:-}}"
pull_request="${2:-${PULL_REQUEST_NUMBER:-}}"
check_name="${AI_REVIEW_CHECK_NAME:-ai/review}"
approved_reviewers="${AI_REVIEW_APPROVED_LOGINS:-chatgpt-codex-connector[bot]}"
request_reviewer="${AI_REVIEW_REQUEST_LOGIN:-}"
timeout_seconds="${AI_REVIEW_TIMEOUT_SECONDS:-600}"
poll_seconds="${AI_REVIEW_POLL_SECONDS:-10}"
evidence_output="${AI_REVIEW_EVIDENCE_OUTPUT:-}"
requester_login="${AI_REVIEW_REQUESTER_LOGIN:-}"
merge_after_review="${AI_REVIEW_MERGE:-false}"

fail() {
  printf 'automated review: %s\n' "$1" >&2
  exit 1
}

[[ -n "$repository" && "$pull_request" =~ ^[0-9]+$ ]] || fail "repository and pull-request number are required"
[[ "$timeout_seconds" =~ ^[1-9][0-9]*$ && "$poll_seconds" =~ ^[1-9][0-9]*$ ]] || fail "review timeout and polling interval must be positive integers"
[[ "$merge_after_review" == "true" || "$merge_after_review" == "false" ]] || fail "AI_REVIEW_MERGE must be true or false"
command -v gh >/dev/null 2>&1 || fail "gh CLI is required"
command -v jq >/dev/null 2>&1 || fail "jq is required"
if [[ -z "$requester_login" ]]; then
  requester_login="$(gh api user --jq '.login')" || fail "unable to resolve authenticated review requester"
fi

head_sha="$(gh api "repos/$repository/pulls/$pull_request" --jq '.head.sha')" || fail "unable to read pull request"
status_url="https://github.com/$repository/pull/$pull_request"

publish_status() {
  local state="$1"
  local description="$2"
  gh api --method POST "repos/$repository/statuses/$head_sha" \
    -f "state=$state" \
    -f "context=$check_name" \
    -f "description=$description" \
    -f "target_url=$status_url" >/dev/null
}

success_pending_completion=false
reset_status_after_error() {
  local exit_code=$?
  if [[ "$exit_code" -ne 0 && "$success_pending_completion" == "true" ]]; then
    publish_status failure "Post-review receipt, verification, or merge failed" || true
  fi
  trap - EXIT
  exit "$exit_code"
}
trap reset_status_after_error EXIT

require_unchanged_head() {
  local current_head
  current_head="$(gh api "repos/$repository/pulls/$pull_request" --jq '.head.sha')" ||
    fail "unable to recheck pull-request head"
  if [[ "$current_head" != "$head_sha" ]]; then
    publish_status error "Pull-request head changed during automated review" || true
    fail "pull-request head changed during automated review"
  fi
}

write_review_evidence() {
  local reviewer="$1"
  local proof="$2"
  local proof_comment_id="${3:-$review_request_id}"
  local observed_at
  [[ -n "$evidence_output" ]] || return 0
  observed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "$(dirname "$evidence_output")"
  jq -n \
    --arg repository "$repository" \
    --argjson pullRequest "$pull_request" \
    --arg headRevision "$head_sha" \
    --arg reviewer "$reviewer" \
    --arg statusCheck "$check_name" \
    --arg proof "$proof" \
    --arg observedAt "$observed_at" \
    --argjson proofCommentId "$proof_comment_id" \
    '{schemaVersion:1,repository:$repository,pullRequest:$pullRequest,headRevision:$headRevision,reviewer:$reviewer,status:"passed",statusCheck:$statusCheck,proof:$proof,proofCommentId:$proofCommentId,observedAt:$observedAt}' \
    > "$evidence_output"
}

merge_verified_pull_request() {
  local reviewer="$1"
  local proof="$2"
  local proof_comment_id="${3:-$review_request_id}"
  local authenticated_reviewer
  local merged
  [[ "$merge_after_review" == "true" ]] || return 0
  require_unchanged_head
  if [[ "$proof" == "approved-review" ]]; then
    authenticated_reviewer="$(gh api --paginate --slurp "repos/$repository/pulls/$pull_request/reviews?per_page=100" | jq -r \
      --arg reviewers "$approved_reviewers" --arg head "$head_sha" \
      '($reviewers | split(",")) as $approved | [.[][] | select((.user.login as $login | $approved | index($login)) != null and .commit_id == $head and (.state == "COMMENTED" or .state == "APPROVED" or .state == "CHANGES_REQUESTED" or .state == "DISMISSED")) | {reviewer:.user.login,state}] | last | select(.state == "APPROVED") | .reviewer // empty')"
  elif [[ "$proof" == "no-findings-reaction" ]]; then
    authenticated_reviewer="$(gh api --paginate --slurp "repos/$repository/issues/comments/$review_request_id/reactions?per_page=100" | jq -r \
      --arg reviewers "$approved_reviewers" \
      '($reviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
  else
    result_comment="$(gh api "repos/$repository/issues/comments/$proof_comment_id")"
    result_comment_reviewer="$(jq -r '.user.login' <<<"$result_comment")"
    result_comment_body="$(jq -r '.body' <<<"$result_comment")"
    issue_reaction_reviewer="$(gh api --paginate --slurp "repos/$repository/issues/$pull_request/reactions?per_page=100" | jq -r \
      --arg reviewers "$approved_reviewers" \
      '($reviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
    if [[ "$result_comment_reviewer" == "$reviewer" &&
          "$issue_reaction_reviewer" == "$reviewer" &&
          "$result_comment_body" == *"Codex Review: Didn't find any major issues."* &&
          "$result_comment_body" == *"**Reviewed commit:** \`${head_sha:0:10}\`"* ]]; then
      authenticated_reviewer="$reviewer"
    else
      authenticated_reviewer=""
    fi
  fi
  if [[ "$authenticated_reviewer" != "$reviewer" ]]; then
    publish_status failure "Automated review changed before protected merge" || true
    fail "automated review changed before protected merge"
  fi
  require_unchanged_head
  merged="$(gh api --method PUT "repos/$repository/pulls/$pull_request/merge" \
    -f "sha=$head_sha" -f "merge_method=merge" --jq '.merged')"
  if [[ "$merged" != "true" ]]; then
    publish_status failure "Protected merge failed after automated review" || true
    fail "protected merge failed after automated review"
  fi
}

publish_status pending "Waiting for approved automated review"
if [[ -n "$request_reviewer" ]]; then
  request_payload="$(jq -cn --arg reviewer "$request_reviewer" '{reviewers:[$reviewer]}')"
  gh api --method POST "repos/$repository/pulls/$pull_request/requested_reviewers" \
    --input - <<<"$request_payload" >/dev/null || true
fi

review_marker="<!-- ai-review-head:$head_sha -->"
review_request_body="@codex review

$review_marker"
trusted_request_ids="$(gh api --paginate --slurp "repos/$repository/issues/$pull_request/comments?per_page=100" | jq -r \
  --arg body "$review_request_body" --arg requester "$requester_login" \
  '[.[][] | select(.body == $body and .user.login == $requester) | .id] | reverse[]')"
review_request_id=""
while IFS= read -r candidate_request_id; do
  [[ -n "$candidate_request_id" ]] || continue
  completed_reviewer="$(gh api --paginate --slurp "repos/$repository/issues/comments/$candidate_request_id/reactions?per_page=100" | jq -r \
    --arg reviewers "$approved_reviewers" \
    '($reviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
  if [[ -n "$completed_reviewer" ]]; then
    review_request_id="$candidate_request_id"
    break
  fi
done <<<"$trusted_request_ids"
if [[ -z "$review_request_id" ]]; then
  created_request="$(gh api --method POST "repos/$repository/issues/$pull_request/comments" \
    -f "body=$review_request_body" --jq '{id,user:.user.login}')"
  [[ "$(jq -r '.user' <<<"$created_request")" == "$requester_login" ]] ||
    fail "created review request is not owned by the trusted requester"
  review_request_id="$(jq -r '.id' <<<"$created_request")"
fi

deadline=$((SECONDS + timeout_seconds))
while ((SECONDS < deadline)); do
  review="$(gh api --paginate --slurp "repos/$repository/pulls/$pull_request/reviews?per_page=100" | jq -c \
    --arg reviewers "$approved_reviewers" --arg head "$head_sha" \
    '($reviewers | split(",")) as $approved | [.[][] | select((.user.login as $login | $approved | index($login)) != null and .commit_id == $head and (.state == "COMMENTED" or .state == "APPROVED" or .state == "CHANGES_REQUESTED" or .state == "DISMISSED")) | {reviewer:.user.login,state,commit_id,submitted_at}] | last // empty')"
  if [[ -n "$review" ]]; then
    reviewer="$(jq -r '.reviewer' <<<"$review")"
    if [[ "$(jq -r '.state' <<<"$review")" == "APPROVED" ]]; then
      require_unchanged_head
      success_pending_completion=true
      publish_status success "Approved automated reviewer approved current PR head"
      write_review_evidence "$reviewer" "approved-review"
      merge_verified_pull_request "$reviewer" "approved-review"
      success_pending_completion=false
      printf 'automated review: %s passed for PR %s at %s by %s\n' "$check_name" "$pull_request" "$head_sha" "$reviewer"
      exit 0
    fi
    publish_status failure "Approved automated reviewer reported current-head findings"
    fail "approved automated reviewer reported findings for current PR head"
  fi
  reaction_reviewer="$(gh api --paginate --slurp "repos/$repository/issues/comments/$review_request_id/reactions?per_page=100" | jq -r \
    --arg reviewers "$approved_reviewers" \
    '($reviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
  if [[ -n "$reaction_reviewer" ]]; then
    require_unchanged_head
    success_pending_completion=true
    publish_status success "Approved automated reviewer found no current-head issues"
    write_review_evidence "$reaction_reviewer" "no-findings-reaction"
    merge_verified_pull_request "$reaction_reviewer" "no-findings-reaction"
    success_pending_completion=false
    printf 'automated review: %s passed for PR %s at %s by %s (+1)\n' "$check_name" "$pull_request" "$head_sha" "$reaction_reviewer"
    exit 0
  fi
  short_head="${head_sha:0:10}"
  no_findings_result="$(gh api --paginate --slurp "repos/$repository/issues/$pull_request/comments?per_page=100" | jq -c \
    --arg reviewers "$approved_reviewers" --arg shortHead "$short_head" \
    '($reviewers | split(",")) as $approved | [.[][] | select((.user.login as $login | $approved | index($login)) != null and (.body | startswith("Codex Review: Didn'\''t find any major issues.")) and (.body | contains("**Reviewed commit:** `" + $shortHead + "`"))) | {id,reviewer:.user.login}] | last // empty')"
  if [[ -n "$no_findings_result" ]]; then
    no_findings_reviewer="$(jq -r '.reviewer' <<<"$no_findings_result")"
    no_findings_comment_id="$(jq -r '.id' <<<"$no_findings_result")"
    issue_reaction_reviewer="$(gh api --paginate --slurp "repos/$repository/issues/$pull_request/reactions?per_page=100" | jq -r \
      --arg reviewers "$approved_reviewers" \
      '($reviewers | split(",")) as $approved | [.[][] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
    if [[ "$issue_reaction_reviewer" == "$no_findings_reviewer" ]]; then
      require_unchanged_head
      success_pending_completion=true
      publish_status success "Approved automated reviewer found no current-head issues"
      write_review_evidence "$no_findings_reviewer" "no-findings-comment" "$no_findings_comment_id"
      merge_verified_pull_request "$no_findings_reviewer" "no-findings-comment" "$no_findings_comment_id"
      success_pending_completion=false
      printf 'automated review: %s passed for PR %s at %s by %s (head-bound comment)\n' "$check_name" "$pull_request" "$head_sha" "$no_findings_reviewer"
      exit 0
    fi
  fi
  sleep "$poll_seconds"
done

publish_status failure "Approved automated review missing or stale" || true
fail "required automated review is missing or stale for current PR head"
