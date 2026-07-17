# T194 External Platform Verification

Status: **awaiting authorized Platform Operations execution**

This document is the non-secret evidence index for T194. Its presence is not a
claim that Azure was mutated, the environment exists, or any live gate passed.
Only an authorized Platform Operations operator may change the status after the
complete sequence below succeeds. Secret values, tokens, connection strings,
Terraform state, and raw credentials are prohibited here.

## Authorization and prerequisite register

- Platform Operations operator: not recorded
- Distinct approver: not recorded
- Authorization reference and expiry: not recorded
- Target subscription/resource group: not recorded
- Fresh quota/provider/capacity attestation: not recorded
- Reviewed Terraform plan digest: not recorded
- Repository configuration digest: not recorded

## Sole mutation and finalization sequence

Record immutable evidence references for each ordered action. A failed or
missing row blocks all later rows and leaves T194 incomplete.

1. Terraform apply/import and non-secret output inventory: not executed
2. PostgreSQL/Redis/data-principal bootstrap: not executed
3. Pinned ALB Controller installation and AGC/subnet attestation: not executed
4. Migration admission/RBAC/network guardrails installation: not executed
5. Every T176 identity/RBAC positive and negative boundary: not executed
6. Jenkins controller plugin/cloud/templates/credentials/jobs configuration: not executed
7. Sole `PLATFORM_FINALIZATION_AUTHORIZED=T194` manifest finalization: not executed
8. Reviewed `config/platform-bootstrap-nonprod.json` digest/preflight: not executed

## Required live suites

- T180 platform sequence and finalization: not executed
- T182 Jenkins controller/ACI/evidence/protected delivery: not executed
- T193 per-actor live identity boundary harness: not executed
- Externally dependent T156 readiness cases: not executed
- Protected Gateway/UI/BFF and private-core checks: not executed

## Recovery and pilot-availability exercises

- UI/BFF/core attempt-wide recovery: not executed
- PostgreSQL PITR, RPO <=5 minutes and RTO <=4 hours: not executed
- Redis session loss, reauthentication, and RTO <=60 minutes: not executed
- Immutable evidence zero-RPO restore: not executed
- First eligible-minute availability observation: not executed
- Monthly-close dry run and co-approval: not executed

## Completion decision

T194 outcome: **not executed**. T154 remains blocked until this document records
a reviewed successful T194 outcome and the live environment evidence is fresh.
