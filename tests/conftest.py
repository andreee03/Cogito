"""Configuration commune des tests.

On pointe DATABASE_URL vers une base temporaire AVANT d'importer l'application,
pour ne jamais toucher à ta vraie base shopping.db.
"""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    # Base vide à chaque test, pour que les tests soient indépendants.
    SQLModel.metadata.drop_all(engine)
    with TestClient(app) as c:  # "with" déclenche le démarrage (création des tables)
        yield c
