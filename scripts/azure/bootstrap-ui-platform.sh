#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-dry-run}"; shift || true
REPO_ROOT="$(pwd)" AUTHORIZATION="" ATTESTATION="" PLAN="infra/azure/platform.tfplan"
while (($#)); do case "$1" in --repo-root) REPO_ROOT="${2:-}"; shift 2;; --authorization) AUTHORIZATION="${2:-}"; shift 2;; --attestation) ATTESTATION="${2:-}"; shift 2;; --plan) PLAN="${2:-}"; shift 2;; *) exit 2;; esac; done
[[ "$MODE" =~ ^(dry-run|plan|apply)$ && -f "$AUTHORIZATION" && -f "$ATTESTATION" ]] || exit 2

jq -e '
  keys==["activatedAt","actorObjectId","consentApprover","denied","expiresAt","roles","schemaVersion"] and .schemaVersion==1 and
  (.roles|sort)==(["Application Administrator","Contributor:application-rg","Network Contributor:named-shared-network","Private DNS Zone Contributor:named-zones","ProviderQuotaRead:allowlisted","Role Based Access Control Administrator:application-rg","Storage Blob Data Contributor:state-container"]|sort) and
  (.consentApprover|keys==["objectId","role"] and .role=="Privileged Role Administrator") and .consentApprover.objectId!=.actorObjectId and
  (.denied|sort)==(["Global Administrator","Owner","Jenkins principal","standing privilege","unrelated app/data/resource access"]|sort)
' "$AUTHORIZATION" >/dev/null || { printf 'bootstrap: invalid JIT authorization\n' >&2; exit 1; }
jq -e 'keys==["capacity","capturedAt","expiresAt","providers","quotas","schemaVersion"] and .schemaVersion==1 and (.providers|type=="object") and (.quotas|type=="object") and (.capacity|type=="object")' "$ATTESTATION" >/dev/null || exit 1
python3 - "$AUTHORIZATION" "$ATTESTATION" <<'PY'
import datetime,json,sys
now=datetime.datetime.now(datetime.timezone.utc)
auth,att=(json.load(open(path)) for path in sys.argv[1:])
parse=lambda value: datetime.datetime.fromisoformat(value.replace("Z","+00:00"))
if not (parse(auth["activatedAt"]) <= now < parse(auth["expiresAt"])): raise SystemExit("bootstrap: JIT activation is not current")
if not (parse(att["capturedAt"]) <= now < parse(att["expiresAt"]) and now-parse(att["capturedAt"]) <= datetime.timedelta(days=7)): raise SystemExit("bootstrap: provider/quota/capacity attestation is stale")
PY

infra="$REPO_ROOT/infra/azure"
[[ -f "$infra/.terraform.lock.hcl" && -f "$infra/versions.tf" ]] || { printf 'bootstrap: provider lock/config missing\n' >&2; exit 1; }
grep -Eq 'backend[[:space:]]+"azurerm"' "$infra/backend.tf" 2>/dev/null || { printf 'bootstrap: locked Azure Storage backend missing\n' >&2; exit 1; }
printf '[bootstrap] reviewed Terraform, JIT scopes, provider lock, and seven-day attestation inputs validated\n'
[[ "$MODE" == dry-run ]] && exit 0
[[ "${PLATFORM_OPERATIONS_INTERACTIVE:-}" == true ]] || { printf 'bootstrap: interactive Platform Operations identity required\n' >&2; exit 1; }
terraform -chdir="$infra" init
if [[ "$MODE" == plan ]]; then terraform -chdir="$infra" plan -out="$(basename "$PLAN")"; exit 0; fi
[[ "${PLATFORM_BOOTSTRAP_AUTHORIZED:-}" == true && -f "$REPO_ROOT/$PLAN" ]] || { printf 'bootstrap: reviewed plan and explicit authorization required\n' >&2; exit 1; }
terraform -chdir="$infra" apply "$(basename "$PLAN")"
# Deliberately no environment-manifest write: only finalize-ui-platform.sh owns it.
