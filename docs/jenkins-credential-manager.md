# Jenkins Azure cloud credential manager

Cloud `azure` uses the stable system credential ID `jenkins-azure-cloud` only
for ACI lifecycle and approved managed-identity attachment. Platform Operations
owns the credential and the root-owned, non-secret expiry/scope reports under
`$JENKINS_HOME/credential-health`.

## Manager boundary

`jenkins-credential-manager` is an authenticated principal with basic
`Overall/Read` only. No global `Credentials/Update`, job configuration, build,
agent, Script Console, or unrelated-credential permission is granted. An
administrator installs `configure-credential-manager.groovy`, which exposes a
localhost-only `credential-manager/update` action restricted to that principal
and the exact `jenkins-azure-cloud` ID. The action is POST-only, uses the normal
Jenkins CSRF crumb filter, preserves subscription/client/scope metadata, and
returns only the accepted version identifier.

Replacement material is read by the rotation client from protected standard input
or an inherited file descriptor and sent only in the authenticated HTTPS
request body over the loopback interface. It never appears in arguments,
environment variables, repository files, responses, logs, retained temporary
files, or health evidence.

## Daily health gate

Install `install-cloud-credential-health-job.groovy` after placing the policy,
metadata, and exact role-assignment report in their controller-owned paths. The
nonconcurrent controller-local job runs daily and never binds the credential.
It checks the exact ACI resource-group and two identity-attachment scopes,
expiry, stable ID, and absence of ACR, AKS, storage, secret, or broad roles.

Alerts occur at 30, 14, and 7 days and are deduplicated per credential version
and threshold. The 30-day alert requires acknowledgement within 24 hours; the
14- and 7-day alerts escalate to the Platform Operations incident route. When
fewer than 30 valid days remain, scope/metadata is invalid, or the 30-day alert
is not acknowledged, protected promotion is quarantined. There is no fallback
credential, controller agent, or local agent.

A new healthy version may clear the old version's quarantine only after the
identityless validator, publisher, and deployer smoke checks required by the
rotation procedure pass. The health job itself does not revoke credentials or
run those delivery-capable templates.
