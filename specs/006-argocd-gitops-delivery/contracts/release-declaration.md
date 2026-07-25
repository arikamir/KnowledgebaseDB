# Contract: Release Declaration

**Path**: `deploy/argocd/environments/<environment>/release.json`  
**Schema**: `config/argocd-release.schema.json`  
**Validator**: `scripts/ci/validate-gitops-release.sh`

The declaration is generated from a protected SemVer `v*` tag. The normalized
tag version must equal `releaseVersion`, and the tag must point to
`sourceRevision`; CI must verify the effective tag-protection gate. The
normalized version must not have been used for a different source revision in
repository history or the protected release ledger. The generated file is
submitted through a bot-branch pull request whose required Copilot status is
verified before merge to protected `main`.

## Valid document

```json
{
  "schemaVersion": 1,
  "environment": "nonprod",
  "releaseVersion": "0.1.0",
  "sourceRevision": "0123456789abcdef0123456789abcdef01234567",
  "services": {
    "ui": { "image": "registry.azurecr.io/ui@sha256:<64-hex>" },
    "bff": { "image": "registry.azurecr.io/bff@sha256:<64-hex>" },
    "core": { "image": "registry.azurecr.io/core@sha256:<64-hex>" }
  }
}
```

The actual declaration must contain concrete lower-case digests; placeholders
above are illustrative only. Additional keys, mutable tags, missing services,
unsupported environments, malformed SemVer, duplicate versions, and credential
strings are invalid. The first implementation accepts only the explicit
`nonprod` target. The containing directory is part of the contract and must
match `environment`.

## Producer and consumer

- CI produces the candidate after image scans and compatibility checks.
- A protected GitHub review approves the change to `main`.
- ApplicationSet reads the declaration and supplies only the three image values
  plus release metadata to the generated Argo Application.
- No secret, token, client credential, kubeconfig, Terraform state, or learner
  data may be included.
