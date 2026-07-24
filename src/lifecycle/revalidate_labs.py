"""Scheduled row-version-safe lab reference revalidation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from agent.lab_reference_validator import LabDestinationValidator
from storage.lab_repository import LabReferenceConflict, LabRepository


@dataclass(slots=True)
class LabRevalidationJob:
    repository: LabRepository
    validator: LabDestinationValidator
    approved_domains: Callable[[str, str], set[str]]
    validator_identity_id: str
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def run(self, *, limit: int = 100) -> dict[str, int]:
        counts = {"checked": 0, "conflicted": 0, "failed": 0}
        for reference in self.repository.due(self.now(), limit=limit):
            attempted_at = self.now()
            domains = self.approved_domains(reference.provider, reference.provider_policy_version)
            if not domains:
                self.repository.invalidate_removed_policy(reference.provider, reference.provider_policy_version, now=attempted_at)
                counts["failed"] += 1
                continue
            result = self.validator.validate_reference(reference, domains)
            try:
                self.repository.record_validation(
                    reference.id, expected_version=reference.row_version,
                    policy_version=reference.provider_policy_version, result=result.result,
                    attempted_at=attempted_at, validator_identity_id=self.validator_identity_id,
                    status_code=result.status_code, redirect_domains=list(result.redirect_domains),
                    error_code=result.error_code, scheduled=True,
                )
                counts["checked"] += 1
                if result.result != "success": counts["failed"] += 1
            except LabReferenceConflict:
                counts["conflicted"] += 1
        return counts


def main() -> None:
    raise SystemExit("Runtime wiring requires the lab-validation workload's exact database and network identity.")


if __name__ == "__main__":
    main()
