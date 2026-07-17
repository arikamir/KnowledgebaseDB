#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="" ACTOR="" RESOURCE_ID=""
usage() { printf 'Usage: %s --manifest FILE --actor NAME --resource-id ID\n' "$0" >&2; exit 2; }
while (($#)); do
  case "$1" in
    --manifest) MANIFEST="${2:-}"; shift 2 ;;
    --actor) ACTOR="${2:-}"; shift 2 ;;
    --resource-id) RESOURCE_ID="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[[ -f "$MANIFEST" && -n "$ACTOR" && -n "$RESOURCE_ID" ]] || usage

# The canonical schema/digest gate stays in one place. Jenkins consumes its
# report and adds only actor binding checks.
report="$("$ROOT/scripts/azure/preflight-ui-platform.sh" schema-digest --repo-root "$ROOT" --manifest "$MANIFEST")"
[[ "$(jq -r '.status' <<<"$report")" == schema-digest-valid ]] || exit 1

case "$ACTOR" in
  publisher|deployer|kubelet) selector=".identities.$ACTOR" ;;
  bff|core|lifecycle|retention|lab-revalidation|migration|evidence-hold-reconciler|alb-controller|gateway-certificate-dns)
    selector=".identities.workloads[\"$ACTOR\"]" ;;
  ui|validator)
    [[ "$RESOURCE_ID" == none && "$(jq -r ".identities.$ACTOR" "$MANIFEST")" == null ]] || exit 1
    jq -cn --arg actor "$ACTOR" '{status:"identity-binding-valid",actor:$actor,identityless:true}'
    exit 0 ;;
  *) usage ;;
esac
expected="$(jq -r "$selector" "$MANIFEST")"
[[ "$expected" == "$RESOURCE_ID" && "$expected" == /subscriptions/* ]] || {
  printf 'managed identity verification failed: manifest binding mismatch\n' >&2
  exit 1
}
jq -cn --arg actor "$ACTOR" --arg resourceId "$RESOURCE_ID" \
  '{status:"identity-binding-valid",actor:$actor,resourceId:$resourceId,identityless:false}'
