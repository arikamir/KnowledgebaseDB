# Jenkins Azure validation cloud

The Jenkinsfile uses `agent none`. Every source revision allocates only the
one-shot `azure-aci-validator` label for checkout and the identical non-Azure
suite in `scripts/ci/validate-non-azure.sh`. No controller, built-in, or
local-agent fallback is permitted.

## Configure the validator template

An administrator first configures the Jenkins Azure Container Agents cloud
named `azure`. Set `VALIDATOR_IMAGE` to a reviewed, immutable
`repository@sha256:<digest>` validator image, then execute
`scripts/jenkins/configure-validator-agent.groovy` through the authenticated,
localhost-only Jenkins Script Console/API. The script replaces only the
validator template and preserves the other templates in the cloud.

The validator has no system-assigned or user-assigned managed identity, Azure
credential environment, ports, or volumes. Its image is digest-pinned and its
retention strategy removes the container after one build.

## Pipeline confinement

All refs run checkout, change planning, contract drift, lint, type checking,
unit, contract, and non-Azure integration tests on `azure-aci-validator`.
Pull requests and unprotected refs stop after that suite. They cannot allocate
publisher/deployer agents or enter Azure login, publishing, evidence,
migration, promotion, deployment, verification, or rollback stages.

Protected revisions may continue only after their independent authorization
and live preflight gates allocate the separately scoped publisher/deployer
templates. No controller, built-in, or local-agent fallback is allowed when
ACI provisioning or validation fails.

## Verify after configuration

Export the live `azure-aci-validator` template to a non-secret JSON document
with the fields defined by `config/jenkins-validator-policy-v1.json`, then run:

```text
scripts/jenkins/verify-validator-agent.sh \
  --template-json /path/to/validator-template.json
```

Run the same command with `--runtime` inside a disposable validator agent. It
also rejects Azure/ARM/Kubernetes delivery environment variables and proves
that the Azure instance metadata identity endpoint does not issue a token.
Any verification failure quarantines the template; it never enables fallback
or delivery permission.
