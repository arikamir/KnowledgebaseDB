# Azure Deployment Plan

> **Status:** Approved — single-admin technical PoC preparation; not T194 or a protected release

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

- Resource group `rg-devopscareer-nonprod` exists in `israelcentral`.
- ACR `acrdevopscareernonprod`, Log Analytics, and AKS
  `aks-devopscareer-nonprod` exist.
- AKS is running Kubernetes 1.35 with one `Standard_B2s` node.
- One legacy `devops-career-agent` deployment is healthy and exposed through
  managed Web App Routing over HTTP.
- The required separate UI/BFF/core workloads, Managed Redis, PostgreSQL,
  Key Vault, evidence stores, Application Insights, AGC, and reviewed platform
  bootstrap manifest are absent.
- The existing legacy routing directly conflicts with the target contract and
  remains untouched during the isolated UAE rollout.

The UAE deployment will use a new isolated stack and will not import, move, or
replace the Israel resources:

- prefix: `devopscareeruae`
- environment: `nonprod`
- resource group: `rg-devopscareeruae-nonprod` (confirmed absent)
- AKS: `aks-devopscareeruae-nonprod`
- ACR: `acrdevopscareeruaenonprod` (global name confirmed available)

The legacy Israel deployment remains available until the UAE HTTPS endpoint and
rollback gates pass. Its later retirement is a separate destructive operation.

## 6. Target architecture

| Component | Azure service / configuration |
|---|---|
| UI, BFF, core, lifecycle workers | New UAE AKS, independent digest-pinned workloads |
| Images | New UAE ACR with admin credentials disabled |
| Browser boundary | Application Gateway for Containers, ALB Controller, Gateway API, HTTPS |
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

- [ ] Populate protected bootstrap inputs without committing secrets or real local tfvars
- [ ] Initialize the locked backend and generate the new UAE Terraform state
- [ ] Generate and review a non-destructive Terraform plan
- [ ] Run Terraform formatting/init/validate and Kubernetes rendering checks
- [ ] Set this plan to `Ready for Validation`
- [ ] Invoke `azure-validate` and populate Validation Proof

### Deployment

- [ ] Invoke `azure-deploy` only after validation status is `Validated`
- [ ] Execute the non-release PoC bootstrap without emitting a T194 manifest
- [ ] Build, publish, and deploy digest-pinned core, BFF, then UI from the approved interactive session
- [ ] Verify HTTPS `/health`, public UI/BFF routing, private core, identities, rollback, and evidence
- [ ] Report the authoritative AGC `https://` URL

### Deferred formal release

- [ ] Establish scoped PIM eligibility and a distinct Graph-consent approver
- [ ] Run the authorized T194 bootstrap/data-principal/controller/finalization sequence
- [ ] Configure and verify Jenkins publisher/deployer protected-delivery templates
- [ ] Execute the protected Jenkins delivery and retain immutable T194 evidence

## 10. Validation Proof

Not yet eligible. Preparation must first encode and validate the isolated UAE
inputs and prove that the PoC path cannot emit T194 evidence or enable Jenkins
protected delivery.

## 11. Next required decision

Collect the remaining environment-specific inputs (public DNS/certificate
issuer, protected backend coordinates, and non-secret group/object references),
then run local Terraform/Kustomize validation and produce the exact no-delete
UAE plan for final mutation approval.
