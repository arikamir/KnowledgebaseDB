# Azure Container Agents exact-UAMI patch

This directory carries the minimal reviewed delta required for Jenkins ACI
templates to attach an exact user-assigned managed identity to the generated
container group. The upstream plugin is not vendored.

- Upstream: `https://github.com/jenkinsci/azure-container-agents-plugin.git`
- Release: `372.v073266fff4a_7`
- Commit: `073266fff4a73604454654e2e20bdac52cfea6dc`
- Build image: `maven:3.9.11-eclipse-temurin-21@sha256:6fdc855a6ed81d288ca7ca37ac6ff5e9308b612485c0801d70b25a858c83d237`

Run `./build.sh`. It clones the exact upstream commit, verifies it, applies
`exact-uami.patch`, runs the complete unit-test suite, and copies the HPI to
`dist/`. Set `WORK_DIR` to retain the upstream checkout or `OUT_DIR` to select
another artifact directory.

The patch intentionally preserves identityless behavior when neither identity
mode is configured. Protected-delivery configuration continues to prohibit
system-assigned identity and supplies exactly one reviewed UAMI.
