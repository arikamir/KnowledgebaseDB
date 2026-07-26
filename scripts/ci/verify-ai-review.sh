#!/usr/bin/env bash
set -euo pipefail

repository="${1:-${GITHUB_REPOSITORY:-}}"
pull_request="${2:-${PULL_REQUEST_NUMBER:-}}"
check_name="${AI_REVIEW_CHECK_NAME:-ai/review}"
approved_reviewers="${AI_REVIEW_APPROVED_LOGINS:-chatgpt-codex-connector[bot]}"
request_reviewer="${AI_REVIEW_REQUEST_LOGIN:-}"
timeout_seconds="${AI_REVIEW_TIMEOUT_SECONDS:-600}"
poll_seconds="${AI_REVIEW_POLL_SECONDS:-10}"

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

publish_status pending "Waiting for approved automated review"
if [[ -n "$request_reviewer" ]]; then
  request_payload="$(jq -cn --arg reviewer "$request_reviewer" '{reviewers:[$reviewer]}')"
  gh api --method POST "repos/$repository/pulls/$pull_request/requested_reviewers" \
    --input - <<<"$request_payload" >/dev/null || true
fi

deadline=$((SECONDS + timeout_seconds))
while ((SECONDS < deadline)); do
  review="$(gh api "repos/$repository/pulls/$pull_request/reviews" | jq -c \
    --arg reviewers "$approved_reviewers" --arg head "$head_sha" \
    '($reviewers | split(",")) as $approved | [.[] | select((.user.login as $login | $approved | index($login)) != null and .commit_id == $head and (.state == "COMMENTED" or .state == "APPROVED")) | {reviewer:.user.login,state,commit_id,submitted_at}] | last // empty')"
  if [[ -n "$review" ]]; then
    reviewer="$(jq -r '.reviewer' <<<"$review")"
    publish_status success "Approved automated reviewer verified current PR head"
    printf 'automated review: %s passed for PR %s at %s by %s\n' "$check_name" "$pull_request" "$head_sha" "$reviewer"
    exit 0
  fi
  sleep "$poll_seconds"
done

publish_status failure "Approved automated review missing or stale" || true
fail "required automated review is missing or stale for current PR head"
