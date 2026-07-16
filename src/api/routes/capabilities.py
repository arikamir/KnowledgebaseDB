from __future__ import annotations

from fastapi import APIRouter

from api.generated.core_api_models import CORE_CONTRACT_DIGEST, CORE_OPERATIONS

router = APIRouter()


@router.get("/capabilities", operation_id="getCoreCapabilities")
def capabilities() -> dict[str, object]:
    mutations = sorted(operation for operation in CORE_OPERATIONS if operation.startswith(("create", "start", "complete", "answer", "submit", "report")))
    return {
        "contract_version": "1.0.0",
        "contract_digest": CORE_CONTRACT_DIGEST,
        "catalog_version": "1.0.0",
        "supported_contract_versions": ["1.0.0"],
        "supported_mutations": mutations,
    }
