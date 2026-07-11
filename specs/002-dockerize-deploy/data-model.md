# Data Model: Dockerize and Deploy to AKS

## ApplicationPackage

- **Purpose**: Represents the portable release artifact created from the
  application source.
- **Fields**:
  - `image_name`
  - `image_tag`
  - `source_revision`
  - `build_context`
  - `entrypoint`
  - `exposed_port`
  - `health_endpoint`
  - `created_at`
- **Validation rules**:
  - `image_tag` must be immutable for a release candidate.
  - `source_revision` must identify the source state used to create the
    package.
  - `health_endpoint` must match the endpoint used by deployment probes.

## DeploymentTarget

- **Purpose**: Describes the environment that receives an application release.
- **Fields**:
  - `name`
  - `environment`
  - `namespace`
  - `registry_reference`
  - `configuration_source`
  - `secret_source`
  - `is_production`
- **Validation rules**:
  - The initial target must be non-production.
  - Cluster credentials and secret values must not be stored in source control.
  - `namespace` must be explicit in deployment documentation and commands.

## DeploymentConfiguration

- **Purpose**: Captures environment-specific runtime values for a target.
- **Fields**:
  - `app_name`
  - `environment`
  - `database_url_reference`
  - `log_level`
  - `performance_targets`
  - `topic_catalog_path`
- **Validation rules**:
  - Configuration must be replaceable without rebuilding the image.
  - Sensitive values must be referenced through the deployment environment
    rather than stored as plain text.

## Release

- **Purpose**: Links an application package to a deployment target and rollout
  state.
- **Fields**:
  - `release_id`
  - `application_package`
  - `deployment_target`
  - `requested_by`
  - `status`
  - `started_at`
  - `completed_at`
  - `verification_result`
- **State transitions**:
  - `prepared` -> `deployed` -> `verified`
  - `prepared` -> `failed`
  - `deployed` -> `failed`
  - `failed` -> `rolled_back`
- **Validation rules**:
  - A release is complete only after deployment health checks pass.
  - A failed release must preserve enough context to identify the rollback
    point.

## RollbackPoint

- **Purpose**: Identifies the last known good release that can be restored.
- **Fields**:
  - `release_id`
  - `image_reference`
  - `deployment_revision`
  - `verified_at`
  - `restore_command`
- **Validation rules**:
  - The rollback point must reference an already-built package.
  - Rollback must not require modifying application source or rebuilding the
    package.

## Relationships Summary

- One `ApplicationPackage` can be promoted to one or more `DeploymentTarget`
  environments.
- One `DeploymentTarget` can have many `Release` records over time.
- A `Release` produces or updates one `RollbackPoint` after successful
  verification.
- `DeploymentConfiguration` belongs to a `DeploymentTarget` and is applied at
  runtime instead of build time.
