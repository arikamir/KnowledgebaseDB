# Azure Deployment Plan

> **Status:** Deployed — single-admin technical PoC; not T194 or a protected release

Generated: 2026-07-17

## 1. Project overview

**Goal:** First deploy the feature-003 DevOps Career Agent as an explicitly
non-release technical PoC in an isolated UAE North environment. Preserve the
formal T194 path for a later protected UI/BFF/core release after independent
approval becomes available.

**Path:** Modify an existing, partially provisioned Azure application.

## 2. Requirements

| Attribute | Proposed value |
|---|---|
| Classification | Technical proof of concept; not a measured pilot or protected release |
| Scale | Small, initially 10–20 internal users |
| Budget | Balanced non-production baseline |
| Subscription | `Pay-As-You-Go` (approved by the user on 2026-07-17) |
| Location | `uaenorth` (selected by the user on 2026-07-17) |
| Compliance | Entra-only workload authentication, private data planes, immutable delivery evidence, Israel business-hour monitoring, no secrets or learner data in delivery evidence |

Azure Policy discovery found only the subscription Security Center built-in
assignment; no additional location, SKU, naming, or networking policy was found.

## 3. Components detected

| Component | Type | Technology | Path |
|---|---|---|---|
| UI | SPA frontend | React, Vite, Node.js 24 | `ui/` |
| BFF | API/session boundary | Fastify, TypeScript, Node.js 24 | `bff/` |
| Core | API and lifecycle workers | FastAPI, Python 3.11, Alembic | `src/`, `api/`, `alembic/` |
| Delivery | Protected CI/CD | Jenkins and versioned shell/Groovy scripts | `Jenkinsfile`, `scripts/` |
| Platform | Azure infrastructure | Terraform and Kustomize | `infra/azure/`, `deploy/k8s/` |

All three application components already have Dockerfiles. Terraform, Kubernetes
manifests, rollout scripts, rollback controls, and live-test harnesses exist.

## 4. Recipe selection

**Selected:** Pure Terraform plus the repository's project-specific Azure
bootstrap/finalization scripts and Jenkins protected-delivery workflow.

**Rationale:** The normative delivery contract requires external Platform
Operations to use the locked Azure Storage Terraform backend, prohibits Jenkins
from applying/importing or reading state, requires a separately reviewed
bootstrap manifest, and mandates exact identity/evidence controls. Adding an
`azd up` wrapper would bypass that established control plane.

## 5. Current Azure state

- The legacy application resource group `rg-devopscareer-nonprod` and AKS
  managed resource group in `israelcentral` were destroyed on 2026-07-18 after
  the UAE deployment passed HTTPS verification.
- The retired Israel stack's AKS cluster, ACR and images, Log Analytics data,
  Container Insights solution, and exact ACR-pull assignment were deleted.
- The recovered historical Terraform teardown state is empty. The original
  ignored local state is retained unchanged as stale audit evidence and must
  not be used for future plans.
- `NetworkWatcher_israelcentral` remains in Azure's shared `NetworkWatcherRG`;
  it is unrelated subscription infrastructure and was intentionally excluded
  from the application destroy plan.
- The UAE North deployment is now the only DevOps Career Agent application
  stack in the subscription.

The UAE deployment will use a new isolated stack and will not import, move, or
replace the Israel resources:

- prefix: `devopscareeruae`
- environment: `nonprod`
- resource group: `rg-devopscareeruae-nonprod` (confirmed absent)
- AKS: `aks-devopscareeruae-nonprod`
- ACR: `acrdevopscareeruaenonprod` (global name confirmed available)

The legacy Israel deployment has been retired. Recreating an Israel application
stack requires a new reviewed plan and state; it must not reuse the retained
historical local state.

## 6. Target architecture

| Component | Azure service / configuration |
|---|---|
| UI, BFF, core, lifecycle workers | New UAE AKS, independent digest-pinned workloads |
| Images | New UAE ACR with admin credentials disabled |
| Browser boundary | Application Gateway for Containers, ALB Controller, Gateway API, cert-manager/Let's Encrypt HTTPS on `career-agent.<AGC-IP>.sslip.io` |
| Core machine boundary | Private DNS and internal load balancer only |
| Sessions | Azure Managed Redis `Balanced_B0`, private endpoint, access keys disabled |
| Durable learning data | PostgreSQL Flexible Server 16 `GP_Standard_D2s_v3`, 32 GiB, Entra-only, private delegated subnet |
| Key material | Key Vault with CSI and versioned certificates/keys |
| Evidence | Two Storage accounts with immutable/version-hold controls |
| Identity | Nine one-to-one workload identities, two Jenkins delivery identities, identityless UI/validator |
| Monitoring | Log Analytics, Application Insights, action groups, alerts, eligible-minute synthetic workflow |

### Regional compatibility

Live provider metadata on 2026-07-17 advertises UAE North for both
`Microsoft.ServiceNetworking/trafficControllers` (Application Gateway for
Containers) and Azure Managed Redis. PostgreSQL Flexible Server 16
`Standard_D2s_v3` General Purpose is advertised in zones 1, 2, and 3. The
`Microsoft.ServiceNetworking` provider is not yet registered; registering it is
an explicit Platform Operations bootstrap action and does not require Jenkins.

## 7. Provisioning-limit evidence collected

These figures apply to the selected `uaenorth` context and must be refreshed if
execution begins more than seven days after capture. No capacity cell is
unknown; services whose providers do not expose quota API data are explicitly
marked as such.

| Resource / quota | Planned effect | Total after deployment | Limit / availability | Result |
|---|---:|---:|---:|---|
| Standard B-family vCPU | Add one 2-vCPU node | 2 | 10 | Pass |
| Regional total vCPU | Add 2 | 2 | 10 | Pass |
| AKS cluster | Add 1 | 1 | 10 default for Pay-As-You-Go | Pass |
| Virtual networks | Add 1 | 1 | 1,000 | Pass |
| Public IP addresses | No explicit Terraform public IP; AGC manages its frontend | At most 1 | 20 | Pass |
| Network security groups | Add 2 | 2 | 5,000 | Pass |
| Private endpoints | Add 2 | 2 | 65,536 | Pass |
| Storage accounts | Add 2 | 2 | 250 | Pass |
| PostgreSQL Flexible Server | Add 1 `GP_Standard_D2s_v3` | 1 | Quota API unsupported; requested SKU/version/zones 1–3 advertised | Capacity advertised |
| Azure Managed Redis | Add 1 `Balanced_B0` | 1 | Quota API unsupported; provider advertises UAE North | Region available |
| Key Vault | Add 1 | 1 | No vault-count restriction identified; transaction limits far exceed pilot scale | Pass |
| Application Gateway for Containers | Add 1 | 1 | Provider advertises UAE North; registration pending | Pass after registration |

Required resource providers for AKS, ACR, Network, Storage, Key Vault, Managed
Redis, PostgreSQL, and monitoring are registered. `Microsoft.ServiceNetworking`
registration is the remaining provider bootstrap action.

## 7a. Preparation research and local verification

- The application is a multi-service Node.js/Python workload hosted on AKS;
  `.NET Aspire` is not present, so the repository's pure-Terraform workflow
  remains the correct recipe.
- AKS supporting resources follow the existing managed-identity, private data
  plane, Log Analytics, and Application Insights architecture. Application
  telemetry is configured through the Application Insights connection string;
  no instrumentation key or application secret is required.
- Azure discovery found no public DNS zone and no Storage account in the
  subscription. The UAE Terraform backend therefore needs a separately created
  Azure Storage account/container before main-state initialization.
- Azure discovery found no existing `DevOps Career` Entra groups. The PoC may
  create the required role groups with the approved administrator as their sole
  initial owner/member, but this is exception evidence and not formal
  separation-of-duties evidence.
- Application Gateway for Containers consumes its frontend certificate from a
  Kubernetes TLS Secret. Azure's documented automated path is cert-manager with
  Let's Encrypt; direct Key Vault CSI mounting is not supported for an AGC
  listener. The approved PoC uses the free IP-encoded `sslip.io` DNS service and
  ACME contact `arikamir1+poc@gmail.com`; the hostname is finalized after AGC
  exposes its frontend IP. The formal paid/custom-issuer path is unchanged.
- An ignored local `infra/azure/terraform.tfstate` tracks the Israel stack. It
  must not be imported, migrated, modified, or used for UAE. A clean-state plan
  excluding that file contains 136 creates, zero updates, zero deletes, and
  zero replacements, targeting only `rg-devopscareeruae-nonprod` plus the
  declared tenant objects. The UAE apply requires a new remote backend/key.
- The isolated remote backend is now available at resource group
  `rg-devopscareeruae-tfstate`, account `stdevcareeruaetfstate`, container
  `tfstate`, key `feature-003/uaenorth-nonprod.tfstate`. It uses Entra data
  access, shared keys disabled, TLS 1.2+, versioning, and seven-day blob/container
  soft delete. It contains no imported Israel state.
- Azure requires a new account-level WORM policy to start `Unlocked`; formal
  Platform Operations locks it in a reviewed second apply. The technical PoC
  remains explicitly `Unlocked` and cannot publish protected-release evidence.
- `terraform fmt -check -recursive infra/azure` passed on 2026-07-18.
- `terraform -chdir=infra/azure init -backend=false -input=false` and
  `terraform -chdir=infra/azure validate` passed with AzureRM `4.81.0` and
  AzureAD `3.9.0`.
- Both `kubectl kustomize deploy/k8s/overlays/aks-nonprod` and the isolated
  `deploy/k8s/overlays/aks-poc` rendered successfully. Sixty focused Terraform,
  AGC, Kubernetes, evidence-retention, and PoC contract tests passed. Functional
  verification remains pending until provisioning and rollout.

## 8. Security, authorization, and destructive-change gates

- The current signed-in identity has subscription-level `Owner`. The project
  contract explicitly prohibits `Owner`, Global Administrator, standing excess
  privilege, and Jenkins infrastructure mutation for T194.
- Execution requires an authorized Platform Operations identity with the exact
  time-bounded PIM roles in the bootstrap contract, plus a distinct JIT
  Privileged Role Administrator approver for Graph consent.
- Required Entra group object IDs, certificate issuers, reviewed public DNS
  zone/source ranges, Terraform backend coordinates, and authorization/expiry
  evidence must be supplied through the protected bootstrap process, never
  committed as real values.
- The UAE stack is new, so no Israel resource may be imported into its state.
  Any unexpected replacement/deletion, legacy-route mutation, RBAC scope beyond
  the reviewed matrix, public exposure beyond AGC HTTPS, or irreversible
  database action requires explicit review of the exact Terraform plan and
  separate approval before execution.

### Approved technical-PoC exception

Because no second tenant administrator is currently available, the user approved
a single-administrator exception for this isolated PoC. It does **not** amend or
satisfy FR-071, T194, `PROTECTED_DELIVERY_READY`, `PILOT_READY`, or any formal
release evidence. The exception has these hard boundaries:

- scope is only `rg-devopscareeruae-nonprod` and its newly created dependencies;
- the existing Israel resource group and workload are untouched;
- no real employee, pilot, production, or personal learning data is permitted;
- no T194 final manifest may be emitted and T194 remains unchecked;
- Jenkins publisher/deployer protected stages remain disabled because their
  manifest and separation gates are intentionally unsatisfied;
- Jenkins may run the identityless validation/build checks, but PoC provisioning,
  image publication, and rollout occur from the explicitly approved interactive
  administrator session outside Jenkins;
- secrets, tokens, kubeconfigs, Terraform state, and real variable files remain
  outside Git and Jenkins;
- the exact Terraform plan must contain no deletion or replacement before apply;
- this exception expires when a distinct consent approver becomes available or
  before any protected release/pilot, whichever occurs first.

The formal release path is unchanged: rerun the scoped PIM/two-person bootstrap,
emit the reviewed T194 manifest, configure Jenkins publisher/deployer agents,
and execute the protected pipeline before claiming release readiness.

### Human bootstrap versus Jenkins delivery

| Phase | Identity | Execution location | Responsibility |
|---|---|---|---|
| Tenant/bootstrap authorization | Human Platform Operations operator with time-bounded PIM activation | Interactive session outside Jenkins | Register provider; create state backend prerequisites; run reviewed Terraform plan/apply; create Entra apps, identities, RBAC, data principals, ALB/migration controls; finalize manifest |
| Graph admin consent | A different human/JIT identity with `Privileged Role Administrator` | Entra approval flow outside Jenkins | Approve only the required Microsoft Graph application consent; cannot be the bootstrap actor |
| Workload identities | Terraform-created managed identities | Azure/AKS | BFF, core, workers, ALB, rotation; no human login |
| Jenkins validation | Identityless `azure-aci-validator` | Jenkins ACI agent | Contract, lint, typecheck, unit, and non-Azure integration gates |
| Jenkins publication | Terraform-created publisher UAMI | Jenkins `azure-aci-publisher` | Build/scan/push digest-pinned images and publish immutable evidence |
| Jenkins delivery | Terraform-created deployer UAMI | Jenkins `azure-aci-deployer` | Migration job, core → BFF → UI rollout, verification, evidence, and bounded rollback |

The repository scripts automate validation of the formal human authorization
record and infrastructure work, but they cannot create their own PIM eligibility
or self-approve Graph consent. For the approved PoC exception those formal
scripts cannot be used to emit T194 evidence; a separate, clearly labelled
non-release execution record is required. Once independent approval exists, the
reviewed bootstrap manifest and Jenkins templates restore the normal protected
pipeline without human Azure credentials in its agents.

## 9. Execution checklist

### Planning

- [x] Analyze workspace and live Azure state
- [x] Scan components and existing infrastructure
- [x] Select the repository-authorized Terraform recipe
- [x] Check target-region provider registration, policies, quotas, and capacity
- [x] Choose a supported region/gateway architecture (`uaenorth` + AGC)
- [x] Confirm reuse of the current `Pay-As-You-Go` subscription by approving this plan
- [x] Record the single-admin technical-PoC exception without weakening T194
- [x] Complete selected-region quota/capacity checks
- [x] Present the deployment plan and receive PoC approval

### Preparation and validation

- [x] Supply a free `sslip.io` hostname strategy and ACME contact email
- [x] Add the isolated PoC cert-manager/Let's Encrypt listener path without changing the formal Key Vault issuer path
- [x] Populate ignored UAE PoC inputs without committing secrets or real local tfvars
- [x] Initialize the isolated Entra-only backend for the new UAE Terraform state
- [x] Generate and review a clean-state non-destructive Terraform plan (136 create, 0 update/delete/replace)
- [x] Run Terraform formatting/init/validate and Kubernetes rendering checks
- [x] Set this plan to `Ready for Validation`
- [x] Invoke `azure-validate` and populate Validation Proof

### Deployment

- [x] Invoke `azure-deploy` only after validation status is `Validated`
- [x] Execute the non-release PoC bootstrap without emitting a T194 manifest
- [x] Build, publish, and deploy digest-pinned core, BFF, then UI from the approved interactive session
- [x] Verify trusted HTTPS, public UI/BFF routing, private Core readiness, workload identities, and Key Vault CSI mounts
- [ ] Execute formal rollback and immutable delivery-evidence gates (deferred to the protected Jenkins release)
- [x] Report the authoritative AGC `https://` URL

### Deferred formal release

- [ ] Establish scoped PIM eligibility and a distinct Graph-consent approver
- [ ] Run the authorized T194 bootstrap/data-principal/controller/finalization sequence
- [ ] Configure and verify Jenkins publisher/deployer protected-delivery templates
- [ ] Execute the protected Jenkins delivery and retain immutable T194 evidence

## 10. Validation Proof

### All validation checks pass

- [x] Terraform installation: `terraform version` → `1.15.5` (`darwin_arm64`)
- [x] Azure CLI installation: `az version` → `2.88.0`
- [x] Authentication: `Pay-As-You-Go`
  (`a6e1647d-3f1f-4ba6-b8a3-a2ad74ec5d7a`) is enabled in tenant
  `06d91dc0-b055-4647-82ab-191086577280`
- [x] Initialize: clean temporary workspace successfully configured the new
  `azurerm` backend; the ignored Israel state was excluded
- [x] Format: `terraform fmt -check -recursive infra/azure`
- [x] Syntax: `terraform -chdir=infra/azure validate`
- [x] Plan preview: remote-state plan contains 136 creates, 0 updates,
  0 deletes, and 0 replacements
- [x] State backend: Entra-authenticated backend initialization and locked plan
  completed against the new empty UAE key
- [x] Azure Policy: only the Security Center built-in assignment is active;
  no location, naming, SKU, or networking conflict was found
- [x] Template resolution: no unresolved `{{ .Env.* }}` values exist
- [x] Build verification: BFF TypeScript build, UI TypeScript/Vite production
  build, both Kustomize overlays, and Python contract collection passed
- [x] Focused validation: 112 AGC, Terraform, Entra, RBAC, Key Vault, evidence,
  Jenkins-identity, and technical-PoC contract tests passed

### Role Assignment Verification

- **Status:** Verified statically
- **Identities checked:** AKS kubelet; BFF; core; lifecycle; retention;
  lab-revalidation; migration; evidence-hold reconciler; ALB Controller;
  gateway certificate/DNS; Jenkins publisher and deployer; four PoC groups
- **Roles confirmed:** exact-ACR `AcrPull`/`AcrPush`; Redis Data Contributor;
  named Key Vault crypto/secret/certificate roles; exact evidence-container
  custom roles and readers; AGC Configuration Manager plus delegated-subnet
  Network Contributor; exact-AKS RBAC Writer; target-resource-group Reader
- **Scope result:** data roles are resource/container/key/certificate scoped.
  Resource-group scope is limited to custom-role definition boundaries, AGC
  configuration, and the deployer's declared read-only inventory requirement.
- **PoC exception:** the four governance groups have the same human owner/member
  and are not separation-of-duties or T194 evidence.

Validation completed on 2026-07-18. The PoC path remains unable to emit T194
evidence or enable Jenkins protected delivery.

### Jenkins protected-template readiness

- The local Jenkins controller is healthy on `http://localhost:8080` and runs
  Azure Container Agents plugin `372.v073266fff4a_7`.
- Its `azure` cloud now targets `rg-devopscareeruae-nonprod` and has one pinned,
  identityless `azure-aci-validator` template. Publisher/deployer replacement
  stopped before mutation because the installed plugin has no per-template ACI
  managed-identity API.
- The UAE publisher has exact ACR `AcrPush` plus delivery-evidence writer, and
  the UAE deployer has target-resource-group `Reader`, exact-AKS RBAC Writer,
  plus delivery-evidence writer. The `jenkins-azure-agents` provisioning
  principal now has the custom UAE `Jenkins ACI Provisioner` role and Managed
  Identity Operator only on those two delivery identities.
- Template configuration now takes the ACI resource group from the reviewed
  bootstrap manifest and rejects cross-subscription/resource-group delivery
  identities and target resources. The focused static suite passes 58 tests.
- The approved PoC-only `poc-reviewed` manifest is digest-valid and records
  `formalT194: false`; it configures no protected pipeline bypass. The formal
  T194 manifest remains deliberately absent.
- Live publisher/deployer configuration is blocked by upstream
  `azure-container-agents` `372.v073266fff4a_7`: its template builder exposes no
  system-assigned or user-assigned identity field. The official immutable
  inbound-agent digest was resolved, but no delivery template was created
  because an identityless delivery agent would violate the contract.

## 11. Deployment result

Deployment completed on 2026-07-18 in `uaenorth`:

- URL: `https://career-agent.4.150.171.72.sslip.io/`
- resource group: `rg-devopscareeruae-nonprod`
- AKS: `aks-devopscareeruae-nonprod`
- ACR: `acrdevopscareeruaenonprod.azurecr.io`
- public edge: Application Gateway for Containers with Gateway API
- public certificate: Let's Encrypt production certificate, contact
  `arikamir1+poc@gmail.com`, Ready in cert-manager
- UI digest: `sha256:ab4b83fc714e9145e6b87e270c9b52602f0f0ed48680c9e02cac6b9b9d718c4d`
- BFF digest: `sha256:6963df190b4c68dc511f73f0a3cca7b510ec9fce7fb3cd2fa2d49391468f6b38`
- Core digest: `sha256:88bbe6dcb19c526f37b081e92650c53d4d265759c54c5407906e5fb1b54da316`

External smoke tests returned `200` for `/`, `/runtime-config.json`, and
`/bff/v1/capabilities` with normal TLS verification enabled. UI, BFF, and Core
each report one Ready replica; the public certificate and both Gateway
listeners are Ready/Programmed.

### Technical-PoC runtime limits

- The single `Standard_B2s` node uses one replica per service and `Recreate`
  rollout semantics; this is not highly available.
- Core currently uses an ephemeral SQLite database and the BFF's implemented
  Redis/session integrations are not registered in the current application
  factory. Azure PostgreSQL and Managed Redis are provisioned privately but are
  not the active PoC runtime stores.
- Lifecycle, retention, certificate-rotation, and lab-revalidation CronJobs are
  suspended for the PoC.
- Key Vault retains deny-by-default networking with temporary public access
  restricted to the approved operator `/32`; workloads use the private
  endpoint and workload identity.
- Port 80 remains available only to support ACME HTTP-01 renewal; application
  traffic is served over trusted HTTPS.
- Provisioning and this first rollout used the explicitly approved interactive
  administrator exception. Jenkins protected publication/deployment remains
  disabled until the formal T194 identity and independent-consent gates exist.

### Israel Central teardown verification

- Confirmation: `DESTROY-nonprod-rg-devopscareer-nonprod`
- Subscription: `Pay-As-You-Go`
  (`a6e1647d-3f1f-4ba6-b8a3-a2ad74ec5d7a`)
- Result: five original managed objects plus the recovered AKS-created
  Container Insights child destroyed; recovered state contains zero resources
- Resource-group checks: `rg-devopscareer-nonprod` and
  `MC_rg-devopscareer-nonprod_aks-devopscareer-nonprod_israelcentral` both absent
- Preserved: `rg-devopscareeruae-nonprod` in `uaenorth` and the unrelated shared
  `NetworkWatcherRG`
- Post-teardown smoke test: UAE site returned HTTPS `200` with successful TLS
  verification

## 12. Next required decision

Before calling this a pilot or protected release, wire Core to Entra-authenticated
PostgreSQL, register the BFF Redis/session and delegated-token integrations,
restore production replica/rollout settings and scheduled workers, replace the
single-admin exception with independent approval, and execute the protected
Jenkins pipeline with rollback and immutable evidence gates. The formal Key
Vault issuer/T194 path remains unchanged.
