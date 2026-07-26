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

fail() {
  printf 'automated review: %s\n' "$1" >&2
  exit 1
}

[[ -n "$repository" && "$pull_request" =~ ^[0-9]+$ ]] || fail "repository and pull-request number are required"
[[ "$timeout_seconds" =~ ^[1-9][0-9]*$ && "$poll_seconds" =~ ^[1-9][0-9]*$ ]] || fail "review timeout and polling interval must be positive integers"
command -v gh >/dev/null 2>&1 || fail "gh CLI is required"
command -v jq >/dev/null 2>&1 || fail "jq is required"

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
    --argjson requestCommentId "$review_request_id" \
    '{schemaVersion:1,repository:$repository,pullRequest:$pullRequest,headRevision:$headRevision,reviewer:$reviewer,status:"passed",statusCheck:$statusCheck,proof:$proof,requestCommentId:$requestCommentId,observedAt:$observedAt}' \
    > "$evidence_output"
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
review_request_id="$(gh api --method POST "repos/$repository/issues/$pull_request/comments" \
  -f "body=$review_request_body" --jq '.id')"

deadline=$((SECONDS + timeout_seconds))
while ((SECONDS < deadline)); do
  review="$(gh api --paginate --slurp "repos/$repository/pulls/$pull_request/reviews?per_page=100" | jq -c \
    --arg reviewers "$approved_reviewers" --arg head "$head_sha" \
    '($reviewers | split(",")) as $approved | [.[][] | select((.user.login as $login | $approved | index($login)) != null and .commit_id == $head and (.state == "COMMENTED" or .state == "APPROVED" or .state == "CHANGES_REQUESTED" or .state == "DISMISSED")) | {reviewer:.user.login,state,commit_id,submitted_at}] | last // empty')"
  if [[ -n "$review" ]]; then
    reviewer="$(jq -r '.reviewer' <<<"$review")"
    if [[ "$(jq -r '.state' <<<"$review")" == "APPROVED" ]]; then
      require_unchanged_head
      publish_status success "Approved automated reviewer approved current PR head"
      write_review_evidence "$reviewer" "approved-review"
      printf 'automated review: %s passed for PR %s at %s by %s\n' "$check_name" "$pull_request" "$head_sha" "$reviewer"
      exit 0
    fi
    publish_status failure "Approved automated reviewer reported current-head findings"
    fail "approved automated reviewer reported findings for current PR head"
  fi
  reaction_reviewer="$(gh api "repos/$repository/issues/comments/$review_request_id/reactions" | jq -r \
    --arg reviewers "$approved_reviewers" \
    '($reviewers | split(",")) as $approved | [.[] | select(.content == "+1" and (.user.login as $login | $approved | index($login)) != null) | .user.login] | last // empty')"
  if [[ -n "$reaction_reviewer" ]]; then
    require_unchanged_head
    publish_status success "Approved automated reviewer found no current-head issues"
    write_review_evidence "$reaction_reviewer" "no-findings-reaction"
    printf 'automated review: %s passed for PR %s at %s by %s (+1)\n' "$check_name" "$pull_request" "$head_sha" "$reaction_reviewer"
    exit 0
  fi
  sleep "$poll_seconds"
done

publish_status failure "Approved automated review missing or stale" || true
fail "required automated review is missing or stale for current PR head"
