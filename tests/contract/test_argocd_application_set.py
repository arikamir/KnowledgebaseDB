from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_application_set_reads_main_release_and_sequences_migration_before_services():
    application_set = load("deploy/argocd/applicationset.yaml")
    assert application_set["apiVersion"] == "argoproj.io/v1alpha1"
    assert application_set["kind"] == "ApplicationSet"
    assert application_set["metadata"]["namespace"] == "argocd"
    assert application_set["spec"]["goTemplate"] is True
    assert application_set["spec"]["goTemplateOptions"] == ["missingkey=error"]

    generator = application_set["spec"]["generators"][0]["git"]
    assert generator["repoURL"] == "https://github.com/arikamir/KnowledgebaseDB.git"
    assert generator["revision"] == "main"
    assert generator["files"] == [{"path": "deploy/argocd/environments/nonprod/release.json"}]

    template = application_set["spec"]["template"]
    assert template["spec"]["project"] == "career-agent"
    sources = template["spec"]["sources"]
    assert [source["path"] for source in sources] == [
        "deploy/k8s/overlays/argocd-nonprod",
        "deploy/k8s/overlays/argocd-nonprod-migration",
    ]
    assert all(source["targetRevision"] == "main" for source in sources)
    assert template["spec"]["destination"] == {
        "server": "https://kubernetes.default.svc",
        "namespace": "career-agent",
    }
    assert template["spec"]["syncPolicy"]["automated"] == {
        "allowEmpty": False,
        "prune": True,
        "selfHeal": True,
    }
    assert template["spec"]["syncPolicy"]["syncOptions"] == [
        "CreateNamespace=false",
        "FailOnSharedResource=true",
        "PruneLast=true",
        "PrunePropagationPolicy=foreground",
        "ServerSideApply=true",
    ]

    images = sources[0]["kustomize"]["images"]
    assert len(images) == 3
    assert {image.split("=", 1)[0] for image in images} == {
        "career-agent/ui",
        "career-agent/bff",
        "career-agent/core",
    }
    assert all(".services." in image for image in images)
    assert sources[1]["kustomize"]["images"] == [
        "career-agent/core={{.services.core.image}}",
    ]
    assert not any("infra/" in str(value) or "terraform" in str(value).lower() for value in template.values())


def test_application_project_is_restricted_to_services_and_migration_job():
    project = load("deploy/argocd/project.yaml")
    assert project["kind"] == "AppProject"
    assert project["spec"]["sourceRepos"] == ["https://github.com/arikamir/KnowledgebaseDB.git"]
    assert project["spec"]["destinations"] == [
        {"server": "https://kubernetes.default.svc", "namespace": "career-agent"},
        {"server": "https://kubernetes.default.svc", "namespace": "career-migrations"},
    ]
    assert project["spec"]["clusterResourceWhitelist"] == []
    assert {entry["kind"] for entry in project["spec"]["namespaceResourceWhitelist"]} == {
        "Deployment", "Service", "HorizontalPodAutoscaler", "PodDisruptionBudget", "Job",
    }


def test_release_declaration_is_semver_and_digest_pinned():
    path = ROOT / "deploy/argocd/environments/nonprod/release.json"
    release = json.loads(path.read_text())
    assert release["schemaVersion"] == 1
    assert release["environment"] == "nonprod"
    assert release["sourceRevision"] == "23a86189e8e13b9f4c82d7da6486b8a805d039ad"
    assert set(release["services"]) == {"ui", "bff", "core"}
    for service in release["services"].values():
        assert "@sha256:" in service["image"]
        assert len(service["image"].rsplit("@sha256:", 1)[1]) == 64


def test_argocd_overlay_is_application_only_and_excludes_platform_resources():
    overlay = load("deploy/k8s/overlays/argocd-nonprod/kustomization.yaml")
    assert overlay["namespace"] == "career-agent"
    assert set(overlay["resources"]) == {"../../base/ui", "../../base/bff", "../../base/core"}
    assert not any("gateway" in resource or "namespace.yaml" in resource for resource in overlay["resources"])
    assert {entry["path"] for entry in overlay["patches"]} >= {"application-images.yaml", "platform-resource-deletions.yaml"}
    deletion_text = (ROOT / "deploy/k8s/overlays/argocd-nonprod/platform-resource-deletions.yaml").read_text()
    for name in ("ui", "bff", "core", "ui-runtime-config", "bff-runtime-config", "core-runtime-config", "bff-key-vault-material", "core-key-vault-material"):
        assert f"name: {name}" in deletion_text

    patch_text = (ROOT / "deploy/k8s/overlays/argocd-nonprod/application-images.yaml").read_text()
    assert patch_text.count("name: career-agent-acr-pull") == 3
    assert "kind: Secret" not in patch_text
    assert "namespace.yaml" not in patch_text
    assert "gateway" not in patch_text.lower()


def test_core_migration_is_a_presync_hook_using_the_release_core_digest() -> None:
    overlay = load("deploy/k8s/overlays/argocd-nonprod-migration/kustomization.yaml")
    assert overlay["resources"] == ["core-migration-presync.yaml"]
    job = load("deploy/k8s/overlays/argocd-nonprod-migration/core-migration-presync.yaml")
    assert job["metadata"]["namespace"] == "career-migrations"
    assert job["metadata"]["annotations"] == {
        "argocd.argoproj.io/hook": "PreSync",
        "argocd.argoproj.io/hook-delete-policy": "BeforeHookCreation,HookSucceeded",
        "argocd.argoproj.io/sync-wave": "-10",
    }
    container = job["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "career-agent/core"
    assert container["command"] == ["/app/scripts/run-migration.sh"]
    assert container["env"] == [
        {"name": "MIGRATION_TARGET", "value": "009_merge_learning_progress"},
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
