from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/k8s/base/migration"
RUNNER = ROOT / "scripts/ci/migrate-core.sh"
IMAGE_RUNNER = ROOT / "scripts/runtime/run-core-migration.sh"


def document(name: str) -> dict[str, object]:
    return yaml.safe_load((MIGRATION / name).read_text())


def documents(name: str) -> list[dict[str, object]]:
    return list(yaml.safe_load_all((MIGRATION / name).read_text()))


def test_namespace_and_migrator_identity_are_dedicated() -> None:
    namespace = document("namespace.yaml")
    account = document("service-account.yaml")
    assert namespace["metadata"] == {
        "name": "career-migrations",
        "labels": {"knowledgebase.io/migration-guardrails": "enforced"},
    }
    assert account["metadata"]["name"] == "core-migrator"
    assert account["metadata"]["namespace"] == "career-migrations"
    assert account["metadata"]["annotations"] == {
        "azure.workload.identity/client-id": "${MIGRATION_CLIENT_ID}",
        "knowledgebase.io/postgresql-role": "core_migrator_ddl_backfill",
    }
    assert account["automountServiceAccountToken"] is False


def test_gitops_rbac_has_only_the_exact_job_observation_surface() -> None:
    role, binding = documents("gitops-rbac.yaml")
    assert role["metadata"]["namespace"] == "career-migrations"
    assert role["rules"] == [
        {
            "apiGroups": ["batch"],
            "resources": ["jobs"],
            "verbs": ["create", "get", "list", "watch", "update", "patch", "delete"],
        },
        {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list", "watch"]},
        {"apiGroups": [""], "resources": ["pods/log"], "verbs": ["get"]},
    ]
    assert binding["roleRef"] == {
        "apiGroup": "rbac.authorization.k8s.io",
        "kind": "Role",
        "name": role["metadata"]["name"],
    }
    assert binding["subjects"] == [{
        "kind": "ServiceAccount",
        "name": "argocd-application-controller",
        "namespace": "argocd",
    }]
    serialized = json.dumps(role["rules"])
    for denied in ("pods/exec", "pods/attach", "pods/portforward", "secrets", "configmaps", "serviceaccounts"):
        assert denied not in serialized


def test_only_migrator_jobs_can_reach_postgresql_dns_and_entra_token_exchange() -> None:
    policy = document("network-policy.yaml")
    assert policy["metadata"]["namespace"] == "career-migrations"
    assert policy["spec"]["podSelector"]["matchLabels"] == {"app.kubernetes.io/name": "core-migration"}
    assert policy["spec"]["policyTypes"] == ["Ingress", "Egress"]
    assert policy["spec"]["ingress"] == []
    egress = policy["spec"]["egress"]
    assert egress[0]["ports"] == [{"port": 53, "protocol": "UDP"}, {"port": 53, "protocol": "TCP"}]
    assert egress[1]["ports"] == [{"port": 5432, "protocol": "TCP"}]
    assert egress[1]["to"] == [{"ipBlock": {"cidr": "${POSTGRES_PRIVATE_ENDPOINT_IP}/32"}}]
    assert egress[2]["ports"] == [{"port": 443, "protocol": "TCP"}]
    assert egress[2]["to"] == [{"ipBlock": {"cidr": "${ENTRA_TOKEN_ENDPOINT_CIDR}"}}]


def test_job_template_is_bounded_nonprivileged_and_expand_only() -> None:
    job = document("job-template.yaml")
    spec = job["spec"]
    pod_spec = spec["template"]["spec"]
    container = pod_spec["containers"][0]
    assert job["metadata"]["namespace"] == "career-migrations"
    assert spec["activeDeadlineSeconds"] == 900
    assert spec["backoffLimit"] == 1
    assert spec["ttlSecondsAfterFinished"] == 300
    assert pod_spec["serviceAccountName"] == "core-migrator"
    assert pod_spec["restartPolicy"] == "Never"
    assert pod_spec["hostNetwork"] is False
    assert pod_spec["hostPID"] is False
    assert pod_spec["hostIPC"] is False
    assert pod_spec["securityContext"] == {"runAsNonRoot": True, "seccompProfile": {"type": "RuntimeDefault"}}
    assert container["name"] == "core-migration"
    assert container["image"] == "${CORE_MIGRATION_IMAGE}"
    assert container["command"] == ["/app/scripts/run-migration.sh"]
    assert container["args"] == ["upgrade", "$(MIGRATION_TARGET)"]
    assert container["env"] == [
        {"name": "MIGRATION_TARGET", "value": "${MIGRATION_TARGET}"},
        {
            "name": "DATABASE_URL",
            "valueFrom": {
                "configMapKeyRef": {
                    "name": "core-migration-policy-v1",
                    "key": "databaseUrl",
                },
            },
        },
    ]
    assert container["securityContext"] == {
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
        "privileged": False,
        "readOnlyRootFilesystem": True,
        "runAsNonRoot": True,
    }
    assert pod_spec["volumes"] == []


def test_admission_policy_makes_runner_image_target_and_sandbox_non_overridable() -> None:
    parameters = document("policy-parameters.yaml")
    policy, binding = documents("validating-admission-policy.yaml")
    assert parameters["immutable"] is True
    assert parameters["data"]["coreRepository"] == "${CORE_IMAGE_REPOSITORY}"
    assert policy["spec"]["failurePolicy"] == "Fail"
    assert policy["spec"]["paramKind"] == {"apiVersion": "v1", "kind": "ConfigMap"}
    assert binding["spec"]["paramRef"]["name"] == "core-migration-policy-v1"
    expressions = "\n".join(item["expression"] for item in policy["spec"]["validations"])
    for required in (
        "core-migrator", "core-migration", "@sha256:", "[0-9a-f]{64}",
        "/app/scripts/run-migration.sh", "learning@head", "progress@head",
        "009_merge_learning_progress", "activeDeadlineSeconds == 900",
        "backoffLimit == 1", "ttlSecondsAfterFinished == 300", "envFrom",
        "hostNetwork", "hostPID", "hostIPC", "hostPath", "privileged",
        "allowPrivilegeEscalation", "readOnlyRootFilesystem", "MIGRATION_TARGET",
        "DATABASE_URL",
        "core-migration-policy-v1", "configMapKeyRef",
    ):
        assert required in expressions


def test_admission_policy_limits_argocd_to_job_mutations_in_migration_namespace() -> None:
    policy, binding = documents("argocd-boundary-policy.yaml")
    assert policy["spec"]["failurePolicy"] == "Fail"
    assert policy["spec"]["matchConstraints"]["resourceRules"] == [{
        "apiGroups": ["*"],
        "apiVersions": ["*"],
        "operations": ["CREATE", "UPDATE", "DELETE"],
        "resources": ["*"],
        "scope": "Namespaced",
    }]
    expression = policy["spec"]["validations"][0]["expression"]
    assert "system:serviceaccount:argocd:argocd-application-controller" in expression
    assert "request.operation == 'DELETE'" in expression
    assert "oldObject.kind == 'Job'" in expression
    assert "object.kind == 'Job'" in expression
    assert binding["spec"]["validationActions"] == ["Deny"]
    assert binding["spec"]["matchResources"]["namespaceSelector"]["matchLabels"] == {
        "knowledgebase.io/migration-guardrails": "enforced",
    }


def test_kustomization_installs_guardrails_but_not_a_migration_job() -> None:
    kustomization = document("kustomization.yaml")
    assert set(kustomization["resources"]) == {
        "namespace.yaml", "service-account.yaml", "gitops-rbac.yaml",
        "network-policy.yaml", "policy-parameters.yaml",
        "validating-admission-policy.yaml", "argocd-boundary-policy.yaml",
    }
    assert "job-template.yaml" not in kustomization["resources"]


def test_runner_uses_only_the_deployer_rbac_surface_and_never_rolls_out_core() -> None:
    source = RUNNER.read_text()
    for required in (
        "kubectl create", "kubectl get job", "kubectl get pods", "kubectl logs",
        "kubectl delete job", "MIGRATION_CLASSIFICATION", "expand-only",
        "CORE_IMAGE_REPOSITORY", "MIGRATION_TARGET", "MIGRATION_BEFORE_HEADS",
        "MIGRATION_AFTER_HEADS", '"reversible":false', '"compensation":null',
    ):
        assert required in source
    for forbidden in (
        "kubectl apply", "kubectl patch", "kubectl exec", "kubectl attach",
        "kubectl port-forward", "kubectl get secret", "kubectl get serviceaccount",
        "docker push", "az acr", "psql ", "alembic ", "kubectl set image",
        "kubectl rollout",
    ):
        assert forbidden not in source


def test_core_image_contains_the_fixed_expand_only_migration_runner() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    source = IMAGE_RUNNER.read_text()
    assert "COPY alembic.ini ./" in dockerfile
    assert "COPY alembic ./alembic" in dockerfile
    assert "COPY scripts/runtime/run-core-migration.sh ./scripts/run-migration.sh" in dockerfile
    assert "chmod 0555 /app/scripts/run-migration.sh" in dockerfile
    assert "learning@head) revision=007_learning_sessions" in source
    assert "progress@head) revision=008_owned_progress" in source
    assert "009_merge_learning_progress) revision=009_merge_learning_progress" in source
    assert "alembic current" in source
    assert 'alembic upgrade "$revision"' in source
    assert "alembic downgrade" not in source


def test_alembic_uses_the_migration_workload_identity_for_postgresql() -> None:
    source = (ROOT / "alembic/env.py").read_text()
    dependencies = (ROOT / "pyproject.toml").read_text()
    assert '"azure-identity' in dependencies
    assert "AZURE_FEDERATED_TOKEN_FILE" in source
    assert "WorkloadIdentityCredential" in source
    assert "https://ossrdbms-aad.database.windows.net/.default" in source
    assert "create_postgres_entra_engine" in source


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CORE_MIGRATION_IMAGE", "acrdevopscareernonprod.azurecr.io/devops-career-agent:latest"),
        ("CORE_MIGRATION_IMAGE", "other.azurecr.io/devops-career-agent@sha256:" + "a" * 64),
        ("CORE_MIGRATION_IMAGE", "acrXdevopscareernonprod.azurecr.io/devops-career-agent@sha256:" + "a" * 64),
        ("MIGRATION_TARGET", "downgrade:-1"),
        ("MIGRATION_CLASSIFICATION", "contract"),
    ],
)
def test_runner_rejects_mutable_cross_repository_or_non_expand_input(
    tmp_path: Path, name: str, value: str,
) -> None:
    env = os.environ | {
        "CORE_IMAGE_REPOSITORY": "acrdevopscareernonprod.azurecr.io/devops-career-agent",
        "CORE_MIGRATION_IMAGE": "acrdevopscareernonprod.azurecr.io/devops-career-agent@sha256:" + "a" * 64,
        "MIGRATION_TARGET": "009_merge_learning_progress",
        "MIGRATION_CLASSIFICATION": "expand-only",
        "MIGRATION_DATABASE_URL": "postgresql+psycopg://migration%40example@postgresql.data-services.svc/career",
        "MIGRATION_EVIDENCE_DIR": str(tmp_path),
        "MUTATION_JOURNAL": str(tmp_path / "journal.jsonl"),
    }
    env[name] = value
    result = subprocess.run([str(RUNNER)], cwd=ROOT, env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert not (tmp_path / "migration-evidence.json").exists()


def test_runner_records_successful_irreversible_migration_and_cleanup(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    kubectl = bin_dir / "kubectl"
    kubectl.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "printf '%s\\n' \"$*\" >> \"$KUBECTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *'get job '*'jsonpath='*) printf 'Complete' ;;\n"
        "  *'get pods '*) printf 'core-migration-pod' ;;\n"
        "  *'logs '*) printf 'MIGRATION_BEFORE_HEADS=007_learning_sessions,008_owned_progress\\nMIGRATION_AFTER_HEADS=009_merge_learning_progress\\n' ;;\n"
        "esac\n"
    )
    kubectl.chmod(0o755)
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "KUBECTL_LOG": str(tmp_path / "kubectl.log"),
        "CORE_IMAGE_REPOSITORY": "acrdevopscareernonprod.azurecr.io/devops-career-agent",
        "CORE_MIGRATION_IMAGE": "acrdevopscareernonprod.azurecr.io/devops-career-agent@sha256:" + "b" * 64,
        "MIGRATION_TARGET": "009_merge_learning_progress",
        "MIGRATION_CLASSIFICATION": "expand-only",
        "MIGRATION_DATABASE_URL": "postgresql+psycopg://migration%40example@postgresql.data-services.svc/career",
        "MIGRATION_EVIDENCE_DIR": str(tmp_path),
        "MUTATION_JOURNAL": str(tmp_path / "journal.jsonl"),
        "BUILD_ID": "test-42",
    }
    result = subprocess.run([str(RUNNER)], cwd=ROOT, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    evidence = json.loads((tmp_path / "migration-evidence.json").read_text())
    assert evidence["status"] == "succeeded"
    assert evidence["target"] == "009_merge_learning_progress"
    assert evidence["databaseRole"] == "core_migrator_ddl_backfill"
    assert evidence["beforeHeads"] == ["007_learning_sessions", "008_owned_progress"]
    assert evidence["afterHeads"] == ["009_merge_learning_progress"]
    assert evidence["cleanup"] == "deleted"
    journal = json.loads((tmp_path / "journal.jsonl").read_text())
    assert journal["reversible"] is False
    assert journal["compensation"] is None
    commands = (tmp_path / "kubectl.log").read_text()
    assert "create -f" in commands
    assert "delete job" in commands


def test_runner_records_failed_job_cleanup_and_stops_before_journaling(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    kubectl = bin_dir / "kubectl"
    kubectl.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "printf '%s\\n' \"$*\" >> \"$KUBECTL_LOG\"\n"
        "case \"$*\" in\n"
        "  *'get job '*'jsonpath='*) printf 'Failed' ;;\n"
        "esac\n"
    )
    kubectl.chmod(0o755)
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "KUBECTL_LOG": str(tmp_path / "kubectl.log"),
        "CORE_IMAGE_REPOSITORY": "acrdevopscareernonprod.azurecr.io/devops-career-agent",
        "CORE_MIGRATION_IMAGE": "acrdevopscareernonprod.azurecr.io/devops-career-agent@sha256:" + "c" * 64,
        "MIGRATION_TARGET": "learning@head",
        "MIGRATION_CLASSIFICATION": "expand-only",
        "MIGRATION_DATABASE_URL": "postgresql+psycopg://migration%40example@postgresql.data-services.svc/career",
        "MIGRATION_EVIDENCE_DIR": str(tmp_path),
        "MUTATION_JOURNAL": str(tmp_path / "journal.jsonl"),
        "BUILD_ID": "test-failed",
    }
    result = subprocess.run([str(RUNNER)], cwd=ROOT, env=env, text=True, capture_output=True)
    assert result.returncode != 0
    evidence = json.loads((tmp_path / "migration-evidence.json").read_text())
    assert evidence["status"] == "failed"
    assert evidence["safeReason"] == "migration Job failed"
    assert evidence["cleanup"] == "deleted"
    assert not (tmp_path / "journal.jsonl").exists()
    commands = (tmp_path / "kubectl.log").read_text()
    assert "delete job" in commands
