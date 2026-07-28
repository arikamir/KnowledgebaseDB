# Research: Argo CD GitOps Application Delivery

## Decision 1: Generate one application from a Git file declaration

**Decision**: Use the Argo CD ApplicationSet Git generator's `files` mode with
`goTemplate: true` and `goTemplateOptions: [missingkey=error]`. Pin the first
generator to the protected `main` branch and the exact path
`deploy/argocd/environments/nonprod/release.json`.

**Rationale**: The file generator maps structured JSON fields into the generated
Application, so the three service images and release metadata are selected from
one reviewed declaration. Failing on missing template keys prevents a partial
or silently defaulted release. A fixed path makes the first environment explicit
and prevents an unreviewed environment from being discovered accidentally.

**Alternatives considered**:

- A directory generator was rejected because it would discover arbitrary files
  and would need extra conventions to distinguish release declarations from
  documentation or platform manifests.
- A list generator was rejected because release data would be duplicated in the
  ApplicationSet manifest rather than reviewed beside the source revision and
  image digests.
- A separate desired-state repository was rejected by FR-006a; the canonical
  source is the protected `main` branch of this repository.

**Evidence**: Argo CD ApplicationSet Git generator and specification references:
<https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/Generators-Git/>
and <https://argo-cd.readthedocs.io/en/stable/operator-manual/applicationset/applicationset-specification/>.

## Decision 2: Restrict the generated application to services and one migration hook

**Decision**: Create a dedicated `AppProject` with a service source containing
the UI, BFF, and Core bases and a separate source containing one bounded Core
`PreSync` migration Job. The generated `Application` targets the existing
`career-agent` and `career-migrations` namespaces; `CreateNamespace=false`;
cluster-scoped resources and unrelated platform paths are excluded.

**Rationale**: Namespace, gateways, private load balancers, platform controllers,
identities, migration admission/runtime configuration, and Terraform resources
are infrastructure-owned. An allowlist plus restricted service and
migration-hook source paths makes the boundary enforceable both in the
repository and at the Argo CD API. Argo CD hooks provide a fail-closed sequence:
the expand-only migration from the exact release Core digest completes before
service Deployments are reconciled. Since AppProject resource allowlists apply
to every destination, a platform-owned admission policy additionally denies
all non-Job mutations by the Argo CD application controller in
`career-migrations`.

**Alternatives considered**:

- Pointing Argo CD at `deploy/k8s/overlays/aks-nonprod` was rejected because that
  overlay also owns platform and ingress resources.
- Allowing all namespace resources was rejected because it weakens the release
  boundary and can allow a future manifest to introduce an unrelated workload.
- Giving the ApplicationSet cluster-wide permissions was rejected because it
  violates FR-002 and makes an application release an infrastructure operation.

**Evidence**: The repository's existing Terraform and AKS overlay ownership
split, plus the Kubernetes Kustomize `images` transformer documentation:
<https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/>.

## Decision 3: Bind one SemVer release to three immutable image digests

**Decision**: Store a JSON release declaration with `schemaVersion`, environment,
SemVer 2.0.0 `releaseVersion`, 40-character `sourceRevision`, and exactly `ui`,
`bff`, and `core` service image fields. CI derives the version from a protected
`v*` tag (normalizing the optional `v` prefix and accepting prerelease/build
metadata), verifies that the tag points to the build revision, and writes the
matching value. Each image must be an ACR `repository@sha256:<64-hex>` reference.
CI validates a release-bundle schema before writing the declaration, verifies
the effective tag-protection gate, rejects versions already associated with a
different source revision for the repository lifetime, and rejects
credential-like fields.

**Rationale**: A single declaration prevents cross-release service mixes and
ensures that Argo CD reconciles the exact artifacts CI validated. Digests remain
the deployment identity even when SemVer is used for human-facing history.

**Alternatives considered**:

- Mutable tags such as `latest` or `0.1.0` were rejected because registry tag
  movement would make rollback and audit records non-reproducible.
- One declaration per service was rejected because it permits partial promotion
  and makes the release identity ambiguous.
- Runtime schema validation only was rejected because invalid desired state must
  be rejected before Argo CD starts a rollout.

## Decision 4: Keep CI publication and platform provisioning independent

**Decision**: The application workflow builds/scans/publishes images and opens or
updates a bot-branch pull request containing the reviewed GitOps declaration.
An approved automated identity is a required review gate before protected
`main` can change; CI verifies that the review targets the current
pull-request head, publishes the required `ai/review` status, and fails closed
when it is missing, stale, or from an unapproved identity. Terraform remains
the only infrastructure provisioner. Argo CD performs
application reconciliation after the declaration lands on protected `main`; the
application workflow does not obtain AKS credentials, run Terraform, publish
application images from the infrastructure workflow, or apply platform
manifests.

**Rationale**: This is the primary safety property in FR-001 through FR-003.
Application rollback then becomes a Git change/reconciliation operation rather
than a platform mutation.

**Alternatives considered**:

- Keeping the current direct `promote.sh` AKS deployment as a fallback was
  rejected as the default path because it preserves a second application
  controller and violates the definite separation requested by the user.
- Letting Argo CD run Terraform was rejected because Terraform state and cloud
  privileges are outside the application controller's responsibility.

## Decision 5a: Keep registry pull credentials out of desired state

**Decision**: Platform bootstrap provisions and rotates the namespace-scoped
`imagePullSecret` named `career-agent-acr-pull`. The application overlay may
reference that name but cannot create the Secret or contain its data; readiness
checks report when it is absent or invalid.

**Rationale**: This preserves the infrastructure/application boundary and avoids
putting registry credentials in Git, ApplicationSet parameters, or CI artifacts.

**Alternatives considered**:

- Granting the release Application Secret creation was rejected because it would
  expand the application controller's authority and expose credential material.
- Relying on an implicit node identity was rejected for this PoC contract because
  the requested out-of-band secret name and rotation ownership must be explicit.

## Decision 5: Use Entra OIDC for humans and workload identities for automation

**Decision**: Configure Argo CD human access through Microsoft Entra OIDC, map
groups or app roles to application-release, infrastructure-admin, and read-only
roles, and keep Argo CD repository/controller and GitHub OIDC identities separate
from human accounts. Store client secrets only in cluster secret management or
workload identity configuration, never in Git or release evidence.

**Rationale**: Central SSO makes privileged actions attributable and supports
session expiry/revocation checks. Separation of human and automation identities
prevents a release manifest or CI log from becoming a credential transport.

**Alternatives considered**:

- Local Argo CD users were rejected because they bypass tenant policy and make
  role review and offboarding harder.
- A long-lived GitHub PAT or client secret in workflow files was rejected by
  FR-014d and FR-014e; GitHub OIDC and Argo CD repository credentials are scoped
  and managed outside desired state.

**Evidence**: Argo CD's Microsoft Entra OIDC guidance:
<https://argo-cd.readthedocs.io/en/stable/operator-manual/user-management/microsoft/>
and RBAC guidance:
<https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/>.

## Decision 5b: Make readiness and timing measurable

**Decision**: The readiness command emits a versioned JSON result containing
`status` (`ready` or `blocked`), environment, named prerequisite checks,
`observedAt`, and an actionable `failureReason` when blocked. Release evidence
also records the affected service, recommended next action, diagnosis, and
next-action visibility timestamps. Environment tests record protected merge,
sync, failure-discovery, and drift timestamps and assert
SC-003's 10-minute, SC-005's two-minute, and SC-008's five-minute limits.

**Rationale**: A stable readiness contract lets CI fail safely without cloud
mutation, while elapsed-time evidence turns the success criteria into verifiable
checks instead of documentation-only targets.

**Alternatives considered**:

- Free-form shell output was rejected because callers could not reliably
  distinguish a platform block from a transient command failure.
- Manual stopwatch notes were rejected because they are not reproducible audit
  evidence.

## Decision 6: Verify with identityless render/contract gates before live sync

**Decision**: Required pre-sync checks are JSON/schema validation, shell syntax,
Kustomize rendering, AppProject/ApplicationSet contract tests, and an explicit
review of generated resources. Live verification then checks Argo CD sync/health,
three Deployment digests, drift correction, and Git rollback evidence.

**Rationale**: Most boundary failures can be detected without Azure credentials
or a running cluster. The remaining checks prove the controller and platform
integration without granting CI infrastructure-admin permissions.

**Alternatives considered**:

- Full end-to-end Azure deployment on every pull request was rejected because it
  is slow, costly, and would blur the infrastructure/application boundary.
- Render-only validation was rejected because it cannot prove registry access,
  health probes, drift, or rollback behavior.
