from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2] / "deploy/k8s/base"
EXPECTED = {
    "ui": ({"cpu": "50m", "memory": "64Mi"}, {"cpu": "250m", "memory": "128Mi"}),
    "bff": ({"cpu": "100m", "memory": "256Mi"}, {"cpu": "500m", "memory": "512Mi"}),
    "core": ({"cpu": "250m", "memory": "512Mi"}, {"cpu": "1000m", "memory": "1Gi"}),
}


def load(service: str, name: str):
    return yaml.safe_load((ROOT / service / name).read_text())


def test_each_service_has_exact_independent_resources_readiness_and_topology_spread():
    for service, (requests, limits) in EXPECTED.items():
        deployment = load(service, "deployment.yaml")
        assert deployment["metadata"]["name"] == service
        assert deployment["spec"]["replicas"] == 2
        containers = deployment["spec"]["template"]["spec"]["containers"]
        app = next(container for container in containers if container["name"] == service)
        assert app["resources"] == {"requests": requests, "limits": limits}
        assert app["readinessProbe"] and app["livenessProbe"]
        assert all(container.get("resources", {}).get("requests") and container.get("resources", {}).get("limits") for container in containers)
        spread = deployment["spec"]["template"]["spec"]["topologySpreadConstraints"]
        assert spread == [{
            "maxSkew": 1,
            "topologyKey": "kubernetes.io/hostname",
            "whenUnsatisfiable": "ScheduleAnyway",
            "labelSelector": {"matchLabels": {"app.kubernetes.io/name": service}},
        }]


def test_each_hpa_scales_only_its_service_from_two_to_four_at_70_percent_cpu():
    targets = {}
    for service in EXPECTED:
        hpa = load(service, "hpa.yaml")
        assert hpa["apiVersion"] == "autoscaling/v2"
        assert hpa["spec"]["minReplicas"] == 2 and hpa["spec"]["maxReplicas"] == 4
        assert hpa["spec"]["metrics"] == [{
            "type": "Resource",
            "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": 70}},
        }]
        targets[service] = hpa["spec"]["scaleTargetRef"]["name"]
    assert targets == {service: service for service in EXPECTED}


def test_each_pdb_removes_at_most_one_matching_replica_and_is_rendered():
    for service in EXPECTED:
        pdb = load(service, "pdb.yaml")
        assert pdb["spec"] == {
            "maxUnavailable": 1,
            "selector": {"matchLabels": {"app.kubernetes.io/name": service}},
        }
        kustomization = load(service, "kustomization.yaml")
        assert "hpa.yaml" in kustomization["resources"] and "pdb.yaml" in kustomization["resources"]
