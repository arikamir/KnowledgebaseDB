#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(pwd)" FACTS="" STATE_METADATA="" ATTESTATIONS="" OUTPUT=""
while (($#)); do case "$1" in --repo-root) REPO_ROOT="${2:-}"; shift 2;; --facts) FACTS="${2:-}"; shift 2;; --state-metadata) STATE_METADATA="${2:-}"; shift 2;; --attestations) ATTESTATIONS="${2:-}"; shift 2;; --output) OUTPUT="${2:-}"; shift 2;; *) exit 2;; esac; done
expected_output="$REPO_ROOT/config/platform-bootstrap-nonprod.json"
[[ "${PLATFORM_FINALIZATION_AUTHORIZED:-}" == T194 && "$OUTPUT" == "$expected_output" && ! -e "$OUTPUT" && -f "$FACTS" && -f "$STATE_METADATA" && -f "$ATTESTATIONS" ]] || {
  printf 'finalization: T194 authorization, exact new output, facts, state, and attestations required\n' >&2; exit 1;
}
jq -e 'keys==["backendContainer","lineage","locked","serial"] and .locked==true and .serial>=1 and (.lineage|length)>=8' "$STATE_METADATA" >/dev/null || exit 1
jq -e 'keys==["albController","identityDenials","jitPermissions","migrationPolicy","providerQuotaCapacity"] and all(.[]; type=="object")' "$ATTESTATIONS" >/dev/null || exit 1
jq -e 'keys==["identities","origins","resourceGroup","resources","review","subscriptionId","tenantId"] and
  (.identities.workloads|length)==9 and .identities.ui==null and .identities.validator==null and
  (.review|keys==["platformOperationsObjectId","securityApproverObjectId"]) and
  .review.platformOperationsObjectId!=.review.securityApproverObjectId' "$FACTS" >/dev/null || exit 1
python3 - "$ATTESTATIONS" <<'PY'
import datetime,json,sys
a=json.load(open(sys.argv[1])); now=datetime.datetime.now(datetime.timezone.utc)
for name,value in a.items():
    stamp=value.get("capturedAt")
    if not stamp: raise SystemExit(f"{name} missing capturedAt")
    captured=datetime.datetime.fromisoformat(stamp.replace("Z","+00:00"))
    if captured > now or now-captured > datetime.timedelta(days=7): raise SystemExit(f"{name} stale")
PY
digest="$($REPO_ROOT/scripts/azure/compute-platform-configuration-digest.sh "$REPO_ROOT")"
generated_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
expires_at="$(python3 - "$generated_at" <<'PY'
import datetime,sys
value=datetime.datetime.fromisoformat(sys.argv[1].replace("Z","+00:00"))+datetime.timedelta(days=7)
print(value.strftime("%Y-%m-%dT%H:%M:%SZ"))
PY
)"
temporary="$(mktemp "$REPO_ROOT/config/.platform-bootstrap.XXXXXX")"
cleanup() { rm -f "$temporary"; }; trap cleanup EXIT
jq -n --argjson facts "$(cat "$FACTS")" --argjson state "$(cat "$STATE_METADATA")" --argjson attestations "$(cat "$ATTESTATIONS")" --argjson digest "$digest" --arg generatedAt "$generated_at" --arg expiresAt "$expires_at" '
  {schemaVersion:1,manifestStatus:"reviewed",environment:"nonprod",tenantId:$facts.tenantId,subscriptionId:$facts.subscriptionId,
   resourceGroup:$facts.resourceGroup,state:$state,
   configuration:{policy:"config/platform-configuration-digest-v1.yaml",algorithm:$digest.algorithm,digest:$digest.digest,recordCount:$digest.recordCount},
   resources:$facts.resources,identities:$facts.identities,origins:$facts.origins,attestations:$attestations,
   review:($facts.review + {generatedAt:$generatedAt,expiresAt:$expiresAt})}
' > "$temporary"
chmod 0444 "$temporary"
"$REPO_ROOT/scripts/ci/validate-evidence.sh" --file "$temporary" >/dev/null
"$REPO_ROOT/scripts/azure/preflight-ui-platform.sh" live --repo-root "$REPO_ROOT" --manifest "$temporary" >/dev/null
mv "$temporary" "$OUTPUT"; trap - EXIT
printf '%s\n' "$OUTPUT"
