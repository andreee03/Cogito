"""Tests de app/verify.py.

Aucun accès Internet : les pages sont lues dans tests/fixtures, et le réseau est
simulé avec httpx.MockTransport (un faux serveur qui répond ce qu'on veut).
"""

import asyncio
from pathlib import Path

import httpx
import pytest

from app import verify
from app.verify import extract_product_data, parse_price, verify_products

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Extraction depuis les 3 pages d'exemple
# ---------------------------------------------------------------------------

def test_jsonld_in_graph():
    data = extract_product_data(fixture("jsonld_graph.html"), "https://www.maison-halde.example/produit/lampe-orbe")
    assert data.name == "Lampe Orbe en laiton"
    assert data.brand == "Maison Halde"                 # brand sous forme d'objet
    assert data.price == 189.0                           # JSON-LD prioritaire sur og (210)
    assert data.currency == "EUR"                        # et pas le prix du produit associé (12)
    assert data.image_url == "https://www.maison-halde.example/media/orbe-1.jpg"


def test_jsonld_in_list_with_broken_blocks():
    data = extract_product_data(fixture("jsonld_list.html"), "https://www.atelier-verone.example/vestes/laine")
    assert data.name == "Veste en laine bouillie"
    assert data.brand == "Atelier Vérone"
    assert data.price == 1290.0                          # AggregateOffer.lowPrice
    assert data.currency == "EUR"
    assert data.image_url == "https://www.atelier-verone.example/media/veste-laine.jpg"  # relative -> absolue


def test_opengraph_fallback():
    data = extract_product_data(fixture("opengraph_only.html"), "https://www.coutellerie.example/couteau")
    assert data.name == "Couteau d'office en damas"
    assert data.brand is None
    assert data.price == 89.9                            # "89,90" format français
    assert data.currency == "EUR"                        # "eur" -> "EUR"
    assert data.image_url == "https://cdn.coutellerie.example/img/couteau-office.jpg"


def test_page_without_any_data():
    data = extract_product_data("<html><body><h1>Rien</h1></body></html>", "https://x.example/")
    assert data.price is None and data.image_url is None and data.name is None


@pytest.mark.parametrize("raw, expected", [
    ("189.00", 189.0),
    (129.9, 129.9),
    ("89,90", 89.9),
    ("1 290,00 €", 1290.0),
    ("1 290,00 €", 1290.0),   # espaces insécables (format français)
    ("1.299,00", 1299.0),
    ("1,299.00", 1299.0),
    ("1,299", 1299.0),
    ("0", None),
    ("0.00", None),
    ("", None),
    ("sur devis", None),
    (None, None),
    (True, None),
])
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


# ---------------------------------------------------------------------------
# 2. Vérification complète avec un faux réseau
# ---------------------------------------------------------------------------

HTML = {"content-type": "text/html; charset=utf-8"}

ROUTES = {
    "https://www.maison-halde.example/produit/lampe-orbe": fixture("jsonld_graph.html"),
    "https://www.coutellerie.example/couteau": fixture("opengraph_only.html"),
    "https://www.coutellerie.example/": "<html><body>Accueil</body></html>",
    "https://shop.example/sans-donnees": "<html><body>Rien</body></html>",
}

seen_user_agents: list[str] = []


async def fake_server(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    seen_user_agents.append(request.headers.get("user-agent", ""))
    if url == "https://panne.example/produit":
        raise httpx.ConnectError("connexion refusée", request=request)
    if url == "https://lent.example/produit":
        await asyncio.sleep(5)
    if url == "https://www.coutellerie.example/ancien-produit":
        return httpx.Response(301, headers={"location": "https://www.coutellerie.example/"})
    if url in ROUTES:
        return httpx.Response(200, text=ROUTES[url], headers=HTML)
    return httpx.Response(404, text="Introuvable", headers=HTML)


def ai_product(url: str, **extra) -> dict:
    """Un produit tel que l'IA le renverrait."""
    return {
        "name": "Produit IA", "brand": "Marque IA", "price": 999.0, "currency": "EUR",
        "url": url, "image_url": "https://ia.example/image.jpg",
        "description": "desc", "why_it_fits": "parce que", "score": 80, **extra,
    }


def run_verify(products: list[dict]) -> list[dict]:
    async def main():
        transport = httpx.MockTransport(fake_server)
        async with httpx.AsyncClient(transport=transport, follow_redirects=True) as client:
            return await verify_products(products, client)
    return asyncio.run(main())


def test_verified_page_replaces_price_and_image():
    product = ai_product("https://www.maison-halde.example/produit/lampe-orbe")
    [result] = run_verify([product])

    assert result["link_verified"] is True
    assert result["price_verified"] is True
    assert result["price"] == 189.0                                   # remplacé
    assert result["image_url"] == "https://www.maison-halde.example/media/orbe-1.jpg"
    assert result["name"] == "Produit IA"                              # gardé
    assert result["why_it_fits"] == "parce que"                        # gardé
    assert product["price"] == 999.0                                   # l'original n'est pas modifié


def test_page_without_data_keeps_ai_values():
    [result] = run_verify([ai_product("https://shop.example/sans-donnees")])
    assert result["link_verified"] is True
    assert result["price_verified"] is False
    assert result["price"] == 999.0
    assert result["image_url"] == "https://ia.example/image.jpg"


def test_missing_brand_is_filled_from_page():
    [result] = run_verify([ai_product("https://www.maison-halde.example/produit/lampe-orbe", brand=None)])
    assert result["brand"] == "Maison Halde"


@pytest.mark.parametrize("url", [
    "https://shop.example/produit-inexistant",          # 404
    "https://panne.example/produit",                    # erreur réseau
    "https://www.coutellerie.example/ancien-produit",   # redirection vers l'accueil
    "pas-une-url",                                       # URL invalide
])
def test_broken_links_are_flagged(url):
    [result] = run_verify([ai_product(url)])
    assert result["link_verified"] is False
    assert result["price_verified"] is False
    assert result["price"] == 999.0


def test_timeout(monkeypatch):
    monkeypatch.setattr(verify, "TIMEOUT_SECONDS", 0.1)
    [result] = run_verify([ai_product("https://lent.example/produit")])
    assert result["link_verified"] is False


def test_broken_links_go_last_and_order_is_kept():
    products = [
        ai_product("https://shop.example/mort-1", name="A"),
        ai_product("https://www.maison-halde.example/produit/lampe-orbe", name="B"),
        ai_product("https://panne.example/produit", name="C"),
        ai_product("https://www.coutellerie.example/couteau", name="D"),
    ]
    results = run_verify(products)
    assert [r["name"] for r in results] == ["B", "D", "A", "C"]
    assert [r["link_verified"] for r in results] == [True, True, False, False]


def test_browser_user_agent_is_sent():
    seen_user_agents.clear()
    run_verify([ai_product("https://shop.example/sans-donnees")])
    assert seen_user_agents and "Mozilla/5.0" in seen_user_agents[0]
