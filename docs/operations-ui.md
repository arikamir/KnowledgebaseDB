# UI platform operations runbook

This runbook covers the non-production UI/BFF/core platform. Platform
Operations owns infrastructure and recovery controls; Application Operations
owns service health and pilot observations. Never place credentials, tokens,
Terraform state, personal learning records, or raw controller logs in delivery
evidence.

## External bootstrap and prerequisites

Only an authorized Platform Operations identity may run the reviewed locked
Terraform plan/import and data-principal bootstrap. GitHub Actions cannot apply
Terraform or read its state. Run `scripts/azure/dry-run-platform-sequence.sh`
first. During authorized T194, install the pinned Gateway API CRDs and ALB
Controller, wait for its readiness attestation, then install the cluster-admin-
owned migration namespace/RBAC/admission guardrails. The sole
`finalize-ui-platform.sh` command emits the reviewed manifest after fresh JIT,
provider/quota/capacity, state, identity-denial, ALB, and migration attestations.
Missing, stale, or digest-drifted manifests block protected delivery.

## Workflow audit and recovery

GitHub retains workflow run metadata while the delivery workflow publishes its
nonsecret source revision, scan/SBOM results, immutable image digests, release
bundle, and desired-state pull request as evidence. A failed or cancelled run
cannot mutate the cluster because application delivery has no kubeconfig or AKS
identity. Resume by starting a new run from a protected source revision; never
reuse a partial release bundle.

## Delivery failure, notification, and recovery

Pre-mutation application failures notify Application and Delivery Operations;
platform failures notify Platform and Delivery Operations; evidence failures
also notify Security Reviewers. Post-mutation or rollback failures page
Application and Platform Operations, require acknowledgement within 15 minutes,
and escalate to an incident commander at 30 minutes. Retry a failed notification
with the same deduplication key for up to 24 hours and retain every attempt.

Promotion is the merge of a reviewed digest-pinned release declaration. Argo CD
reconciles that Git state. Recovery uses `.github/workflows/rollback.yml` to
open a reviewed Git reversion; direct cluster changes are not authoritative.

A digest published but never promoted remains `published_unpromoted`, cannot be
selected by another build, and receives no release alias. Reuse requires a new
manifest and every current validation, scan, identity, environment, and evidence
gate. Unreferenced and unheld items become GC-eligible after 30 days; retain
disposition evidence for 90 days and never delete promoted or held digests.

## Identity and certificate operations

The validator and UI are identityless. The GitHub Actions publisher has only
exact ACR push and its pre-promotion evidence prefixes. Delivery Operations
has a separate exact-path writer limited to post-sync evidence stages; it
cannot write pre-promotion evidence, list/delete blobs, or change retention.
No pipeline deployer identity exists.
The AKS kubelet has exact-registry `AcrPull`
and cannot push, administer, federate, assign roles, or become an application
pod identity. ALB Controller has only exact AGC-resource-group configuration and
association-subnet join. Gateway rotation has only named certificate-version and
DNS-record operations. Validate all bindings and cross-role denials after every
change.

Normal BFF and gateway/private-core certificate rotation provides at least a
24-hour overlap, proves every replica/route/token path, and retires old trust by
48 hours. Partial convergence removes only affected replicas from readiness,
retries for 24 hours, then quarantines/pages and rolls back when verified.
Emergency rotation revokes compromised material immediately, clears affected
session/token caches where required, and permits safe reauthentication only—no
password, access-key, plaintext, alternate issuer, or stale-secret fallback.

## Readiness, migration, lifecycle, and retention

UI, BFF, and core each maintain HPA, PDB, topology spread, liveness, and per-
replica readiness. BFF readiness checks Redis, tenant JWKS, session encryption,
BFF certificate, core TLS, delegated token, and health token. Core checks
PostgreSQL, JWKS, mounted key material, and functional TLS. A failed replica is
removed without restarting healthy replicas.

Expand-only migrations run before core rollout as the fixed digest/runner/target
in `career-migrations` under the migrator identity. Admission, namespace RBAC,
logs, heads, cleanup, and immutable evidence must pass; schema changes are never
automatically reversed. Directory reconciliation runs every four hours and its
revocation dispatcher at least every five minutes. Alert at 2/6/12 hours and
retain the 24-hour end-to-end bound. Retention claims and processes due owner
graphs through audited procedures; complete deletion is due within 90 days and
must leave no linkable identity.

## Pilot availability and recovery evidence

Application Operations owns one observation per eligible minute, missed-run
failure accounting, and calendar-month close. Only maintenance announced 24
hours ahead is excluded, capped at four hours per month; excess/unannounced and
missed observations remain failures. Platform Operations co-approves recovery
evidence. Publish the monthly record through the immutable evidence path. A
missed close blocks the next pilot opening until reconciled.

Recovery drills record actual results: stateless UI/BFF/core RPO 0 and RTO <=60
minutes; PostgreSQL PITR RPO <=5 minutes and RTO <=4 hours; Redis session RTO
<=60 minutes with reauthentication but no core-data loss; immutable evidence RPO
0/RTO <=4 hours; controller audit RPO 0 after two-copy fsync/RTO <=4 hours.
Record incidents, scheduled/excluded/eligible/successful/failed minutes, exercised
RTO/RPO, owner approval, and Platform Operations co-approval without secrets.
