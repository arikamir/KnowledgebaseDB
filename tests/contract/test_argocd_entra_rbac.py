from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_rbac_policy_maps_distinct_roles_and_readonly_default() -> None:
    policy = yaml.safe_load((ROOT / "config/argocd-rbac-policy.yaml").read_text())
    data = policy["data"]
    assert data["policy.default"] == "role:readonly"
    assert "career-agent-application-release" in data["policy.csv"]
    assert "career-agent-infrastructure-admin" in data["policy.csv"]
    assert "career-agent-observability-readonly" in data["policy.csv"]
    assert "requiredClaims" in data
    policy_text = (ROOT / "config/argocd-rbac-policy.yaml").read_text().lower()
    assert "clientsecret:" not in policy_text
    assert "client_secret:" not in policy_text


def test_entra_contract_keeps_credentials_out_of_desired_state() -> None:
    text = (ROOT / "config/argocd-oidc-rbac.yaml").read_text().lower()
    assert "clientsecret:" not in text
    assert "oidcclientsecretref" in text
    assert "never-persist-token-or-client-secret" in text
