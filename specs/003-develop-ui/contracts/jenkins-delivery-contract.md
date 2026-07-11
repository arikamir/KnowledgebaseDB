# Jenkins Delivery Contract

## Purpose

The root Declarative `Jenkinsfile` is the CI/CD entry point for UI, BFF, and
core. It orchestrates versioned scripts and must not duplicate release policy in
job configuration or inline Groovy.

## Trigger and reference policy

- Pull requests and unprotected refs may validate but cannot authenticate to
  Azure for publication or deployment.
- Only an explicitly configured protected main/release ref may publish and
  promote. Manual rebuild-all and recovery actions are parameterized, audited,
  and unavailable to untrusted builds.
- A delivery attempt begins only after Jenkins accepts a protected-ref trigger
  and assigns a build identifier. A source-control/webhook trigger that cannot
  be accepted because the controller is unavailable is not a delivery attempt
  and remains visible in the source-control or webhook-delivery audit.
- A target-environment lock and milestone reject concurrent or stale promotion.
- A controller or agent failure before the first environment mutation leaves
  desired state unchanged. A failure or abort after a mutation initiates
  attempt-wide reverse rollback before the accepted attempt is finalized.

## Change plan

`scripts/ci/detect-changes.sh` compares the revision with an explicit merge base
and emits immutable `change-plan.json`:

```json
{
  "sourceRevision": "<full-git-sha>",
  "baselineRevision": "<full-git-sha>",
  "services": {"ui": true, "bff": false, "core": false},
  "reason": ["ui/**"]
}
```

- `ui/**` selects UI; `bff/**` selects BFF; core source, Python dependency,
  migration, and core test paths select core.
- Shared contracts select their producers and consumers. Common CI/build files,
  base toolchains, an unknown/empty baseline, or an explicit audited rebuild-all
  conservatively select all services.
- Documentation-only changes select no image and cannot publish or deploy.
- Every later stage consumes the archived plan; no stage recalculates scope.

## Required stage state machine

```text
checkout -> change plan -> parallel validation -> compatibility gate
         -> parallel build/scan/publish -> pre-promotion evidence -> promotion gate
         -> snapshot -> core -> evidence checkpoint -> BFF -> evidence checkpoint
         -> UI -> verify -> final evidence
```

- Only selected validation and image lanes run. Each lane uses an isolated,
  ephemeral agent/container and publishes test, scan, and SBOM results.
- Failed or unstable validation, compatibility, scan, identity, or digest
  integrity stops the pipeline before promotion.
- Build each selected image once. Promotion reuses its recorded digest and may
  never rebuild it.
- Deploy selected services in `core -> BFF -> UI` order. Each rollout, health,
  smoke, and producer/consumer compatibility check must pass before the next.
- Required evidence available at each gate is published before the next
  environment mutation. Evidence-publication failure blocks that mutation and,
  when an earlier mutation occurred, initiates attempt-wide reverse rollback.

## Release manifest

The protected build fingerprints and archives a non-secret
`release-manifest.json`:

```json
{
  "sourceRevision": "<full-git-sha>",
  "jenkins": {"buildNumber": "42", "buildUrl": "https://jenkins/job/42/"},
  "createdAt": "2026-07-11T12:00:00Z",
  "services": {
    "ui": {
      "image": "registry.azurecr.io/career-ui@sha256:<digest>",
      "contractVersion": "1.x",
      "sbomRef": "<artifact-reference>",
      "scanRef": "<artifact-reference>"
    }
  }
}
```

Every selected image value must match `repository@sha256:<digest>`; tags are
rejected. The manifest contains all selected services and preserves the current
digests of unselected services in the promotion snapshot.

## Jenkins execution and Azure identity boundary

- The controller is available only at `http://localhost:8080` and is not an
  Entra OIDC issuer.
- The existing Jenkins Azure cloud node named `azure` provisions and connects
  ephemeral ACI agents in the configured resource group.
- Cloud `azure` uses its existing controller-held service principal only for
  ACI lifecycle and approved identity attachment. It must have no ACR push or
  AKS deployment permission, and its tenant, subscription, resource-group
  scope, credential expiry, and denied data-plane permissions are preflighted.
- Publication runs only on the `azure-aci-publisher` template using its
  ACR-scoped user-assigned managed identity. Promotion, deployment,
  verification, and rollback run only on `azure-aci-deployer` using its
  AKS-scoped user-assigned managed identity.
- The pipeline fails before publication when agent identity, subscription,
  tenant, ACR, or AKS scope differs from the declared environment.
- Jenkins stores no Azure application-delivery credential or kubeconfig beyond
  the existing cloud-provisioning service-principal credential. That credential
  is scoped, rotated, and audited separately from application delivery.
- Cloud-agent provisioning or connection failure stops before Azure
  authentication or publication and cannot fall back to a local agent.

## ACI template identity binding

| Jenkins cloud | Template | Required identity | Permitted stages |
|---|---|---|---|
| `azure` | `azure-aci-publisher` | Publisher UAMI | Build, scan, ACR push, digest resolution, publication evidence |
| `azure` | `azure-aci-deployer` | Deployer UAMI | Promotion, migration, AKS deployment, verification, rollback, deployment evidence |

Each template declares exactly its expected user-assigned managed identity.
System-assigned identity and additional user-assigned identities are prohibited.
Preflight compares the running container group's identity resource IDs with the
expected Terraform outputs before Azure CLI authentication.

## Provisioning credential lifecycle

- Credential owner: platform operations.
- Credential update authority: a dedicated least-privilege Jenkins
  credential-manager role usable only through the localhost administrative
  interface and restricted to the stable credential entry used by cloud
  `azure`; general job operators, evidence readers, and ACI agents cannot use it.
- Maximum rotation interval: 90 days.
- Expiry alerts: 30, 14, and 7 days.
- Failure to acknowledge the 30-day alert prohibits protected-branch promotion;
  the 14-day and 7-day alerts escalate to the platform-operations incident
  channel.
- Promotion is prohibited when fewer than 30 valid days remain.
- Replacement acceptance requires successful publisher and deployer ACI
  provisioning plus identity-boundary checks.
- Replacement secret material is accepted only through protected standard input
  or an inherited file descriptor and never appears in command arguments,
  environment variables, repository files, retained temporary files, API
  responses, or logs.
- Emergency revocation disables ordinary build provisioning and cannot fall
  back to another Azure credential. Only an audited, quarantined
  rotation-validation path may provision publisher and deployer smoke agents;
  ordinary provisioning remains disabled until both templates pass.

## Failure and rollback invariants

- A failure before environment promotion changes no deployed service digest.
- Before the first environment mutation, record the current UI, BFF, and core
  digests as the immutable pre-attempt snapshot and track each service changed
  by the accepted attempt.
- If a rollout, health, compatibility, evidence, Jenkins, agent, or Azure
  dependency failure occurs after a mutation, stop downstream deployment and
  restore every service changed by the attempt in reverse deployment order
  (`UI -> BFF -> core` for a full three-service attempt).
- Verify every restored digest and the resulting producer/consumer
  compatibility before finalizing the attempt. Services not changed by the
  attempt remain untouched.
- If attempt-wide rollback cannot restore the snapshot, fail closed and require
  an explicitly approved recovery plan. Never automatically reverse a
  destructive database migration; migrations must use expand-first evolution
  so image rollback remains compatible with the retained schema.

## Required evidence and tests

Immediately after Jenkins accepts the trigger and assigns the build identifier,
create a minimal non-authoritative controller audit record with build ID, source
revision, start time, `result=pending`, and `failedStage=null`. Create it before
requesting an ACI agent. Finalize it exactly once with completion time, terminal
result, and the failed stage or `none`; agent-provisioning, evidence, and
rollback failures are terminal stages rather than missing records.

Once an authenticated delivery agent starts, publish/fingerprint change and
release manifests, JUnit results, digest resolution, scan/SBOM summaries,
before/after deployment snapshots, rollout and smoke logs, and rollback results
in the authoritative Azure Storage container. Failure to publish evidence
required by the next gate blocks the next environment mutation; if an earlier
mutation occurred, it initiates attempt-wide rollback. Controller-local archives
are non-authoritative convenience copies. Exclude credentials and personal data.

Pipeline tests cover UI-only, BFF-only, core-only, shared/all, docs-only, and
first-build change plans; validation failure with zero promotion; tag rejection;
deployment order; injected rollout rollback; stale/concurrent build rejection;
identity/RBAC denial; pending-to-terminal controller-audit transitions;
attempt-wide reverse rollback; and evidence completeness.

## Evidence retention contract

- Authoritative store: dedicated Azure Storage container.
- Immutable path: `deliveries/<environment>/<build-id>/<stage>/<artifact>`;
  every upload uses `If-None-Match: *`.
- Enforcement: custom writer role without blob read, list, tag-mutation, or
  delete operations; Azure ABAC conditions restrict the environment/stage
  prefix; the container applies a default version-level immutability policy to
  each accepted version. A writer cannot successfully replace or delete an
  accepted evidence version even when the conditional header is omitted or a
  bypass is attempted.
- Normal retention: 90 days.
- Incident hold: total retention may extend to no later than 180 days from
  evidence creation and records owner, reason, incident reference, start, and
  expiry.
- Readers: the separately configured Delivery Operators and Security Reviewers
  Microsoft Entra groups only.
- Hold managers: a separately configured Evidence Hold Managers Microsoft Entra
  group alone may create, extend, or release holds; every transition is audited,
  and reader membership alone grants no hold-management authority.
- Writers: the stage-appropriate publisher/deployer managed identity has
  path-scoped write access with no general read, list, tag-mutation, or delete
  access; conditional creation plus default version immutability guarantees the
  required no-successful-replacement outcome.
- Prohibited content: credentials, kubeconfigs, tokens, raw identity claims,
  personal learning data, and unredacted logs.
