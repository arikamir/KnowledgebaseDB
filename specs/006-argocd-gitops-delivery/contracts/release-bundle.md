# Contract: Pre-declaration Release Bundle

**Schema**: `config/gitops-release-bundle.schema.json`  
**Validator**: `scripts/ci/validate-release-bundle.sh`  
**Producer**: `scripts/ci/write-gitops-release.sh`

The release bundle is the CI hand-off produced after all image, scan, contract,
and compatibility checks. It is validated before the GitOps release
declaration is generated.

Required fields are:

- explicit environment `nonprod`;
- normalized SemVer 2 `releaseVersion` and its protected `sourceTag`;
- lowercase 40-character `sourceRevision` matching the protected tag commit;
- originating CI run identifier, repository, and workflow;
- exactly three ACR `repository@sha256:<64-hex>` image references for UI, BFF,
  and Core; and
- non-secret links to contract, scan, and compatibility evidence.

The validator fails closed when the tag is not proven protected, the tag and
source revision differ, a version is reused for another source revision, a
service is missing, a mutable image reference is supplied, or credential-shaped
content appears anywhere in the bundle.

