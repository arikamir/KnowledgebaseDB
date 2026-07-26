#!/usr/bin/env bash
set -euo pipefail

repository="${1:-${GITHUB_REPOSITORY:-}}"
pull_request="${2:-${PULL_REQUEST_NUMBER:-}}"
check_name="${COPILOT_REVIEW_CHECK_NAME:-copilot/review}"
reviewer="${COPILOT_REVIEWER_LOGIN:-copilot-pull-request-reviewer[bot]}"
timeout_seconds="${COPILOT_REVIEW_TIMEOUT_SECONDS:-600}"
poll_seconds="${COPILOT_REVIEW_POLL_SECONDS:-10}"

fail() {
  printf 'copilot review: %s\n' "$1" >&2
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

publish_status pending "Waiting for GitHub Copilot review"
request_payload="$(jq -cn --arg reviewer "$reviewer" '{reviewers:[$reviewer]}')"
if ! gh api --method POST "repos/$repository/pulls/$pull_request/requested_reviewers" \
  --input - <<<"$request_payload" >/dev/null; then
  publish_status failure "Unable to request GitHub Copilot review" || true
  fail "unable to request GitHub Copilot review"
fi

deadline=$((SECONDS + timeout_seconds))
while ((SECONDS < deadline)); do
  review="$(gh api "repos/$repository/pulls/$pull_request/reviews" | jq -c \
    --arg reviewer "$reviewer" --arg head "$head_sha" \
    '[.[] | select(.user.login == $reviewer and .commit_id == $head and (.state == "COMMENTED" or .state == "APPROVED"))] | last // empty')"
  if [[ -n "$review" ]]; then
    publish_status success "GitHub Copilot reviewed the current PR head"
    printf 'copilot review: %s passed for PR %s at %s\n' "$check_name" "$pull_request" "$head_sha"
    exit 0
  fi
  sleep "$poll_seconds"
done

publish_status failure "GitHub Copilot review missing or stale" || true
fail "required Copilot review is missing or stale for current PR head"
