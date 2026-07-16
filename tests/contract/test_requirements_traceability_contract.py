from scripts.ci.contract_gate import validate_traceability


def test_every_requirement_and_task_is_traced() -> None:
    validate_traceability()
