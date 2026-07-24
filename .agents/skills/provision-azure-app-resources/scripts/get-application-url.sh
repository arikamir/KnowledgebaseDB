#!/usr/bin/env bash
set -euo pipefail

namespace="${1:-career-agent}"
gateway="${2:-public-gateway}"

command -v kubectl >/dev/null 2>&1 || {
  echo "[azure-infra] kubectl is required to resolve the application URL" >&2
  exit 1
}

echo "[azure-infra] Waiting for the public AGC Gateway endpoint..." >&2
kubectl wait --namespace "$namespace" \
  --for=condition=Programmed \
  "gateway/$gateway" \
  --timeout=10m >/dev/null

address="$(kubectl get gateway "$gateway" --namespace "$namespace" -o jsonpath='{.status.addresses[0].value}')"

[[ -n "$address" ]] || {
  echo "[azure-infra] AGC Gateway has no public address" >&2
  exit 1
}

echo "https://$address/"
