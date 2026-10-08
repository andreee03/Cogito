"""Tests du jalon 4 : itérations avec contexte, réactions, limite de 3 itérations.
Plus le mode FAKE_CLAUDE (faux Claude gratuit pour le développement)."""

import pytest

from app import cogitate
from app import fake_claude as fake_claude_module
from tests.test_cogitate import ANSWER, fake_claude as fake_claude_fixture, fake_response, new_item  # noqa: F401

fake_claude = fake_claude_fixture  # la fixture est réutilisée telle quelle


def cogitate_and_get(client, item_id, feedback=None):
    r = client.post(f"/items/{item_id}/cogitate", json={"feedback": feedback})
    assert r.status_code == 202, r.text
    return client.get(f"/searches/{r.json()['search_id']}").json()


# ---------------------------------------------------------------------------
# Réactions
# ---------------------------------------------------------------------------

def test_reaction_like_dislike_and_reset(client, fake_claude):
    fake_claude.responses = [fake_response(ANSWER)]
    item = new_item(client)
    result_id = cogitate_and_get(client, item["id"])["results"][0]["id"]

    for reaction in ["like", "dislike", None]:
        r = client.patch(f"/results/{result_id}", json={"reaction": reaction})
        assert r.status_code == 200
        assert r.json()["reaction"] == reaction
        assert r.json()["id"] == result_id

    assert client.patch(f"/results/{result_id}", json={"reaction": "love"}).status_code == 422
    assert client.patch(f"/results/{result_id}", json={}).status_code == 422
    assert client.patch("/results/999", json={"reaction": "like"}).status_code == 404


# ---------------------------------------------------------------------------
# Itérations avec contexte
# ---------------------------------------------------------------------------

def test_second_iteration_gets_compact_summary(client, fake_claude):
    fake_claude.responses = [fake_response(ANSWER), fake_response(ANSWER)]
    item = new_item(client)
    first = cogitate_and_get(client, item["id"])
    liked, disliked = first["results"]
    client.patch(f"/results/{liked['id']}", json={"reaction": "like"})
    client.patch(f"/results/{disliked['id']}", json={"reaction": "dislike"})

    second = cogitate_and_get(client, item["id"], feedback="moins cher")
    assert second["iteration"] == 2

    first_prompt = fake_claude.calls[0]["messages"][0]["content"]
    prompt = fake_claude.calls[1]["messages"][0]["content"]
    assert "Ce que tu m'as déjà proposé" not in first_prompt
    assert "### Itération 1" in prompt
    assert "- Lampe Orbe (Maison Halde, 175 EUR) — J'AIME" in prompt
    assert "- Lampe Arc (Atelier X, 240 EUR) — JE N'AIME PAS" in prompt
    assert "moins cher" in prompt
    # Résumé compact : ni URL ni description des recherches précédentes.
    assert "https://" not in prompt
    assert "Laiton brossé" not in prompt


def test_third_iteration_summarizes_both_previous(client, fake_claude):
    fake_claude.responses = [fake_response(ANSWER)] * 3
    item = new_item(client)
    cogitate_and_get(client, item["id"])
    cogitate_and_get(client, item["id"], feedback="trop classique")
    cogitate_and_get(client, item["id"], feedback="plus coloré")

    prompt = fake_claude.calls[2]["messages"][0]["content"]
    assert "### Itération 1" in prompt and "### Itération 2" in prompt
    assert "Mon retour avant cette itération : trop classique" in prompt
    assert prompt.rstrip().endswith("Trouve-moi entre 5 et 8 produits et termine par le bloc JSON demandé.")
    assert "plus coloré" in prompt


# ---------------------------------------------------------------------------
# Limite de 3 itérations
# ---------------------------------------------------------------------------

def test_limit_of_three_iterations(client, fake_claude):
    fake_claude.responses = [fake_response(ANSWER)] * 3
    item = new_item(client)
    for expected in [1, 2, 3]:
        assert cogitate_and_get(client, item["id"])["iteration"] == expected

    r = client.post(f"/items/{item['id']}/cogitate", json={"feedback": "encore"})
    assert r.status_code == 409
    assert "3 itérations" in r.json()["detail"]
    assert client.get(f"/items/{item['id']}").json()["iterations_count"] == 3
    assert len(fake_claude.calls) == 3


def test_failed_search_does_not_use_an_iteration(client, fake_claude):
    fake_claude.responses = [fake_response("Pas de JSON ici."), fake_response(ANSWER)]
    item = new_item(client)

    failed = cogitate_and_get(client, item["id"])
    assert failed["status"] == "error"
    assert client.get(f"/items/{item['id']}").json()["iterations_count"] == 0

    retry = cogitate_and_get(client, item["id"])
    assert retry["status"] == "done"
    assert retry["iteration"] == 1          # même numéro : l'essai raté ne compte pas
    # Les recherches en erreur n'apparaissent pas dans le résumé envoyé à Claude.
    assert "### Itération" not in fake_claude.calls[1]["messages"][0]["content"]
    assert client.get(f"/items/{item['id']}").json()["iterations_count"] == 1
    assert len(client.get(f"/items/{item['id']}/searches").json()) == 2  # historique complet


# ---------------------------------------------------------------------------
# Mode FAKE_CLAUDE
# ---------------------------------------------------------------------------

def test_fake_claude_mode(client, monkeypatch):
    monkeypatch.undo()  # retire le garde-fou de conftest : on veut le vrai get_client
    monkeypatch.setenv("FAKE_CLAUDE", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # aucune clé nécessaire
    monkeypatch.setattr(fake_claude_module, "DELAY_SECONDS", 0)

    async def no_network(products):  # pas de vrais appels réseau dans les tests
        return [{**p, "link_verified": False, "price_verified": False} for p in products]
    monkeypatch.setattr(cogitate, "verify_products", no_network)

    item = new_item(client)
    first = cogitate_and_get(client, item["id"])
    assert first["status"] == "done"
    assert first["cost_usd"] == 0
    assert len(first["results"]) == 5

    second = cogitate_and_get(client, item["id"], feedback="autre chose")
    names = lambda s: {r["name"] for r in s["results"]}  # noqa: E731
    assert names(first) != names(second)  # la 2e itération propose autre chose
