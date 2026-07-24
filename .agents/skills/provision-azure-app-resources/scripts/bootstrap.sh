#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$(pwd)}"
skill_root="$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$repo_root/infra/azure"
template="$skill_root/assets/terraform"

if [ -e "$target" ]; then
  echo "[azure-infra] Reusing existing $target; no files overwritten"
  exit 0
fi

mkdir -p "$repo_root/infra"
mkdir -p "$target"
for file in versions.tf variables.tf main.tf jenkins-agent-identities.tf delivery-evidence-storage.tf outputs.tf terraform.tfvars.example .gitignore .terraform.lock.hcl; do
  [[ -f "$template/$file" ]] && cp "$template/$file" "$target/$file"
done

if command -v terraform >/dev/null 2>&1; then
  terraform -chdir="$target" fmt
fi

echo "[azure-infra] Created deterministic Terraform foundation at $target"
echo "[azure-infra] Copy terraform.tfvars.example to an ignored terraform.tfvars and set the subscription plus configured evidence-reader group IDs"
