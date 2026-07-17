#!/usr/bin/env bash
set -euo pipefail

SERVICE="" EXPECTED_IMAGE="" NAMESPACE="${DELIVERY_NAMESPACE:-career-agent}" SMOKE_URL=""
while (($#)); do
  case "$1" in
    --service) SERVICE="${2:-}"; shift 2 ;;
    --expected-image) EXPECTED_IMAGE="${2:-}"; shift 2 ;;
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --smoke-url) SMOKE_URL="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ "$SERVICE" =~ ^(ui|bff|core)$ && "$EXPECTED_IMAGE" =~ @sha256:[0-9a-f]{64}$ && "$SMOKE_URL" =~ ^https:// ]] || exit 2
kubectl -n "$NAMESPACE" rollout status "deployment/$SERVICE" --timeout="${DELIVERY_ROLLOUT_TIMEOUT:-5m}"
actual="$(kubectl -n "$NAMESPACE" get deployment "$SERVICE" -o json | jq -er --arg service "$SERVICE" '.spec.template.spec.containers[] | select(.name==$service) | .image')"
[[ "$actual" == "$EXPECTED_IMAGE" ]] || { printf 'verification: digest mismatch\n' >&2; exit 1; }
curl --fail --silent --show-error --max-time 30 "$SMOKE_URL" >/dev/null
