"""Pytest fixtures for the DevOps career agent."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent.settings import AppSettings
from api.app import create_app
from api.route_helpers import build_container


@pytest.fixture()
def app_container(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'devops-career-agent.sqlite3'}"
    settings = AppSettings(database_url=database_url)
    return build_container(settings)


@pytest.fixture()
def app(app_container):
    return create_app(settings=app_container.settings, container=app_container)


@pytest.fixture()
def client(app):
    return TestClient(app)
