"""Configuration commune des tests.

On pointe DATABASE_URL vers une base temporaire AVANT d'importer l'application,
pour ne jamais toucher à ta vraie base shopping.db.
"""

import os
import tempfile

# TEST_DATABASE_URL (facultatif) : lancer les tests sur une base Postgres de
# test. ATTENTION : elle est vidée à chaque test, ne jamais y mettre ta vraie base.
os.environ["DATABASE_URL"] = (
    os.getenv("TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/test.db"
)
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")
# Les tests ne dépendent pas de ton .env : le mode FAKE_CLAUDE y est coupé
# (load_dotenv ne remplace jamais une variable déjà définie).
os.environ["FAKE_CLAUDE"] = "0"

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


@pytest.fixture(autouse=True)
def no_real_claude(monkeypatch):
    """Garde-fou : si un test oublie de simuler Claude, il échoue au lieu
    d'appeler (et de payer) la vraie API."""
    def forbidden():
        raise RuntimeError("Un test a tenté d'appeler la vraie API Claude !")
    monkeypatch.setattr("app.cogitate.get_client", forbidden)
