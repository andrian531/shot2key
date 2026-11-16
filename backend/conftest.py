"""Shared pytest fixtures.

Every test runs against throwaway data/uploads/outputs directories so the real
``backend/data`` folder is never touched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def env(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("SHOT2KEY_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SHOT2KEY_UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SHOT2KEY_OUTPUTS_DIR", str(tmp_path / "outputs"))
    return tmp_path


@pytest.fixture()
def client(env):
    """FastAPI TestClient with the app lifespan executed."""
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as test_client:
        yield test_client
