from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


PHASES = {
    "redis_entra_token_expiry_1",
    "redis_entra_token_expiry_2",
    "postgres_entra_token_expiry_1",
    "postgres_entra_token_expiry_2",
    "tenant_jwks_refresh",
    "tenant_jwks_unknown_kid",
    "tenant_jwks_stale_24h",
    "key_vault_csi_active_version_refresh",
    "key_vault_csi_partial_replica_mount_failure",
    "transient_dependency_reconnect",
}


def load_evidence() -> dict[str, object]:
    path = os.environ.get("DEPLOYED_ENTRA_ROLLOVER_EVIDENCE")
    if not path:
        pytest.skip("T194 must establish the live environment before deployed rollover execution")
    value = json.loads(Path(path).read_text())
    assert isinstance(value, dict)
    return value


def test_successive_live_rollovers_cover_every_replica_pool_and_preserve_state() -> None:
    evidence = load_evidence()
    assert evidence["schemaVersion"] == 1
    assert evidence["authorizedGate"] == "post-T194"
    assert evidence["environment"] == "nonprod"
    replicas = evidence["replicas"]
    assert isinstance(replicas, dict)
    assert set(replicas) == {"bff", "core"}
    assert all(isinstance(values, list) and len(values) >= 2 and len(values) == len(set(values)) for values in replicas.values())
    pools = evidence["connectionPools"]
    assert isinstance(pools, dict) and set(pools) == {"redis", "postgresql"}
    assert all(isinstance(values, list) and values and len(values) == len(set(values)) for values in pools.values())
    baseline = evidence["baseline"]
    assert baseline["savedDataDigest"].startswith("sha256:")
    assert baseline["sessionCookieDigest"].startswith("sha256:")
    rows = evidence["observations"]
    assert isinstance(rows, list) and rows
    identities = {(row["phase"], row["service"], row["replicaId"], row["poolId"]) for row in rows}
    expected = {
        (phase, service, replica, pool)
        for phase in PHASES
        for service, service_replicas in replicas.items()
        for replica in service_replicas
        for pool_type, pool_ids in pools.items()
        for pool in pool_ids
        if (service == "bff" and pool_type == "redis") or (service == "core" and pool_type == "postgresql")
    }
    assert identities == expected
    for row in rows:
        assert set(row) == {
            "phase", "service", "replicaId", "poolId", "startedAt", "recoveredAt",
            "workloadUidBefore", "workloadUidAfter", "readyRemovedDuringFault", "readyAfterRecovery",
            "tokenOrKeyVersionBefore", "tokenOrKeyVersionAfter", "sessionCookieDigest",
            "savedDataDigest", "fallbackCredentialObserved", "rawEvidenceRef",
        }
        assert row["workloadUidBefore"] == row["workloadUidAfter"]
        assert row["readyRemovedDuringFault"] is True
        assert row["readyAfterRecovery"] is True
        assert row["tokenOrKeyVersionBefore"] != row["tokenOrKeyVersionAfter"]
        assert row["sessionCookieDigest"] == baseline["sessionCookieDigest"]
        assert row["savedDataDigest"] == baseline["savedDataDigest"]
        assert row["fallbackCredentialObserved"] is False
        assert str(row["rawEvidenceRef"]).startswith("https://")


def test_live_rollover_evidence_explicitly_denies_every_fallback_class() -> None:
    evidence = load_evidence()
    assert evidence["fallbackDenials"] == {
        "workloadRestart": True,
        "cookieClearing": True,
        "password": True,
        "accessKey": True,
        "plaintextSecret": True,
        "savedDataLoss": True,
    }
