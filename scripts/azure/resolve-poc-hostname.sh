#!/usr/bin/env bash
set -euo pipefail

frontend_fqdn="${1:-}"
[[ "$frontend_fqdn" =~ ^[A-Za-z0-9.-]+$ ]] || {
  printf 'usage: %s <agc-frontend-fqdn>\n' "$0" >&2
  exit 2
}

command -v dig >/dev/null 2>&1 || {
  printf 'PoC hostname: dig is required\n' >&2
  exit 1
}

frontend_ip="$(dig +short A "$frontend_fqdn" | awk '/^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ { print; exit }')"
[[ "$frontend_ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || {
  printf 'PoC hostname: AGC frontend has no IPv4 address yet: %s\n' "$frontend_fqdn" >&2
  exit 1
}

IFS=. read -r octet1 octet2 octet3 octet4 <<<"$frontend_ip"
for octet in "$octet1" "$octet2" "$octet3" "$octet4"; do
  ((octet >= 0 && octet <= 255)) || {
    printf 'PoC hostname: invalid frontend IPv4 address: %s\n' "$frontend_ip" >&2
    exit 1
  }
done

printf 'career-agent.%s.sslip.io\n' "$frontend_ip"
