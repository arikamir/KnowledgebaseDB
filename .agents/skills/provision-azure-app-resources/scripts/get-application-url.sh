#!/usr/bin/env bash
set -euo pipefail

namespace="${1:-app-routing-system}"
service="${2:-nginx}"

command -v kubectl >/dev/null 2>&1 || {
  echo "[azure-infra] kubectl is required to resolve the application URL" >&2
  exit 1
}

echo "[azure-infra] Waiting for the public ingress endpoint..." >&2
kubectl wait --namespace "$namespace" \
  --for=jsonpath='{.status.loadBalancer.ingress[0].ip}' \
  "service/$service" \
  --timeout=10m >/dev/null

address="$(kubectl get service "$service" --namespace "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
if [[ -z "$address" ]]; then
  address="$(kubectl get service "$service" --namespace "$namespace" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
fi

[[ -n "$address" ]] || {
  echo "[azure-infra] Ingress controller has no public address" >&2
  exit 1
}

echo "http://$address/"
