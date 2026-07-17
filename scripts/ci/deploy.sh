#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; shift || true
NAMESPACE="${DELIVERY_NAMESPACE:-career-agent}" SERVICE="" IMAGE="" OUTPUT=""
while (($#)); do
  case "$1" in
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --service) SERVICE="${2:-}"; shift 2 ;;
    --image) IMAGE="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ "$NAMESPACE" =~ ^[a-z0-9][a-z0-9-]{0,62}$ ]] || exit 2
image_for() {
  kubectl -n "$NAMESPACE" get deployment "$1" -o json | jq -er --arg service "$1" \
    '.spec.template.spec.containers[] | select(.name==$service) | .image | select(test("@sha256:[0-9a-f]{64}$"))'
}
case "$ACTION" in
  snapshot)
    [[ -n "$OUTPUT" && ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || exit 1
    mkdir -p "$(dirname "$OUTPUT")"
    ui="$(image_for ui)"; bff="$(image_for bff)"; core="$(image_for core)"
    temporary="$(mktemp "$(dirname "$OUTPUT")/.snapshot.XXXXXX")"
    jq -n --arg environment "$NAMESPACE" --arg ui "$ui" --arg bff "$bff" --arg core "$core" \
      '{environment:$environment,services:{bff:$bff,core:$core,ui:$ui}}' > "$temporary"
    chmod 0444 "$temporary"; mv "$temporary" "$OUTPUT"
    ;;
  mutate)
    [[ "$SERVICE" =~ ^(ui|bff|core)$ && "$IMAGE" =~ ^[a-z0-9.-]+\.azurecr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$ ]] || exit 2
    kubectl -n "$NAMESPACE" set image "deployment/$SERVICE" "$SERVICE=$IMAGE"
    ;;
  current)
    [[ "$SERVICE" =~ ^(ui|bff|core)$ ]] || exit 2
    image_for "$SERVICE"
    ;;
  *) exit 2 ;;
esac
