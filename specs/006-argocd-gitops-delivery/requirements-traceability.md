# Requirements Traceability: Argo CD GitOps Application Delivery

This matrix links every functional requirement and buildable success criterion
to planned tasks and its verification point. Task completion remains tracked in
`tasks.md`; this document is the review map for the implementation gate.

| Requirement | Task IDs | Verification evidence |
| --- | --- | --- |
| FR-001 | T013, T015, T019 | Workflow boundary tests |
| FR-002 | T013, T016, T017, T019 | Permission and workflow boundary tests |
| FR-003 | T013, T015, T019 | Infrastructure workflow boundary tests |
| FR-004 | T003, T005, T006, T023-T025, T046 | Bundle schema, writer, and validation tests |
| FR-004a | T005, T007, T020, T023-T024 | SemVer schema and tag tests |
| FR-004b | T003, T006-T007, T020, T024 | Protected-tag/source-match tests |
| FR-005 | T010, T021, T024-T025 | Git desired-state and PR-flow tests |
| FR-006 | T010, T024, T028 | ApplicationSet and reconciliation tests |
| FR-006a | T017, T021, T024 | Copilot and protected-main tests |
| FR-006b | T010-T011, T024, T028 | ApplicationSet discovery tests |
| FR-006c | T008-T011 | Kustomize and resource-boundary tests |
| FR-007 | T005-T006, T008, T011, T020, T025 | Digest validation and render tests |
| FR-007a | T004, T008, T011, T026, T043 | Pull-secret ownership and readiness tests |
| FR-008 | T006, T012, T020, T024, T026-T027 | Invalid-release and readiness tests |
| FR-009 | T005-T006, T020, T023, T025 | Single-release identity tests |
| FR-010 | T029, T032-T033, T036 | Evidence schema and diagnosis tests |
| FR-011 | T028, T035 | Drift and self-heal tests |
| FR-012 | T030-T031, T034, T036 | Reviewed rollback tests |
| FR-013 | T030, T034, T036 | Rollback audit evidence tests |
| FR-014 | T013, T017, T037-T039, T041 | Permission matrix and RBAC tests |
| FR-014a | T037, T040-T041 | Entra OIDC authentication tests |
| FR-014b | T037, T039-T041 | Group/app-role mapping tests |
| FR-014c | T037, T041-T042 | Expiry/revocation tests |
| FR-014d | T017, T037, T041 | Identity separation tests |
| FR-014e | T005-T006, T029, T032, T041-T042, T048 | Credential-redaction tests |
| FR-015 | T014, T018, T029, T032-T033, T042, T047 | End-to-end evidence links |
| FR-015a | T029, T032-T033, T042 | Human-action audit tests |
| FR-016 | T005-T006, T010, T024, T027 | Nonprod-only validation tests |
| FR-017 | T028, T031, T035 | Last-known-good and failure-retention tests |
| FR-018 | T026-T027, T046-T047 | Readiness and compatibility tests |
| SC-001 | T014, T018, T029, T032-T033, T042, T047 | Trace evidence record |
| SC-002 | T013, T015-T019, T046-T047 | Workflow mutation audit |
| SC-003 | T028, T033, T047 | Merge-to-sync timing evidence |
| SC-004 | T006, T020, T024, T026-T028, T031 | Rejection and last-known-good evidence |
| SC-005 | T029, T031-T033, T036, T047 | Diagnosis and next-action timestamps |
| SC-006 | T030-T031, T034, T047 | Rollback recovery evidence |
| SC-007 | T013, T019, T037-T038, T042, T047 | Allow/deny audit records |
| SC-008 | T028, T031, T035, T047 | Drift detection and recovery evidence |
| SC-009 | T007, T020, T024-T025, T047 | Reproducibility and version ledger |
| SC-010 | T037-T038, T041-T042, T047 | Entra permission evidence |
| SC-011 | T037, T042, T047 | Tenant/subject audit evidence |
| SC-012 | T011, T022, T028, T046-T047 | Three-digest and resource-scope evidence |

## Cross-cutting task coverage

| Task | Scope | Verification |
| --- | --- | --- |
| T001 | Workflow ownership boundary documentation | Documentation review |
| T002 | GitHub/Azure prerequisite documentation | Prerequisite checklist |
| T044 | Implemented quickstart synchronization | Quickstart validation |
| T045 | Requirements traceability maintenance | Matrix completeness check |
