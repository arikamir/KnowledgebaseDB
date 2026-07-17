#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-schema-digest}"; shift || true
REPO_ROOT="$(pwd)" MANIFEST=""
while (($#)); do case "$1" in --repo-root) REPO_ROOT="${2:-}"; shift 2;; --manifest) MANIFEST="${2:-}"; shift 2;; *) exit 2;; esac; done
[[ "$MODE" =~ ^(schema-digest|live)$ && -f "$MANIFEST" ]] || exit 2

python3 - "$MANIFEST" "$REPO_ROOT/config/platform-bootstrap.schema.json" <<'PY'
import json, re, sys
m=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2]))
if set(m) != set(s["required"]): raise SystemExit("manifest keys do not match schema")
if m["schemaVersion"] != 1 or m["environment"] not in ("nonprod","dev","test","stage"): raise SystemExit("manifest version/environment invalid")
if not re.fullmatch(r"sha256:[0-9a-f]{64}",m["configuration"]["digest"]): raise SystemExit("digest invalid")
if m["identities"].get("ui") is not None or m["identities"].get("validator") is not None: raise SystemExit("UI/validator must be identityless")
if len(m["identities"].get("workloads",{})) != 9: raise SystemExit("workload identity topology incomplete")
PY
digest_json="$($REPO_ROOT/scripts/azure/compute-platform-configuration-digest.sh "$REPO_ROOT")"
[[ "$(jq -r '.configuration.digest' "$MANIFEST")" == "$(jq -r '.digest' <<<"$digest_json")" ]] || { printf 'preflight: repository configuration digest mismatch\n' >&2; exit 1; }
[[ "$(jq -r '.configuration.recordCount' "$MANIFEST")" == "$(jq -r '.recordCount' <<<"$digest_json")" ]] || exit 1
[[ "$MODE" == schema-digest ]] && { jq -cn '{status:"schema-digest-valid",identityless:true}'; exit 0; }
[[ "$(jq -r '.manifestStatus' "$MANIFEST")" == reviewed ]] || exit 1
command -v az >/dev/null && command -v kubectl >/dev/null || exit 1
subscription="$(jq -r '.subscriptionId' "$MANIFEST")"; resource_group="$(jq -r '.resourceGroup' "$MANIFEST")"
[[ "$(az account show --query id -o tsv)" == "$subscription" ]] || exit 1
az group show --name "$resource_group" --query id -o tsv >/dev/null
kubectl get --raw='/readyz' >/dev/null
kubectl -n azure-alb-system get deployment alb-controller -o json >/dev/null
kubectl get validatingadmissionpolicy career-migration-policy -o json >/dev/null
! kubectl get ingress --all-namespaces -o name | grep -q . || { printf 'preflight: legacy Ingress exists\n' >&2; exit 1; }
[[ "$(az aks show --resource-group "$resource_group" --name "$(jq -r '.resources.aksId|split("/")|last' "$MANIFEST")" --query 'webAppRouting.identityResourceId' -o tsv)" == "" ]] || exit 1
jq -cn '{status:"live-preflight-valid",terraformStateRead:false,subscriptionWideRead:false}'
