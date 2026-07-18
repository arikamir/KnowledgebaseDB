# GitHub Actions Azure delivery

GitHub Actions is the CI/CD orchestrator. Jenkins files and controller plugins
remain only as legacy migration material; no deployment job depends on a
Jenkins controller or ACI callback.

## Workflows

- `.github/workflows/ci.yml` runs the full identityless validation suite on pull
  requests, pushes, and manual dispatch.
- `.github/workflows/delivery.yml` runs validation, digest-pinned image build /
  scan / publication, protected non-production promotion, migration, rollout,
  verification, and bounded two-person recovery.
- `.github/workflows/reusable-validate.yml` is shared by delivery and regular
  CI so a protected ref cannot skip the all-ref validation gate.

Protected delivery uses GitHub OIDC and short-lived Azure tokens. Configure
these repository/environment values before enabling the workflows:

- secrets: `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
  `AZURE_PUBLISHER_CLIENT_ID`, and `AZURE_DEPLOYER_CLIENT_ID`;
- variables: `ACR_LOGIN_SERVER`, `AKS_RESOURCE_GROUP`, `AKS_CLUSTER_NAME`,
  `EVIDENCE_STORAGE_ACCOUNT`, and the three service smoke URLs;
- environments: `nonprod-publisher`, `nonprod`, and `nonprod-recovery`, with
  required reviewers configured on `nonprod` and `nonprod-recovery`.

Terraform creates the publisher and deployer federated credentials bound to the
repository and protected environment subjects. It deliberately does not grant
pull requests an Azure token or give the publisher deployment permissions.
The existing publisher/deployer RBAC scopes are retained; only the orchestration
trust relationship changes from Jenkins to GitHub Actions.

The first Azure apply after creating the GitHub repository must include
`github_repository = "owner/name"`. Do not place a client secret, kubeconfig,
registry password, or Azure access token in GitHub secrets.
