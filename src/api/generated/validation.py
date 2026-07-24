"""Runtime operation-registration validation against generated inventory."""

from .core_api_models import CORE_OPERATIONS


def validate_registered_operations(operation_ids: set[str]) -> None:
    unknown = operation_ids - set(CORE_OPERATIONS)
    if unknown:
        raise RuntimeError(f"Unknown core operation registrations: {sorted(unknown)}")
