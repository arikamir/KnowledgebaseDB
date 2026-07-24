# Jenkins Delivery Contract

## Purpose

The root Declarative `Jenkinsfile` is the CI/CD entry point for UI, BFF, and
core. It orchestrates versioned scripts and must not duplicate release policy in
job configuration or inline Groovy.

## Trigger and reference policy

- Every ref runs checkout, change planning, authored-contract/catalog drift,
  lint, typecheck, unit, contract, and non-Azure integration validation on the
  identityless `azure-aci-validator` template. Pull requests and unprotected
  refs stop after those gates and cannot request publisher/deployer agents or
  authenticate to Azure.
- Only an explicitly configured protected main/release ref may publish and
  promote. Manual rebuild-all and recovery actions are parameterized, audited,
  and unavailable to untrusted builds. Only a member of the configured Jenkins
  `Delivery Recovery Operators` role may request either action, and a distinct
  member of the Platform Operations approver group must approve it before an
  agent is allocated. The requester cannot approve their own action. The audit
  records both identities, reason, source revision, selected environment,
  declared service scope, and recovery reference. Rebuild-all may run the
  ordinary validation/publish/delivery state machine only; recovery may run
  read-only diagnosis and the bounded rollback/reconciliation stages only and
  cannot bypass compatibility, identity, evidence, or environment-lock gates.
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
  "validationLanes": {
    "contractIntegrity": true,
    "readinessScenarios": false,
    "performanceProfile": false,
    "infrastructure": false
  },
  "reason": ["ui/**"]
}
```

- All four `validationLanes` keys are mandatory booleans:
  `contractIntegrity` dispatches the gate implemented by T034,
  `readinessScenarios` dispatches T156, `performanceProfile` dispatches
  T157, and `infrastructure` dispatches the infrastructure/static/live
  validation selected for that change. The archived plan, not path
  recalculation, is the sole input to each dispatcher.
- `sourceRevision` is always a full resolved Git object ID.
  `baselineRevision` is a full resolved Git object ID when an accepted baseline
  exists and JSON `null` only for a genuine first build or authenticated
  baseline lookup that returns no prior baseline. The field is never omitted and
  uses no string sentinel. A null baseline forces all services and validation
  lanes to `true` and adds `missing-baseline` to `reason`; a malformed,
  abbreviated, or explicitly supplied but unresolvable revision fails closed
  instead of becoming null.
- The classifier starts every service and lane at `false`, then boolean-ORs
  every changed path's selections; no rule can clear an earlier selection.
  `contractIntegrity` is finally forced to `true` for every ref, and `reason`
  retains the sorted unique matching path/rule identifiers.
- `ui/**` selects UI; `bff/**` selects BFF; core source, Python dependency,
  migration, and core test paths select core.
- `specs/003-develop-ui/contracts/bff-api-v1.openapi.yaml` selects UI and BFF;
  `contractIntegrity` validation plus checked-in BFF-route-validator and
  UI-client/type/validator drift must pass before generation, UI/BFF tests, or
  image builds.
- `specs/003-develop-ui/contracts/core-api-v1.openapi.yaml` selects BFF and core;
  `contractIntegrity` validation plus checked-in BFF core-client/type and
  core-validator drift must pass before generation, core/BFF tests, or image
  builds.
- `specs/003-develop-ui/contracts/supported-guidance-topics-v1.yaml` selects UI,
  BFF, core, and `contractIntegrity`; canonical-catalog validation and generated
  core-runtime plus BFF/UI consumer-catalog drift must pass before validation,
  performance fixtures, or image builds.
- `specs/003-develop-ui/contracts/implementation-readiness-contract.md`
  selects all three services and all four validation lanes because it is the
  normative source for cross-service, performance, and infrastructure outcomes.
- `specs/003-develop-ui/requirements-traceability.md` selects all three
  services, `contractIntegrity`, and `infrastructure`; T034 validates all
  124 rows and their affected task/evidence paths before any selected lane runs.
- `tests/fixtures/readiness-scenario-manifest-v1.yaml` selects UI, BFF, core,
  `contractIntegrity`, `readinessScenarios`, and `infrastructure`. T034 must
  first verify its manifest digest, derived per-case fixture digests, operation
  references, unique expanded case IDs, and denominator arithmetic; T156 then
  runs the exhaustive readiness suite across every selected service and
  external/deployed infrastructure case.
- `tests/performance/performance-profile-v1.json` selects UI, BFF, and core
  plus `contractIntegrity` and `performanceProfile`. T034 must first verify its
  full-profile and fixture-set digests, evidence schema, pinned BFF/core
  contract-byte digests, regenerated mapper digest/drift result, operation
  pairing, assignment, and timeout policy; T157 then runs the exact
  browser/BFF/core performance suite and retains all bound digests. Neither
  normative input may enter the documentation-only lane.
- Shared contracts select their producers and consumers. Common CI/build files,
  base toolchains, a genuine first/missing baseline represented as JSON `null`,
  or an explicit audited rebuild-all conservatively select all services. A
  genuine first/missing null baseline or audited rebuild-all also sets every
  validation lane to `true`.
- Executable/template changes under the mandatory provision/teardown Azure
  skills select infrastructure validation and all three services; they can
  never use the documentation-only lane.
- Documentation-only changes select no image and cannot publish or deploy;
  `contractIntegrity` remains `true` because every ref runs the canonical
  authored-contract/catalog/traceability gate, while the other lanes are
  `false`.
- Every later stage consumes the archived plan; no stage recalculates scope.

## Required stage state machine

```text
trusted controller audit -> identityless checkout/change plan
         -> canonical-contract/catalog-drift gate -> parallel non-Azure validation
         -> compatibility gate -> protected-ref/environment gate
         -> bootstrap-manifest consistency gate -> exact ACI identity-binding gate
         -> read-only platform preflight -> post-bootstrap delivery-identity validation
         -> parallel build/scan/publish -> pre-promotion evidence -> promotion gate
         -> snapshot -> schema compatibility -> in-cluster expand migration Job
         -> migration evidence
         -> core -> evidence checkpoint -> BFF -> evidence checkpoint
         -> UI -> verify -> final evidence
```

- Only selected validation and image lanes run. Each lane uses an isolated,
  ephemeral agent/container and publishes test, scan, and SBOM results.
- Failed or unstable validation, compatibility, scan, identity, or digest
  integrity stops the pipeline before promotion.
- Build each selected image once. Promotion reuses its recorded digest and may
  never rebuild it.
- Both canonical OpenAPI documents are validated before generated consumers are
  refreshed. CI regenerates into a temporary location and fails on drift in BFF
  route validators/core client/types, UI client/types/validators, or explicit
  BFF boundary mappings; committed output must carry the applicable BFF/core
  contract digest used by conformance tests.
- Deploy selected services in `core -> BFF -> UI` order. Each rollout, health,
  smoke, and producer/consumer compatibility check must pass before the next.
- Required evidence available at each gate is published before the next
  environment mutation. Evidence-publication failure blocks that mutation and,
  when an earlier mutation occurred, initiates attempt-wide reverse rollback.

## Delivery notifications and acknowledgement

Notification state is part of the controller audit and authoritative evidence;
delivery completion never depends on an email or chat provider being available.

| Event | Initial route | Acknowledge/escalate | Terminal delivery outcome |
|---|---|---|---|
| Protected validation, scan, compatibility, or publish failure before mutation | Application Operations and Delivery Operators | Acknowledge within 4 hours; escalate to Application Operations lead at 8 hours | `failed_pre_mutation`; no environment change |
| Jenkins controller/ACI/AKS/ACR/Key Vault/platform denial before mutation | Platform Operations and Delivery Operators | Acknowledge within 30 minutes; page Platform Operations lead at 60 minutes | `failed_pre_mutation`; no fallback credential |
| Evidence-storage rejection or unavailable evidence gate | Platform Operations, Delivery Operators, and Security Reviewers | Acknowledge within 30 minutes; page Security and Platform leads at 60 minutes | Stop before next mutation or enter rollback |
| Abort, dependency loss, rollout failure, or compatibility failure after mutation | Application and Platform Operations | Immediate page; acknowledge within 15 minutes; incident commander at 30 minutes | `rolling_back` until verified snapshot or `rollback_failed` |
| Rollback/compensation failure or irreversible-migration quarantine | Application and Platform Operations; Security Reviewers when evidence is affected | Immediate critical page; acknowledge within 15 minutes; incident commander and service owner at 30 minutes | `rollback_failed` or `recovery_required`; environment quarantined |
| Successful protected delivery | Delivery Operators and Application Operations | Informational; no acknowledgement deadline | `succeeded` with final evidence reference |

Notification dispatch is retried for 24 hours with deduplication by build/event;
dispatch failure is itself recorded and routed through the operational alert
channel but cannot rewrite the already established delivery result.

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
- `azure-aci-validator` has no system-assigned or user-assigned managed identity.
  It is the only template permitted to run checkout, contract drift, lint,
  typecheck, unit, contract, and non-Azure integration validation on any ref.
  Its stage allowlist excludes Azure login, ACR push, evidence upload,
  migrations, deployment, verification, and rollback; unprotected refs are
  confined to this template and stop after validation.
- Cloud `azure` uses its existing controller-held service principal only for
  ACI lifecycle and approved identity attachment. It must have no ACR push or
  AKS deployment permission, and its tenant, subscription, resource-group
  scope and credential expiry are inspected before provisioning. Its denied
  data-plane permissions are proven by the separate post-bootstrap
  delivery-identity validation.
- Publication runs only on the `azure-aci-publisher` template using its
  ACR-scoped user-assigned managed identity. Promotion, deployment,
  verification, and rollback run only on `azure-aci-deployer` using its
  AKS-scoped user-assigned managed identity. The deployer also has control-plane
  `Reader` on only the target resource group for live bootstrap-manifest and
  platform preflight checks; it cannot read Terraform state, Key Vault secret
  values, ACR content, Redis data, or PostgreSQL data.
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
| `azure` | `azure-aci-validator` | None | All-ref checkout, contract drift, lint, typecheck, and tests without Azure authentication; PR/unprotected refs stop here |
| `azure` | `azure-aci-publisher` | Publisher UAMI | Build, scan, ACR push, digest resolution, publication evidence |
| `azure` | `azure-aci-deployer` | Deployer UAMI | Live manifest/platform read-only checks; promotion; migration-Job orchestration; AKS deployment, verification, rollback, and evidence |

Publisher/deployer templates declare exactly their expected user-assigned
managed identity. Validator declares no identity. System-assigned identity and
additional user-assigned identities are prohibited on every template.
Post-bootstrap validation compares the running container group's identity
resource IDs with the reviewed bootstrap manifest before Azure CLI
authentication.

## External platform bootstrap and identity validation phases

- Infrastructure provisioning and import are Platform Operations prerequisites
  executed outside Jenkins with an interactive Entra identity. The reviewed
  Terraform configuration uses pinned AzureRM and AzureAD providers plus an
  Azure Storage backend with blob-lease locking. No Jenkins identity may run
  `terraform apply`, `terraform import`, or an equivalent infrastructure
  mutation.
- Bootstrap uses time-bounded PIM activation: state-container-only `Storage Blob
  Data Contributor`; application-RG `Contributor` plus `Role Based Access
  Control Administrator`; named shared-resource Network/Private-DNS roles; an
  allowlisted provider-registration/quota-read custom subscription role; JIT
  `Application Administrator`; and a separate JIT `Privileged Role
  Administrator` approver only for Microsoft Graph application consent.
  PostgreSQL bootstrap uses its PIM-controlled bootstrap-admin group. `Owner`,
  `Global Administrator`, standing excess privilege, unrelated resource/app/
  data access, and any grant to Jenkins principals are prohibited and tested.
- `scripts/azure/bootstrap-ui-platform.sh` initializes and applies/imports all
  reviewed Terraform, including evidence-lifecycle and monitoring resources;
  `scripts/azure/bootstrap-data-principals.sh` creates and denial-tests the
  scoped data principals. Platform Operations installs the version-pinned ALB
  Controller and the cluster-admin-owned migration namespace/RBAC/admission
  guardrails. Neither bootstrap script emits the environment manifest.
- Only after those operations succeed does
  `scripts/azure/finalize-ui-platform.sh` verify final state/configuration
  digests, all identities and denials, controller readiness, and migration-
  policy UID/resource version, then emit the
  non-secret `config/platform-bootstrap-nonprod.json` containing the tenant,
  subscription, resource group, Terraform state lineage/serial, resource and
  delivery-identity IDs, public browser origin, private machine origin, and
  configuration digest plus live ALB Controller and migration-policy
  attestations. It records provider-registration and quota/capacity
  attestations that expire after seven days. The schema-validated manifest is
  reviewed with the infrastructure change and contains no credential material.
- The identityless validator checks the reviewed manifest schema and repository
  configuration digest using `platform-configuration-digest-v1`: canonical
  sorted path/mode/length/content records over allowlisted platform inputs, with
  the emitted environment manifest and local/runtime/state/VCS/secret files
  excluded. Matching add/remove/rename/mode/content drift fails. On protected refs, the deployer template's target-RG
  `Reader` grant compares manifest IDs/tags with live resources and exact Jenkins
  ACI template bindings; it never reads Terraform state. A missing, stale, or
  inconsistent manifest blocks delivery, and Jenkins never repairs it.
- `scripts/azure/preflight-ui-platform.sh` is read-only and runs after the
  manifest/identity-binding gate. It verifies target subscription/resource
  group, AKS version/capacity/networking/OIDC, pinned ALB Controller/Gateway
  prerequisites, ACR reachability, data-plane principals, and the absence of
  legacy Web App Routing/NGINX ingress. Provider registration and regional/
  subscription quota are taken only from the unexpired external bootstrap
  attestation; Jenkins receives no subscription-wide reader grant.
- Post-bootstrap validation proves AKS kubelet `AcrPull`, publisher `AcrPush`,
  deployer AKS rights, controller data-plane denial, publisher/deployer
  cross-denial, exact identity binding, and tenant/subscription/resource-group
  scope. Protected publication remains blocked until this phase passes.
- Pull requests and unprotected refs never run the manifest/live-resource or
  delivery-identity checks because they stop on the identityless validator.

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
- Replacement acceptance requires successful identityless-validator, publisher,
  and deployer ACI provisioning plus identity-boundary checks.
- Replacement secret material is accepted only through protected standard input
  or an inherited file descriptor and never appears in command arguments,
  environment variables, repository files, retained temporary files, API
  responses, or logs.
- Emergency revocation disables ordinary build provisioning and cannot fall
  back to another Azure credential. Only an audited, quarantined
  rotation-validation path may provision one smoke agent from each declared
  template; ordinary provisioning remains disabled until the identityless
  validator and both privileged templates pass.

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
- Each reversible journal entry receives at most three compensation attempts
  with delays of 0, 15, and 45 seconds, and the complete automatic rollback has
  a 20-minute deadline measured from rollback entry. Every request, response,
  timeout, verification result, and elapsed time is appended to the journal.
  A timeout or failed verification counts as a failed attempt. After the third
  failure or total deadline, automatic compensation stops at that entry rather
  than skipping a dependency and applying earlier entries out of order.
- If attempt-wide rollback cannot restore the snapshot, set the immutable
  terminal state `rollback_failed`, quarantine promotion, issue the critical
  notification above, and require a two-person approved recovery plan from a
  Delivery Recovery Operator and a distinct Platform Operations approver.
  Recovery continues from the first unverified reverse entry and re-verifies all
  later compensations; it never silently marks the attempt rolled back. Never
  automatically reverse a destructive database migration; migrations must use
  expand-first evolution so image rollback remains compatible with the retained
  schema.

### Core schema sequencing

- A selected core schema change must pass canonical core OpenAPI/schema
  compatibility and required pre-mutation evidence before
  `scripts/ci/migrate-core.sh` creates a bounded Kubernetes migration Job.
- In the dedicated migration namespace, the deployer may `create/get/watch/delete`
  Jobs, `get/list/watch` Pods, and `get` `pods/log`; it cannot exec, attach,
  port-forward, read secrets/configuration, mutate service accounts, or reach
  PostgreSQL. A cluster-admin-owned admission policy outside deployer RBAC
  enforces the exact migrator service account, one nonprivileged container,
  approved core ACR repository by digest, fixed runner/allowed target,
  allowlisted environment/volumes, deadline/retry/TTL, and no host access. The Job uses a dedicated Kubernetes
  service account and migration Workload Identity, mounts no deployer token,
  obtains a short-lived PostgreSQL Entra token, and alone holds the DDL grants
  needed by Alembic. NetworkPolicy permits only that Job to reach PostgreSQL;
  the deployer cannot push the selected digest and the publisher cannot create
  the Job.
- The migration runner accepts only explicit targets: `learning@head`,
  `progress@head`, or `009_merge_learning_progress`; bare `head` is rejected
  while sibling heads exist.
- `007_learning_sessions` and `008_owned_progress` are expand-only sibling heads
  from Foundation revision `006_owned_roadmaps`. Combined delivery applies both
  and merge revision `009_merge_learning_progress` before core rollout.
- The mutation journal records schema heads before/after, contract digest,
  evidence reference, and an operator recovery reference. Schema entries are
  irreversible and have no automatic compensating SQL.
- The Job has an active deadline, retry bound, immutable image digest and
  explicit Alembic target. Success/failure status, pod logs, identity, target,
  before/after heads, and cleanup result are evidence gates. A migration failure
  stops before core image mutation, cleans up the Job, publishes failure
  evidence, quarantines further promotion, and requires operator recovery. A
  later core rollout failure restores the prior compatible core digest while
  retaining the expanded schema and records verification of that combination.

## Required evidence and tests

Immediately after Jenkins accepts the trigger and assigns the build identifier,
a globally trusted, administrator-installed controller plugin built from a
pinned protected revision and verified artifact digest invokes a `RunListener`
independently of repository Jenkinsfile/shared-library code. It creates the
authoritative controller-lifecycle `RunAction` audit record, which
is explicitly non-authoritative as delivery evidence, with build ID, source
revision, start time, `result=pending`, and `failedStage=null`. It runs on the controller
before `node`, agent allocation, checkout, or workspace creation and cannot be
omitted, shadowed, or overridden by repository code. The listener performs monotonic updates,
restart recovery, retention cleanup, and exactly-once finalization with
completion time, terminal result, and failed stage or `none`; agent-provisioning,
evidence, and rollback failures are terminal stages rather than missing records.
After an authenticated agent is available,
`scripts/ci/manage-controller-audit.sh` may serialize/synchronize the trusted
record into evidence but cannot create, replace, suppress, or finalize controller state.

The plugin fsyncs each lifecycle transition to the normal Jenkins run record and
to a host-managed append-only replicated controller-audit volume before it may
request an ACI agent. Protected scheduling is disabled whenever that two-copy
store is unhealthy. Platform Operations owns the volume, hourly integrity check,
and encrypted backup; jobs, agents, Jenkins credentials, and repository code
cannot mutate or delete it. This gives accepted controller-audit transitions an
RPO of zero and a four-hour controller-recovery objective. After controller disk
loss, the plugin restores from the replica, reconciles every build ID against
queue/run metadata, source-control webhook delivery audit, and any Azure
evidence, marks an accepted nonterminal orphan `aborted_recovered`, and blocks
new protected delivery until every post-mutation orphan is rolled back or an
approved recovery plan reaches a verified terminal state.

Once an authenticated delivery agent starts, publish/fingerprint change and
release manifests, JUnit results, digest resolution, scan/SBOM summaries,
before/after deployment snapshots, rollout and smoke logs, and rollback results
in the authoritative Azure Storage container. Failure to publish evidence
required by the next gate blocks the next environment mutation; if an earlier
mutation occurred, it initiates attempt-wide rollback. Controller-local archives
are non-authoritative convenience copies. Exclude credentials and personal data.

An ACR digest that was published but never promoted is recorded as
`published_unpromoted` with build ID, source revision, scan/SBOM references, and
release-manifest digest. It is not an eligible deployment selector for another
build. A later attempt may resolve the same immutable digest only through a new
release manifest after rerunning every current validation, scan, identity,
evidence, and environment gate. Unreferenced unpromoted artifacts are
quarantined from release aliases and become GC-eligible after 30 days, while
their provenance and disposition evidence remains under the 90-day evidence
policy; promoted or held digests are never removed by that cleanup.

Pipeline tests cover UI-only, BFF-only, core-only, shared/all,
mixed-path-union/no-clearing/sorted-unique-reasons, BFF-OpenAPI-only,
core-OpenAPI-only, guidance-catalog-only, implementation-readiness-contract-only,
traceability-only, readiness-manifest-only, performance-profile-only,
provision/teardown-skill executable/template, docs-only, first/missing-baseline,
invalid-supplied-baseline, and audited rebuild-all change plans; validation
failure with zero promotion; tag rejection;
deployment order; injected rollout rollback; stale/concurrent build rejection;
identity/RBAC denial; pending-to-terminal controller-audit transitions;
attempted untrusted controller-audit library override;
attempt-wide reverse rollback; canonical-contract/client drift; identityless
validator all-ref enforcement and unprotected confinement; missing/expired/
stale/inconsistent bootstrap manifests; Jenkins Terraform/state-read denial;
target-RG-only preflight; provider/quota attestation expiry; post-bootstrap
identity validation; bounded migration-Job identity/RBAC/timeout/cleanup;
targeted and merged migration heads; irreversible migration recovery; and
evidence completeness; manual requester/approver separation; notification
routing/acknowledgement/escalation; bounded compensation retry/deadline and
`rollback_failed`; controller disk-loss restore/orphan reconciliation; and
published-but-unpromoted digest quarantine, reuse gating, and cleanup.

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
- Incident hold: Azure's version-level legal-hold boolean on every enumerated
  evidence-set `blob_version_id`, separate from the fixed locked
  90-day `immutable_until`, records owner, reason, incident reference, start,
  and an expiry no later than 180 days from creation. Release/expiry clears the
  version-level hold boolean but cannot shorten the base lock; deletion requires both elapsed
  `immutable_until` and no legal hold.
- Readers: the separately configured Delivery Operators and Security Reviewers
  Microsoft Entra groups only.
- Hold managers: a separately configured Evidence Hold Managers Microsoft Entra
  group alone may request set, expiry-metadata extension, or clear operations;
  a separate minimal reconciler applies/clears each version legal hold;
  every transition/inventory result is audited and never changes the locked 90-day interval,
  and reader membership alone grants no hold-management authority.
- Writers: the stage-appropriate publisher/deployer managed identity has
  path-scoped write access with no general read, list, tag-mutation, or delete
  access; conditional creation plus default version immutability guarantees the
  required no-successful-replacement outcome.
- Prohibited content: credentials, kubeconfigs, tokens, raw identity claims,
  personal learning data, and unredacted logs.
