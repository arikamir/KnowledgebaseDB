# Legacy Jenkins Azure validation cloud

GitHub Actions is now the authoritative CI/CD orchestrator. This document and
the Jenkins assets it describes are retained only for migration and audit
history; new delivery configuration must use
`docs/github-actions-azure.md` and `.github/workflows/`.

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

## Configure protected-delivery templates

Only after the sole Platform Operations finalizer has emitted the fresh,
reviewed `config/platform-bootstrap-nonprod.json`, set
`PLATFORM_BOOTSTRAP_MANIFEST` to that file and set `PUBLISHER_IMAGE` and
`DEPLOYER_IMAGE` to reviewed `repository@sha256:<digest>` references. Run
`scripts/jenkins/configure-publisher-deployer-agents.groovy` through the same
authenticated administrator channel used for the validator configuration.

The script binds `azure-aci-publisher` to exactly `identities.publisher` and
`azure-aci-deployer` to exactly `identities.deployer` from the reviewed
manifest. It also retargets the cloud's ACI resource group to the manifest's
reviewed `resourceGroup`; this prevents a retained controller configuration
from provisioning agents into an earlier region. The provisioning credential
must already pass its scope and expiry verification for that target group.
Its custom `Jenkins ACI Provisioner` role is maintained by
`scripts/azure/configure-jenkins-aci-provisioner-role.sh`; the role includes
resource-group-scoped ARM deployment lifecycle actions because the plugin
creates container groups through `Microsoft.Resources/deployments`, plus only
the required ACI group lifecycle and log-read actions.
Both templates reject cross-subscription/resource-group, system-assigned, or
additional identities, use one-shot
agents, expose no credential volumes or environment, and have no Terraform
capability. The existing `azure-aci-validator` remains identityless. Publisher
and deployer permissions come only from their Azure UAMIs: publisher has exact
ACR/evidence publication authority, while deployer has exact AKS/evidence
delivery authority and Reader only on the target application resource group.
Neither identity may read Terraform state, Key Vault secret values, ACR
content, Redis data, or PostgreSQL data, and they cannot assume one another.

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

After the publisher/deployer templates are configured, export the non-secret
template shapes, running ACI identity attachments, reference/stage request,
exact positive assignments, and denial results. Validate them against the
same reviewed manifest with `scripts/jenkins/verify-aci-identity-binding.sh`.
That command is a mandatory post-finalization gate; a missing, swapped,
additional, or system-assigned identity, an unauthorized reference or stage,
or any assignment/denial drift blocks protected delivery.

For the approved single-administrator technical PoC only, an administrator may
configure and verify the same exact template bindings from a `poc-reviewed`
manifest by setting `ALLOW_TECHNICAL_POC=true` and passing
`--allow-technical-poc` to the verifier. Both PoC attestations must explicitly
record `formalT194: false`. This exception configures templates but does not
unblock the Jenkinsfile: the protected live preflight continues to require a
formal `reviewed` T194 manifest.

The controller plugin must expose template-level system-assigned and
user-assigned identity setters. Configuration fails before replacing the cloud
when those APIs are absent. The upstream `azure-container-agents` release
`372.v073266fff4a_7` does not expose them. The reviewed, pinned patch and
reproducible build in `vendor/jenkins/azure-container-agents-uami/` add only
those template properties and the corresponding ARM container-group identity
block. Its tests prove that the default template remains identityless and that
an exact UAMI renders as `UserAssigned` without a system identity. Install the
built HPI and verify the live plugin methods before enabling protected-delivery
templates.

To install it through the authenticated, localhost-only Jenkins Script Console,
set the HPI path and digest from the reproducible build, then evaluate
`scripts/jenkins/install-azure-container-agents-uami.groovy`:

```sh
export AZURE_CONTAINER_AGENTS_UAMI_HPI="$PWD/vendor/jenkins/azure-container-agents-uami/dist/azure-container-agents-372.v073266fff4a_7-exact-uami.hpi"
export AZURE_CONTAINER_AGENTS_UAMI_SHA256="$(sha256sum "$AZURE_CONTAINER_AGENTS_UAMI_HPI" | cut -d' ' -f1)"
```

The installer rejects a different filename, digest, plugin short name, or
version, and refuses to replace an existing unreviewed plugin. Restart Jenkins
after installation, then rerun `configure-publisher-deployer-agents.groovy`.

The Jenkins global URL must be reachable from Azure Container Instances. A
local-lab URL such as `http://localhost:8080/` causes inbound agents to retry
forever because `localhost` resolves inside the ACI container. The Pipeline
SCM URL must likewise be a Git endpoint reachable from the ACI subnet; a
controller-local `file://` checkout is suitable only for loading the Jenkinsfile
and cannot supply source to an ephemeral Azure agent.
