#!/usr/bin/env bash
set -euo pipefail

repository="${1:-${GITHUB_REPOSITORY:-}}"
pull_request="${2:-${PULL_REQUEST_NUMBER:-}}"
check_name="${COPILOT_REVIEW_CHECK_NAME:-copilot/review}"

fail() {
  printf 'copilot review: %s\n' "$1" >&2
  exit 1
}

[[ -n "$repository" && "$pull_request" =~ ^[0-9]+$ ]] || fail "repository and pull-request number are required"
command -v gh >/dev/null 2>&1 || fail "gh CLI is required"

head_sha="$(gh api "repos/$repository/pulls/$pull_request" --jq '.head.sha')" || fail "unable to read pull request"
result="$(gh api "repos/$repository/commits/$head_sha/check-runs" | jq -c --arg name "$check_name" '[.check_runs[] | select(.name == $name) | {status,conclusion}] | last // empty')"
[[ -n "$result" ]] || fail "required Copilot status check is missing"
[[ "$(jq -r '.status' <<<"$result")" == "completed" && "$(jq -r '.conclusion' <<<"$result")" == "success" ]] || fail "required Copilot status check is not successful"

printf 'copilot review: %s passed for PR %s\n' "$check_name" "$pull_request"
