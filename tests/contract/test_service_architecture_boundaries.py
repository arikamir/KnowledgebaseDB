from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source(directory: str) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / directory).rglob("*.ts*") if "node_modules" not in path.parts and "tests" not in path.parts)


def test_ui_calls_only_the_bff_and_has_no_storage_or_core_dependency() -> None:
    ui = source("ui/src")
    assert "/api/v1" not in ui
    assert "postgres" not in ui.casefold()
    assert "redis" not in ui.casefold()
    assert "localStorage.setItem" not in ui
    assert "sessionStorage.setItem" not in ui


def test_bff_has_no_database_dependency_or_cross_service_source_import() -> None:
    bff = source("bff/src")
    assert "sqlalchemy" not in bff.casefold()
    assert "psycopg" not in bff.casefold()
    assert "../../src/" not in bff
