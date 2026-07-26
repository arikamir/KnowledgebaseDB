# Contract: Release and Reconciliation Evidence

The release hand-off must link the following identifiers without copying secret
material:

```text
GitHub Actions run
  -> SemVer releaseVersion
  -> sourceRevision
  -> UI/BFF/Core image digests
  -> reviewed desired-state revision on main
  -> generated Argo Application
  -> sync/health result and timestamp
```

## Required evidence fields

- schema version `2` (the version that introduces the vendor-neutral
  `automatedReview` record)
- CI run ID and repository/branch
- event type (`release`, `sync`, or `rollback`) and actor type (`automation` or `human`)
- source revision and release version
- three image repository/digest references
- validation and scan results, including failed checks when applicable
- desired-state Git revision and Application name
- Argo sync status, health status, reason, and timestamps
- affected service, recommended next action, and diagnosis/next-action visibility timestamps
- automation identity or Entra tenant/subject/role for human actions
- rollback source/target revisions, reason, actor, approval result, and outcome when the event type is `rollback`
- protected source tag, normalized release version, and approved automated-review result
- readiness result and elapsed-time fields for merge-to-sync, failure
  diagnosis, and drift detection

The evidence record MUST include an `automationIdentity` when `actorType` is
`automation`, or a `humanAction` identity record when `actorType` is `human`.
It MUST include an `automatedReview` result with the approved reviewer identity,
required status-check name, and observation time, plus a readiness result and
validation evidence. The collector MUST consume the successful gate's receipt,
including its current head, pull request, reviewer, and proof type, and MUST NOT
accept caller-supplied reviewer or pass-status values. It MUST compare the
receipt's pull request and head with the independently retained release or
rollback scope, then authenticate the live PR head, successful status, and
approved review or no-findings reaction through GitHub. A
rollback event MUST include its source/target revisions, actor, approval
result, reason, and outcome. A failed rollout MUST include
`affectedService`, `reason`, and `nextAction`; `diagnosedAt` and
`nextActionVisibleAt` are required when measuring the two-minute diagnosis
criterion. Evidence collectors MUST reject credential-shaped values before
upload.

Evidence is uploaded to the existing protected delivery evidence store or GitHub
Actions artifacts according to retention policy. Logs must redact tokens,
client secrets, kubeconfigs, connection strings, and raw learner data. A failed
release leaves the last known-good declaration and application running.
