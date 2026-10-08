"""Tests du jalon 3 : app/cogitate.py et les routes de recherche.

L'API Claude est simulée par un faux client (FakeClient) et la vérification
des liens par une fausse fonction : aucun appel réseau, aucun coût.
"""

import asyncio
from types import SimpleNamespace

import pytest
from sqlmodel import Session

from app import cogitate
from app.cogitate import CogitateError, ask_claude, build_user_prompt, estimate_cost, parse_products
from app.db import engine
from app.models import Category, Item, Search, SearchStatus

# ---------------------------------------------------------------------------
# Faux client Claude
# ---------------------------------------------------------------------------

PRODUCTS_JSON = """{"products": [
  {"name": "Lampe Orbe", "brand": "Maison Halde", "price": 189, "currency": "eur",
   "url": "https://www.maison-halde.example/produit/lampe-orbe",
   "image_url": null, "description": "Laiton brossé", "why_it_fits": "Sobre et durable",
   "score": 92},
  {"name": "Lampe Arc", "brand": "Atelier X", "price": "240,00", "currency": "EUR",
   "url": "https://atelier-x.example/arc", "image_url": "https://atelier-x.example/arc.jpg",
   "description": null, "why_it_fits": "Pièce de créateur", "score": 140},
  {"name": "Sans URL", "url": null, "why_it_fits": "ignoré", "score": 50}
]}"""

ANSWER = f"Voici ma sélection, après plusieurs recherches.\n\n```json\n{PRODUCTS_JSON}\n```\nBonne lecture !"


def fake_response(text: str, stop_reason="end_turn", input_tokens=10_000, output_tokens=2_000, searches=3):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            server_tool_use=SimpleNamespace(web_search_requests=searches),
        ),
    )


class FakeClient:
    """Imite anthropic.AsyncAnthropic : renvoie les réponses prévues, dans l'ordre,
    et garde une trace de chaque appel."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.messages = self  # pour que client.messages.create(...) fonctionne

    async def create(self, **kwargs):
        # On copie la liste : ask_claude la modifie ensuite (pause_turn).
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


async def fake_verify(products):
    """Remplace verify_products : 1er lien OK avec prix corrigé, les autres morts."""
    results = []
    for i, p in enumerate(products):
        ok = i == 0
        results.append({**p, "link_verified": ok, "price_verified": ok,
                        "price": 175.0 if ok else p["price"]})
    return sorted(results, key=lambda p: not p["link_verified"])


@pytest.fixture
def fake_claude(monkeypatch):
    """Installe un faux client ; le test lui donne ses réponses via .responses."""
    client = FakeClient()
    monkeypatch.setattr(cogitate, "get_client", lambda: client)
    monkeypatch.setattr(cogitate, "verify_products", fake_verify)
    return client


# ---------------------------------------------------------------------------
# 1. Fonctions unitaires
# ---------------------------------------------------------------------------

def test_parse_products_with_text_around():
    products = parse_products(ANSWER)
    assert [p["name"] for p in products] == ["Lampe Orbe", "Lampe Arc"]  # "Sans URL" ignoré
    assert products[0]["currency"] == "EUR"
    assert products[1]["price"] == 240.0       # "240,00" -> 240.0
    assert products[1]["score"] == 100         # 140 ramené à 100
    assert products[0]["image_url"] is None


def test_parse_products_without_code_fence():
    assert len(parse_products(f"Résultat : {PRODUCTS_JSON} fin.")) == 2


def test_parse_products_takes_the_last_block():
    first = '{"products": [{"name": "Brouillon", "url": "https://a.example/x", "score": 1}]}'
    products = parse_products(f"{first}\nVersion finale :\n{PRODUCTS_JSON}")
    assert products[0]["name"] == "Lampe Orbe"


@pytest.mark.parametrize("text", [
    "Désolé, je n'ai rien trouvé.",
    '```json\n{"products": [{"name": "X", "url": "https://x.example",}\n```',  # JSON cassé
    '{"products": []}',
])
def test_parse_products_errors(text):
    with pytest.raises(CogitateError):
        parse_products(text)


def test_estimate_cost():
    usage = fake_response("", input_tokens=1_000_000, output_tokens=200_000, searches=5).usage
    assert estimate_cost(usage) == pytest.approx(1.0 + 1.0 + 0.05)

    usage.server_tool_use = None  # pas de recherche web
    assert estimate_cost(usage) == pytest.approx(2.0)


def test_build_user_prompt():
    item = Item(title="Lampe de chevet", category=Category.deco, notes="laiton",
                custom_prompt="Pas de LED visible", budget_max=250)
    prompt = build_user_prompt("J'aime le minimalisme.", item, feedback="moins cher")
    for expected in ["J'aime le minimalisme.", "Lampe de chevet", "meubles / déco",
                     "laiton", "Pas de LED visible", "250 €", "moins cher"]:
        assert expected in prompt


def test_ask_claude_sends_the_right_request():
    client = FakeClient(fake_response(ANSWER))
    answer = asyncio.run(ask_claude(client, "Ma demande"))

    [call] = client.calls
    assert call["model"] == "claude-haiku-4-5"
    assert call["tools"] == [cogitate.WEB_SEARCH_TOOL]
    assert call["tools"][0]["type"] == "web_search_20250305"
    assert call["tools"][0]["user_location"]["country"] == "FR"
    assert call["system"] == cogitate.COGITATE_SYSTEM_PROMPT
    assert call["messages"] == [{"role": "user", "content": "Ma demande"}]
    assert "Lampe Orbe" in answer.text


def test_ask_claude_resumes_after_pause_turn():
    paused = fake_response("Je cherche encore…", stop_reason="pause_turn")
    client = FakeClient(paused, fake_response(ANSWER))
    answer = asyncio.run(ask_claude(client, "Ma demande"))

    assert len(client.calls) == 2
    # 2e appel : même demande + la réponse en pause renvoyée telle quelle.
    assert client.calls[1]["messages"] == [
        {"role": "user", "content": "Ma demande"},
        {"role": "assistant", "content": paused.content},
    ]
    assert answer.cost_usd == pytest.approx(2 * (0.01 + 0.01 + 0.03))  # coûts additionnés
    assert len(parse_products(answer.text)) == 2


def test_ask_claude_gives_up_after_too_many_pauses():
    pauses = [fake_response("…", stop_reason="pause_turn")] * (cogitate.MAX_CONTINUATIONS + 1)
    with pytest.raises(CogitateError):
        asyncio.run(ask_claude(FakeClient(*pauses), "Ma demande"))


# ---------------------------------------------------------------------------
# 2. Routes (la tâche de fond s'exécute avant que client.post rende la main)
# ---------------------------------------------------------------------------

def new_item(client, **extra):
    body = {"title": "Lampe de chevet", "category": "deco", "budget_max": 250, **extra}
    return client.post("/items", json=body).json()


def test_cogitate_full_flow(client, fake_claude):
    fake_claude.responses = [fake_response(ANSWER)]
    item = new_item(client)

    r = client.post(f"/items/{item['id']}/cogitate", json={"feedback": None})
    assert r.status_code == 202
    search_id = r.json()["search_id"]
    assert r.json() == {"search_id": search_id}

    search = client.get(f"/searches/{search_id}").json()
    assert set(search) == {"id", "item_id", "iteration", "feedback", "status", "error",
                           "created_at", "cost_usd", "results"}
    assert search["status"] == "done"
    assert search["error"] is None
    assert search["iteration"] == 1
    assert search["created_at"].endswith("Z")
    assert search["cost_usd"] == pytest.approx(0.05)  # 0,01 + 0,01 + 3 × 0,01

    first, second = search["results"]
    assert set(first) == {"id", "search_id", "name", "brand", "price", "currency", "url",
                          "image_url", "description", "why_it_fits", "score",
                          "link_verified", "price_verified", "reaction"}
    assert first["name"] == "Lampe Orbe"
    assert first["price"] == 175.0                     # prix vérifié sur la page
    assert first["link_verified"] is True and first["price_verified"] is True
    assert second["link_verified"] is False
    assert first["reaction"] is None

    # Le prompt envoyé contient bien le profil et l'article.
    sent = fake_claude.calls[0]["messages"][0]["content"]
    assert "Lampe de chevet" in sent and "Mes goûts" in sent

    item = client.get(f"/items/{item['id']}").json()
    assert item["status"] == "resultats"
    assert item["iterations_count"] == 1

    assert client.get(f"/items/{item['id']}/searches").json() == [search]


def test_cogitate_unreadable_answer_marks_error(client, fake_claude):
    fake_claude.responses = [fake_response("Je n'ai rien trouvé, désolé.")]
    item = new_item(client)

    search_id = client.post(f"/items/{item['id']}/cogitate", json={}).json()["search_id"]
    search = client.get(f"/searches/{search_id}").json()
    assert search["status"] == "error"
    assert "JSON" in search["error"]
    assert search["results"] == []
    assert search["cost_usd"] is not None  # l'appel a quand même coûté
    assert client.get(f"/items/{item['id']}").json()["status"] == "a_chercher"


def test_cogitate_api_failure_marks_error(client, monkeypatch):
    class BrokenClient:
        class messages:
            @staticmethod
            async def create(**kwargs):
                raise ConnectionError("réseau coupé")
    monkeypatch.setattr(cogitate, "get_client", BrokenClient)
    item = new_item(client)

    search_id = client.post(f"/items/{item['id']}/cogitate", json={}).json()["search_id"]
    search = client.get(f"/searches/{search_id}").json()
    assert search["status"] == "error"
    assert "réseau coupé" in search["error"]


def test_cogitate_409_when_search_running(client, fake_claude):
    item = new_item(client)
    with Session(engine) as session:  # on simule une recherche en cours
        session.add(Search(item_id=item["id"], iteration=1, status=SearchStatus.running))
        session.commit()

    r = client.post(f"/items/{item['id']}/cogitate", json={"feedback": None})
    assert r.status_code == 409
    assert fake_claude.calls == []


def test_feedback_is_saved_and_sent(client, fake_claude):
    fake_claude.responses = [fake_response(ANSWER), fake_response(ANSWER)]
    item = new_item(client)
    client.post(f"/items/{item['id']}/cogitate", json={"feedback": None})
    r = client.post(f"/items/{item['id']}/cogitate", json={"feedback": "trop classique"})

    search = client.get(f"/searches/{r.json()['search_id']}").json()
    assert search["iteration"] == 2
    assert search["feedback"] == "trop classique"
    assert "trop classique" in fake_claude.calls[1]["messages"][0]["content"]
    assert [s["iteration"] for s in client.get(f"/items/{item['id']}/searches").json()] == [1, 2]


def test_404s(client):
    assert client.post("/items/999/cogitate", json={}).status_code == 404
    assert client.get("/items/999/searches").status_code == 404
    assert client.get("/searches/999").status_code == 404


def test_interrupted_searches_are_failed_on_startup(client):
    from app.cogitate import fail_interrupted_searches

    item = new_item(client)
    with Session(engine) as session:
        session.add(Search(item_id=item["id"], iteration=1, status=SearchStatus.running))
        db_item = session.get(Item, item["id"])
        db_item.status = "en_recherche"
        session.add(db_item)
        session.commit()

    fail_interrupted_searches()
    [search] = client.get(f"/items/{item['id']}/searches").json()
    assert search["status"] == "error"
    assert client.get(f"/items/{item['id']}").json()["status"] == "a_chercher"


def test_missing_api_key_gives_clear_error(monkeypatch):
    monkeypatch.undo()  # retire le garde-fou de conftest pour tester le vrai get_client
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(CogitateError, match="ANTHROPIC_API_KEY"):
        cogitate.get_client()
