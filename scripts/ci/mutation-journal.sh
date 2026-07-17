#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-}"; [[ -n "$ACTION" ]] || exit 2; shift
JOURNAL_DIR="" ATTEMPT="" ENVIRONMENT="" SNAPSHOT="" EVENT="" SERVICE="" PREVIOUS_IMAGE="" INTENDED_IMAGE=""
RESULT="" COMPENSATION_ATTEMPT="" ELAPSED_SECONDS="" ACTOR="automation"
while (($#)); do
  case "$1" in
    --journal-dir) JOURNAL_DIR="${2:-}"; shift 2 ;;
    --attempt) ATTEMPT="${2:-}"; shift 2 ;;
    --environment) ENVIRONMENT="${2:-}"; shift 2 ;;
    --snapshot) SNAPSHOT="${2:-}"; shift 2 ;;
    --event) EVENT="${2:-}"; shift 2 ;;
    --service) SERVICE="${2:-}"; shift 2 ;;
    --previous-image) PREVIOUS_IMAGE="${2:-}"; shift 2 ;;
    --intended-image) INTENDED_IMAGE="${2:-}"; shift 2 ;;
    --result) RESULT="${2:-}"; shift 2 ;;
    --compensation-attempt) COMPENSATION_ATTEMPT="${2:-}"; shift 2 ;;
    --elapsed-seconds) ELAPSED_SECONDS="${2:-}"; shift 2 ;;
    --actor) ACTOR="${2:-}"; shift 2 ;;
    *) exit 2 ;;
  esac
done

fail() { printf 'mutation journal: %s\n' "$1" >&2; exit 1; }
[[ "$ATTEMPT" =~ ^[A-Za-z0-9._-]{3,128}$ && -n "$JOURNAL_DIR" ]] || fail "invalid attempt"
command -v jq >/dev/null || fail "jq required"
mkdir -p "$JOURNAL_DIR"; chmod 0700 "$JOURNAL_DIR"
JOURNAL="$JOURNAL_DIR/$ATTEMPT.jsonl"
SNAPSHOT_COPY="$JOURNAL_DIR/$ATTEMPT.snapshot.json"

verify_chain() {
  [[ -f "$JOURNAL" ]] || fail "journal missing"
  local previous expected actual base line
  previous="$(printf '0%.0s' {1..64})"
  while IFS= read -r line; do
    jq -e . >/dev/null <<<"$line" || fail "invalid journal event"
    actual="$(jq -r '.eventHash' <<<"$line")"
    [[ "$(jq -r '.previousHash' <<<"$line")" == "$previous" ]] || fail "journal chain broken"
    base="$(jq -cS 'del(.eventHash)' <<<"$line")"
    expected="$(printf '%s' "$base" | shasum -a 256 | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] || fail "journal event modified"
    previous="$actual"
  done < "$JOURNAL"
  expected_snapshot="$(head -n 1 "$JOURNAL" | jq -r '.snapshotDigest // empty')"
  if [[ -n "$expected_snapshot" ]]; then
    [[ -f "$SNAPSHOT_COPY" && "sha256:$(shasum -a 256 "$SNAPSHOT_COPY" | awk '{print $1}')" == "$expected_snapshot" ]] || fail "snapshot modified"
  fi
}

append_event() {
  verify_chain
  local previous base hash at
  previous="$(tail -n 1 "$JOURNAL" | jq -r '.eventHash')"
  at="${JOURNAL_NOW:-$(date -u '+%Y-%m-%dT%H:%M:%SZ')}"
  base="$(jq -cnS --arg event "$EVENT" --arg attempt "$ATTEMPT" --arg at "$at" --arg actor "$ACTOR" \
    --arg service "$SERVICE" --arg previousImage "$PREVIOUS_IMAGE" --arg intendedImage "$INTENDED_IMAGE" \
    --arg result "$RESULT" --arg compensationAttempt "$COMPENSATION_ATTEMPT" --arg elapsed "$ELAPSED_SECONDS" \
    --arg previousHash "$previous" '
    {schemaVersion:1,event:$event,attemptId:$attempt,at:$at,actor:$actor,
     service:(if $service=="" then null else $service end),
     previousImage:(if $previousImage=="" then null else $previousImage end),
     intendedImage:(if $intendedImage=="" then null else $intendedImage end),
     compensationAttempt:(if $compensationAttempt=="" then null else ($compensationAttempt|tonumber) end),
     result:(if $result=="" then null else $result end),
     elapsedSeconds:(if $elapsed=="" then null else ($elapsed|tonumber) end),previousHash:$previousHash}')"
  hash="$(printf '%s' "$base" | shasum -a 256 | awk '{print $1}')"
  jq -cS --arg hash "$hash" '. + {eventHash:$hash}' <<<"$base" >> "$JOURNAL"
  chmod 0600 "$JOURNAL"
}

case "$ACTION" in
  init)
    [[ "$ENVIRONMENT" =~ ^[a-z0-9][a-z0-9._-]{1,62}$ && -f "$SNAPSHOT" && ! -e "$JOURNAL" && ! -e "$SNAPSHOT_COPY" ]] || fail "invalid or duplicate initialization"
    jq -e 'keys==["environment","services"] and (.services|keys==["bff","core","ui"]) and
      all(.services[]; test("^[a-z0-9.-]+\\.azurecr\\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$"))' "$SNAPSHOT" >/dev/null || fail "invalid complete snapshot"
    cp "$SNAPSHOT" "$SNAPSHOT_COPY"; chmod 0444 "$SNAPSHOT_COPY"
    previous="$(printf '0%.0s' {1..64})"; at="${JOURNAL_NOW:-$(date -u '+%Y-%m-%dT%H:%M:%SZ')}"; snapshot_digest="sha256:$(shasum -a 256 "$SNAPSHOT_COPY" | awk '{print $1}')"
    base="$(jq -cnS --arg attempt "$ATTEMPT" --arg at "$at" --arg environment "$ENVIRONMENT" --arg previousHash "$previous" --arg snapshotDigest "$snapshot_digest" \
      '{schemaVersion:1,event:"initialized",attemptId:$attempt,at:$at,actor:"automation",service:null,previousImage:null,intendedImage:null,compensationAttempt:null,result:$environment,elapsedSeconds:null,previousHash:$previousHash,snapshotDigest:$snapshotDigest}')"
    hash="$(printf '%s' "$base" | shasum -a 256 | awk '{print $1}')"
    jq -cS --arg hash "$hash" '. + {eventHash:$hash}' <<<"$base" > "$JOURNAL"; chmod 0600 "$JOURNAL"
    ;;
  append)
    [[ "$EVENT" =~ ^(forward_planned|forward_completed|forward_verified|forward_failed|reverse_attempt|reverse_verified|reverse_failed|recovery_approved|terminal)$ ]] || fail "invalid event"
    [[ -z "$SERVICE" || "$SERVICE" =~ ^(ui|bff|core)$ ]] || fail "invalid service"
    append_event
    ;;
  verify) verify_chain ;;
  *) exit 2 ;;
esac
