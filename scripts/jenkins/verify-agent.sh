#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="" ACTOR="" RESOURCE_ID="" TEMPLATE_JSON=""
usage() { printf 'Usage: %s --manifest FILE --actor NAME --resource-id ID [--template-json FILE]\n' "$0" >&2; exit 2; }
while (($#)); do
  case "$1" in
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    --actor) ACTOR="${2:-}"; shift 2 ;;
    --resource-id) RESOURCE_ID="${2:-}"; shift 2 ;;
    --template-json) TEMPLATE_JSON="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -f "$MANIFEST" && -n "$ACTOR" && -n "$RESOURCE_ID" ]] || usage

"$ROOT/scripts/jenkins/verify-managed-identity.sh" \
  --manifest "$MANIFEST" --actor "$ACTOR" --resource-id "$RESOURCE_ID" >/dev/null
if [[ "$ACTOR" == validator ]]; then
  [[ -f "$TEMPLATE_JSON" ]] || usage
  "$ROOT/scripts/jenkins/verify-validator-agent.sh" --template-json "$TEMPLATE_JSON" >/dev/null
elif [[ "$ACTOR" != publisher && "$ACTOR" != deployer ]]; then
  printf 'agent verification failed: only validator, publisher, or deployer are Jenkins agents\n' >&2
  exit 1
fi
jq -cn --arg actor "$ACTOR" '{status:"agent-preflight-valid",actor:$actor,terraform:false,stateRead:false}'
