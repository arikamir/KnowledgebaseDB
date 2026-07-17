#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; [[ -n "$ACTION" ]] || exit 2; shift
PLAN="" BUILD_ID="" REVISION="" REGISTRY="" OUTPUT_DIR="" STATE_DIR="" EVIDENCE_DIR="" NOW="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
SERVICE="" DIGEST="" GATES=""
while (($#)); do
  case "$1" in
    --plan) PLAN="${2:-}"; shift 2 ;;
    --build-id) BUILD_ID="${2:-}"; shift 2 ;;
    --revision) REVISION="${2:-}"; shift 2 ;;
    --registry) REGISTRY="${2:-}"; shift 2 ;;
    --output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --state-dir) STATE_DIR="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --service) SERVICE="${2:-}"; shift 2 ;;
    --digest) DIGEST="${2:-}"; shift 2 ;;
    --gates) GATES="${2:-}"; shift 2 ;;
    --now) NOW="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done
[[ "$REGISTRY" =~ ^[a-z0-9.-]+\.azurecr\.io$ && -n "$STATE_DIR" ]] || exit 2
mkdir -p "$STATE_DIR"; chmod 0700 "$STATE_DIR"
epoch() { jq -nr --arg value "$1" '$value | fromdateiso8601'; }
atomic_json() { local target="$1"; shift; local temporary; temporary="$(mktemp "$(dirname "$target")/.json.XXXXXX")"; jq "$@" > "$temporary"; chmod 0600 "$temporary"; mv "$temporary" "$target"; }

publish_manifest() {
  local entries="$1" manifest="$OUTPUT_DIR/release-manifest.json" temporary manifest_digest
  mkdir -p "$OUTPUT_DIR"; chmod 0700 "$OUTPUT_DIR"
  temporary="$(mktemp "$OUTPUT_DIR/.release-manifest.XXXXXX")"
  jq -n --arg build "$BUILD_ID" --arg revision "$REVISION" --arg now "$NOW" --argjson services "$entries" \
    '{schemaVersion:1,buildId:$build,sourceRevision:$revision,createdAt:$now,services:$services,selectorPolicy:"digest-only"}' > "$temporary"
  chmod 0444 "$temporary"; mv "$temporary" "$manifest"
  manifest_digest="sha256:$(shasum -a 256 "$manifest" | awk '{print $1}')"
  printf '%s' "$manifest_digest"
}

case "$ACTION" in
  publish)
    [[ -f "$PLAN" && "$BUILD_ID" =~ ^[A-Za-z0-9._-]+$ && "$REVISION" =~ ^[0-9a-f]{40}$ && -n "$OUTPUT_DIR" ]] || exit 2
    jq -e --arg revision "$REVISION" 'keys == ["baselineRevision","reason","services","sourceRevision","validationLanes"] and .sourceRevision==$revision and (.services|keys==["bff","core","ui"]) and all(.services[]; type=="boolean")' "$PLAN" >/dev/null || exit 1
    entries='{}'
    for service in ui bff core; do
      [[ "$(jq -r --arg service "$service" '.services[$service]' "$PLAN")" == true ]] || continue
      case "$service" in ui) context="ui"; dockerfile="ui/Dockerfile" ;; bff) context="bff"; dockerfile="bff/Dockerfile" ;; core) context="."; dockerfile="Dockerfile" ;; esac
      service_dir="$OUTPUT_DIR/$service"; mkdir -p "$service_dir"
      # The transient quarantine tag is never a release alias; manifests select
      # only the resolved repository@sha256 digest.
      repository="$REGISTRY/devops-career-agent-$service"; quarantine_tag="$repository:quarantine-$BUILD_ID"
      metadata="$service_dir/build-metadata.json"
      docker buildx build --file "$dockerfile" --tag "$quarantine_tag" --push --metadata-file "$metadata" "$context"
      digest="$(jq -er '."containerimage.digest" | select(test("^sha256:[0-9a-f]{64}$"))' "$metadata")"
      image="$repository@$digest"
      trivy image --format json --output "$service_dir/scan.json" "$image"
      syft "$image" -o "spdx-json=$service_dir/sbom.spdx.json"
      entries="$(jq -cn --argjson current "$entries" --arg service "$service" --arg image "$image" --arg scan "$service/scan.json" --arg sbom "$service/sbom.spdx.json" '$current + {($service):{image:$image,scanEvidence:$scan,sbomEvidence:$sbom}}')"
      hex="${digest#sha256:}"; state="$STATE_DIR/$service-$hex.json"; [[ ! -e "$state" ]] || { printf 'digest already belongs to an earlier build; use fresh-gate reuse\n' >&2; exit 1; }
      jq -n --arg service "$service" --arg digest "$digest" --arg build "$BUILD_ID" --arg revision "$REVISION" --arg now "$NOW" \
        --arg scan "$service/scan.json" --arg sbom "$service/sbom.spdx.json" \
        '{schemaVersion:1,status:"published_unpromoted",service:$service,digest:$digest,buildId:$build,sourceRevision:$revision,publishedAt:$now,scanEvidence:$scan,sbomEvidence:$sbom,releaseManifestDigest:null,promoted:false,held:false,references:0,releaseAlias:false}' > "$state"
      chmod 0600 "$state"
    done
    release_digest="$(publish_manifest "$entries")"
    for state in "$STATE_DIR"/*.json; do
      [[ -f "$state" ]] || continue
      jq -e --arg build "$BUILD_ID" '.buildId==$build and .releaseManifestDigest==null' "$state" >/dev/null || continue
      atomic_json "$state" --arg digest "$release_digest" '.releaseManifestDigest=$digest' "$state"
    done
    printf '%s\n' "$OUTPUT_DIR/release-manifest.json"
    ;;
  reuse)
    [[ "$SERVICE" =~ ^(ui|bff|core)$ && "$DIGEST" =~ ^sha256:[0-9a-f]{64}$ && -f "$GATES" && -n "$OUTPUT_DIR" && "$BUILD_ID" =~ ^[A-Za-z0-9._-]+$ && "$REVISION" =~ ^[0-9a-f]{40}$ ]] || exit 2
    jq -e 'keys==["environment","evidence","identity","scan","validation"] and all(.[]; .==true)' "$GATES" >/dev/null || exit 1
    state="$STATE_DIR/$SERVICE-${DIGEST#sha256:}.json"; [[ -f "$state" ]] || exit 1
    jq -e --arg service "$SERVICE" --arg digest "$DIGEST" --arg build "$BUILD_ID" '.status=="published_unpromoted" and .service==$service and .digest==$digest and .buildId!=$build and .promoted==false' "$state" >/dev/null || exit 1
    image="$REGISTRY/devops-career-agent-$SERVICE@$DIGEST"
    entries="$(jq -cn --arg service "$SERVICE" --arg image "$image" '{($service):{image:$image,reusedThroughFreshGates:true}}')"
    release_digest="$(publish_manifest "$entries")"
    atomic_json "$state" --arg build "$BUILD_ID" --arg manifest "$release_digest" '.references += 1 | .lastReuseBuildId=$build | .lastReuseManifestDigest=$manifest' "$state"
    ;;
  gc)
    [[ -n "$EVIDENCE_DIR" ]] || exit 2; mkdir -p "$EVIDENCE_DIR"; now_epoch="$(epoch "$NOW")"
    for state in "$STATE_DIR"/*.json; do
      [[ -f "$state" ]] || continue
      jq -e '.status=="published_unpromoted" and .promoted==false and .held==false and .references==0' "$state" >/dev/null || continue
      published="$(jq -r '.publishedAt' "$state")"; ((now_epoch - $(epoch "$published") >= 30 * 86400)) || continue
      service="$(jq -r '.service' "$state")"; digest="$(jq -r '.digest' "$state")"
      atomic_json "$state" '.status="gc_eligible"' "$state"
      az acr repository delete --yes --name "${REGISTRY%%.*}" --image "devops-career-agent-$service@$digest" >/dev/null
      retained_until_epoch=$(( $(epoch "$published") + 90 * 86400 ))
      atomic_json "$state" --arg now "$NOW" --arg status "gc_deleted" --argjson retainUntilEpoch "$retained_until_epoch" '.status=$status | .dispositionAt=$now | .dispositionEvidenceRetainUntilEpoch=$retainUntilEpoch' "$state"
      cp "$state" "$EVIDENCE_DIR/$(basename "$state")"
    done
    ;;
  *) exit 2 ;;
esac
