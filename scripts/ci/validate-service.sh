#!/usr/bin/env bash
set -euo pipefail

plan=""
selection_type=""
selection=""

fail() {
  printf 'validate-service: %s\n' "$1" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --plan) plan="${2:-}"; shift 2 ;;
    --service) selection_type="service"; selection="${2:-}"; shift 2 ;;
    --lane) selection_type="lane"; selection="${2:-}"; shift 2 ;;
    --) shift; break ;;
    *) fail "unknown argument: $1" ;;
  esac
done

[[ -f "$plan" ]] || fail "--plan must name an archived change plan"
[[ -n "$selection_type" && -n "$selection" ]] || fail "select exactly one service or validation lane"
[[ $# -gt 0 ]] || fail "a dispatch command is required"
command -v jq >/dev/null || fail "jq is required"

jq -e '
  (keys | sort) == ["baselineRevision", "reason", "services", "sourceRevision", "validationLanes"] and
  (.sourceRevision | type == "string" and test("^[0-9a-f]{40}$")) and
  (.baselineRevision == null or (.baselineRevision | type == "string" and test("^[0-9a-f]{40}$"))) and
  (.services | keys | sort) == ["bff", "core", "ui"] and
  ([.services[] | type] | all(. == "boolean")) and
  (.validationLanes | keys | sort) == ["contractIntegrity", "infrastructure", "performanceProfile", "readinessScenarios"] and
  ([.validationLanes[] | type] | all(. == "boolean")) and
  (.validationLanes.contractIntegrity == true) and
  (.reason | type == "array" and all(.[]; type == "string"))
' "$plan" >/dev/null || fail "change plan schema is invalid"

case "$selection_type:$selection" in
  service:ui|service:bff|service:core)
    selected=$(jq -r --arg key "$selection" '.services[$key]' "$plan") ;;
  lane:contractIntegrity|lane:readinessScenarios|lane:performanceProfile|lane:infrastructure)
    selected=$(jq -r --arg key "$selection" '.validationLanes[$key]' "$plan") ;;
  *) fail "unknown selection: $selection" ;;
esac

if [[ "$selected" == "true" ]]; then
  exec "$@"
fi

exit 0
