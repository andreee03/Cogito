"""Tests du jalon 1 : /health, /profile et le CRUD des articles."""

from app.prompts import DEFAULT_MASTER_PROMPT


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_profile_default_then_update(client):
    assert client.get("/profile").json() == {"master_prompt": DEFAULT_MASTER_PROMPT}

    r = client.put("/profile", json={"master_prompt": "Minimalisme japonais."})
    assert r.status_code == 200
    assert client.get("/profile").json() == {"master_prompt": "Minimalisme japonais."}


def test_create_item_shape(client):
    r = client.post("/items", json={"title": "Lampe de bureau", "category": "deco", "budget_max": 250})
    assert r.status_code == 200
    item = r.json()
    assert set(item) == {
        "id", "title", "category", "notes", "custom_prompt", "budget_max",
        "status", "created_at", "iterations_count",
    }
    assert item["status"] == "a_chercher"
    assert item["iterations_count"] == 0
    assert item["notes"] is None
    assert item["created_at"].endswith("Z")  # ISO 8601 en UTC


def test_invalid_category_rejected(client):
    r = client.post("/items", json={"title": "X", "category": "voitures"})
    assert r.status_code == 422


def test_list_most_recent_first(client):
    for title in ["Premier", "Deuxième", "Troisième"]:
        client.post("/items", json={"title": title, "category": "autre"})
    titles = [i["title"] for i in client.get("/items").json()]
    assert titles == ["Troisième", "Deuxième", "Premier"]


def test_patch_partial(client):
    item = client.post("/items", json={"title": "Veste", "category": "vetements", "notes": "laine"}).json()

    r = client.patch(f"/items/{item['id']}", json={"budget_max": 400, "status": "achete"})
    assert r.status_code == 200
    updated = r.json()
    assert updated["budget_max"] == 400
    assert updated["status"] == "achete"
    assert updated["notes"] == "laine"  # champ non envoyé : inchangé

    # On peut vider un champ facultatif…
    assert client.patch(f"/items/{item['id']}", json={"notes": None}).json()["notes"] is None
    # …mais pas un champ obligatoire.
    assert client.patch(f"/items/{item['id']}", json={"title": None}).status_code == 422


def test_get_and_delete(client):
    item = client.post("/items", json={"title": "Tournevis", "category": "outils"}).json()
    assert client.get(f"/items/{item['id']}").status_code == 200

    r = client.delete(f"/items/{item['id']}")
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"/items/{item['id']}").status_code == 404
    assert client.delete(f"/items/{item['id']}").status_code == 404
