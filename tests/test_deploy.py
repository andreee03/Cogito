"""Tests du jalon 5 : CORS et URL de base Postgres (Neon / Render)."""

import pytest

from app.db import normalize_database_url

FRONT = "http://localhost:5173"  # présent dans ALLOWED_ORIGINS par défaut


def test_cors_allows_front_end(client):
    r = client.get("/health", headers={"Origin": FRONT})
    assert r.headers["access-control-allow-origin"] == FRONT


def test_cors_preflight_for_patch(client):
    # Avant un PATCH/PUT/DELETE, le navigateur envoie une requête OPTIONS de "pré-vol".
    r = client.options("/results/1", headers={
        "Origin": FRONT,
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "content-type",
    })
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == FRONT
    assert "PATCH" in r.headers["access-control-allow-methods"]


def test_cors_rejects_unknown_origin(client):
    r = client.get("/health", headers={"Origin": "https://site-inconnu.example"})
    assert "access-control-allow-origin" not in r.headers


def test_allowed_origins_parsing(monkeypatch):
    from app.main import allowed_origins

    monkeypatch.setenv("ALLOWED_ORIGINS", " https://front.onrender.com/ , http://localhost:5173,, ")
    assert allowed_origins() == ["https://front.onrender.com", "http://localhost:5173"]


@pytest.mark.parametrize("url, expected", [
    ("postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require",
     "postgresql+psycopg://u:p@ep-x.eu-central-1.aws.neon.tech/neondb?sslmode=require"),
    ("postgres://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
    ("sqlite:///./shopping.db", "sqlite:///./shopping.db"),
])
def test_normalize_database_url(url, expected):
    assert normalize_database_url(url) == expected
