"""Tests de POST /import/notion : Notion est remplacé par un faux serveur."""

import json

import httpx
import pytest

from app import notion_import


def notion_page(title: str) -> dict:
    """Une page Notion réduite à ce que l'import lit : sa propriété titre."""
    return {
        "object": "page",
        "properties": {
            "Done": {"type": "status", "status": {"name": "Not started"}},
            "Name": {"type": "title", "title": [{"plain_text": title}]},
        },
    }


@pytest.fixture
def fake_notion(monkeypatch):
    """Faux Notion : renvoie `pages` (découpées en `batches`) et garde les requêtes reçues."""
    state = {"batches": [[]], "status": 200, "requests": []}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        state["requests"].append({"url": str(request.url), "headers": request.headers, "body": body})
        if state["status"] != 200:
            return httpx.Response(state["status"], json={"message": "boom"})
        index = int(body.get("start_cursor") or 0)
        has_more = index + 1 < len(state["batches"])
        return httpx.Response(200, json={
            "results": [notion_page(t) for t in state["batches"][index]],
            "has_more": has_more,
            "next_cursor": str(index + 1) if has_more else None,
        })

    monkeypatch.setenv("NOTION_TOKEN", "secret-test")
    monkeypatch.delenv("NOTION_DATABASE_ID", raising=False)
    monkeypatch.setattr(
        notion_import, "get_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return state


def test_import_creates_items_from_titles(client, fake_notion):
    fake_notion["batches"] = [["Joint salle de bain", "Scalpel et lames"]]

    r = client.post("/import/notion")

    assert r.status_code == 200
    data = r.json()
    assert data["imported"] == 2
    assert data["skipped"] == 0
    assert [i["title"] for i in data["items"]] == ["Joint salle de bain", "Scalpel et lames"]
    for item in data["items"]:
        assert item["category"] == "autre"
        assert item["status"] == "a_chercher"
        assert item["notes"] is None and item["budget_max"] is None
    assert {i["title"] for i in client.get("/items").json()} == {"Joint salle de bain", "Scalpel et lames"}


def test_import_sends_inbox_filter_to_notion(client, fake_notion):
    client.post("/import/notion")

    request = fake_notion["requests"][0]
    assert request["url"] == f"https://api.notion.com/v1/databases/{notion_import.DEFAULT_DATABASE_ID}/query"
    assert request["headers"]["authorization"] == "Bearer secret-test"
    assert request["headers"]["notion-version"] == notion_import.NOTION_VERSION
    filters = request["body"]["filter"]["and"]
    assert {"property": "Category", "select": {"is_empty": True}} in filters
    assert {"property": "Project", "relation": {"is_empty": True}} in filters
    assert {"property": "Done", "status": {"does_not_equal": "Done"}} in filters


def test_import_follows_pagination(client, fake_notion):
    fake_notion["batches"] = [["A"], ["B"], ["C"]]

    data = client.post("/import/notion").json()

    assert data["imported"] == 3
    assert len(fake_notion["requests"]) == 3
    assert fake_notion["requests"][1]["body"]["start_cursor"] == "1"


def test_import_skips_duplicates_and_empty_titles(client, fake_notion):
    client.post("/items", json={"title": "Lampe de bureau", "category": "deco"})
    fake_notion["batches"] = [["lampe de bureau", "", "   ", "Pull", "Pull"]]

    data = client.post("/import/notion").json()

    assert data["imported"] == 1
    assert data["skipped"] == 2  # "lampe de bureau" (casse ignorée) + le 2e "Pull"
    # Relancer l'import ne crée rien de plus.
    again = client.post("/import/notion").json()
    assert again["imported"] == 0 and again["skipped"] == 3
    assert len(client.get("/items").json()) == 2


def test_import_truncates_long_titles(client, fake_notion):
    fake_notion["batches"] = [["x" * 250]]

    data = client.post("/import/notion").json()

    assert len(data["items"][0]["title"]) == 200


def test_import_uses_configured_database_id(client, fake_notion, monkeypatch):
    monkeypatch.setenv("NOTION_DATABASE_ID", "autre-base")
    client.post("/import/notion")
    assert "/databases/autre-base/query" in fake_notion["requests"][0]["url"]


def test_import_without_token_is_503(client, monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    r = client.post("/import/notion")

    assert r.status_code == 503
    assert "NOTION_TOKEN" in r.json()["detail"]


@pytest.mark.parametrize("status, expected", [(401, "NOTION_TOKEN"), (404, "Connexions"), (500, "boom")])
def test_import_notion_errors_are_502_with_message(client, fake_notion, status, expected):
    fake_notion["status"] = status

    r = client.post("/import/notion")

    assert r.status_code == 502
    assert expected in r.json()["detail"]
    assert client.get("/items").json() == []


def test_import_network_error_is_502(client, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("hors ligne")

    monkeypatch.setenv("NOTION_TOKEN", "secret-test")
    monkeypatch.setattr(
        notion_import, "get_http_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    r = client.post("/import/notion")
    assert r.status_code == 502
    assert "Impossible de joindre Notion" in r.json()["detail"]
