#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM_URL="https://github.com/jenkinsci/azure-container-agents-plugin.git"
UPSTREAM_TAG="372.v073266fff4a_7"
UPSTREAM_COMMIT="073266fff4a73604454654e2e20bdac52cfea6dc"
PLUGIN_VERSION="372.v073266fff4a_7-uami.2"
MAVEN_IMAGE="maven:3.9.11-eclipse-temurin-21@sha256:6fdc855a6ed81d288ca7ca37ac6ff5e9308b612485c0801d70b25a858c83d237"
M2_CACHE="${M2_CACHE:-/private/tmp/jenkins-azure-container-agents-m2}"
OUT_DIR="${OUT_DIR:-$ROOT/dist}"

if [[ -n "${WORK_DIR:-}" ]]; then
  checkout="$WORK_DIR"
  cleanup=false
else
  checkout="$(mktemp -d "${TMPDIR:-/tmp}/azure-container-agents-uami.XXXXXX")"
  cleanup=true
fi
if $cleanup; then
  trap 'rm -rf "$checkout"' EXIT
fi

git clone --quiet --depth 1 --branch "$UPSTREAM_TAG" "$UPSTREAM_URL" "$checkout"
actual_commit="$(git -C "$checkout" rev-parse HEAD)"
if [[ "$actual_commit" != "$UPSTREAM_COMMIT" ]]; then
  echo "upstream commit mismatch: expected $UPSTREAM_COMMIT, got $actual_commit" >&2
  exit 1
fi
git -C "$checkout" apply --check "$ROOT/exact-uami.patch"
git -C "$checkout" apply "$ROOT/exact-uami.patch"

mkdir -p "$M2_CACHE"
docker run --rm \
  -v "$checkout:/workspace" \
  -v "$M2_CACHE:/root/.m2" \
  -w /workspace \
  "$MAVEN_IMAGE" \
  mvn -B -DskipITs -Dchangelist="$PLUGIN_VERSION" test hpi:hpi

artifact="$(find "$checkout/target" -maxdepth 1 -type f -name '*.hpi' -print -quit)"
if [[ -z "$artifact" ]]; then
  echo "build succeeded without producing an HPI" >&2
  exit 1
fi
mkdir -p "$OUT_DIR"
output="$OUT_DIR/azure-container-agents-${UPSTREAM_TAG}-exact-uami.hpi"
cp "$artifact" "$output"
sha256sum "$output"
printf 'HPI=%s\n' "$output"
