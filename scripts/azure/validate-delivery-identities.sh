#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODE="live" MANIFEST="" REPORT="" POLICY="$ROOT/config/delivery-identity-boundaries-v1.json"
usage() { printf 'Usage: %s [--mode contract|live] --manifest FILE --report FILE [--policy FILE]\n' "$0" >&2; exit 2; }
while (($#)); do case "$1" in
  --mode) MODE="${2:-}"; shift 2;; --manifest) MANIFEST="${2:-}"; shift 2;;
  --report) REPORT="${2:-}"; shift 2;; --policy) POLICY="${2:-}"; shift 2;; *) usage;; esac; done
[[ "$MODE" =~ ^(contract|live)$ && -f "$MANIFEST" && -f "$REPORT" && -f "$POLICY" ]] || usage

preflight_mode=schema-digest; [[ "$MODE" == live ]] && preflight_mode=live
"$ROOT/scripts/azure/preflight-ui-platform.sh" "$preflight_mode" --repo-root "$ROOT" --manifest "$MANIFEST" >/dev/null

jq -e --argjson manifest "$(cat "$MANIFEST")" --slurpfile policy "$POLICY" '
  .schemaVersion == 1 and
  .manifestConfigurationDigest == $manifest.configuration.digest and
  (.actors | keys) == ($policy[0].actors | keys) and
  all(.actors | to_entries[];
    .key as $actor | .value as $actual | $policy[0].actors[$actor] as $expected |
    ($actual | keys) == ["allowed", "denied", "identityResourceId"] and
    ($actual.allowed | sort) == ($expected.allowed | sort) and
    ($actual.denied | sort) == ($expected.denied | sort) and
    if $expected.source == "identityless" then $actual.identityResourceId == null
    elif $expected.source == "external-jenkins-cloud-provisioner" then
      ($actual.identityResourceId == ("/subscriptions/" + $manifest.subscriptionId + "/resourceGroups/" + $manifest.resourceGroup + "/providers/Microsoft.ManagedIdentity/userAssignedIdentities/jenkins-cloud-provisioner"))
    else
      ($expected.source | split(".")) as $path |
      $actual.identityResourceId == ($manifest | getpath($path))
    end) and
  ([.actors[] | .identityResourceId | select(. != null)]) as $ids |
  (($ids | length) == ($ids | unique | length)) and
  (.actors.controller.identityResourceId != $manifest.identities.publisher) and
  (.actors.controller.identityResourceId != $manifest.identities.deployer)
' "$REPORT" >/dev/null || { printf 'delivery identity validation failed: scope, actor, positive, denial, digest, or cross-role drift\n' >&2; exit 1; }

jq -cn --arg mode "$MODE" --arg digest "$(jq -r '.configuration.digest' "$MANIFEST")" \
  '{schemaVersion:1,status:"delivery-identities-valid",mode:$mode,configurationDigest:$digest,crossRoleDenials:true}'
