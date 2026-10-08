"""Vérification des liens produits proposés par l'IA.

Pour chaque produit (en parallèle) :
1. on télécharge la page (timeout 10 s, User-Agent de navigateur) ;
2. si erreur réseau, statut >= 400 ou redirection vers l'accueil : link_verified = False ;
3. sinon on lit les données structurées de la page :
   - d'abord le JSON-LD (<script type="application/ld+json">, objet @type "Product") ;
   - à défaut, les balises meta og:title, og:image, product:price:amount/currency ;
4. un prix trouvé sur la page REMPLACE celui de l'IA (price_verified = True),
   et une image trouvée sur la page remplace celle de l'IA.

Les produits dont le lien est mort sont gardés, mais placés en fin de liste.
"""

import asyncio
import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10.0
MAX_PAGE_BYTES = 5_000_000  # on ne lit pas plus de 5 Mo par page

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

CURRENCY_SYMBOLS = {"€": "EUR", "$": "USD", "£": "GBP", "CHF": "CHF"}


# ---------------------------------------------------------------------------
# 1. Extraction des données d'une page (fonctions pures, faciles à tester)
# ---------------------------------------------------------------------------

@dataclass
class PageData:
    """Ce qu'on a réussi à lire sur la page produit."""
    name: str | None = None
    brand: str | None = None
    price: float | None = None
    currency: str | None = None
    image_url: str | None = None


def parse_price(value: Any) -> float | None:
    """Convertit "1 290,00 €", "1,299.00", "89,90" ou 129.9 en float.

    Renvoie None si ce n'est pas un prix exploitable (vide, 0, négatif…).
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        price = float(value)
    else:
        # On ne garde que chiffres, virgules et points (les espaces, y compris
        # insécables, servent de séparateur de milliers en français).
        s = re.sub(r"[^\d,.]", "", str(value))
        if not s:
            return None
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):   # format européen : 1.299,00
                s = s.replace(".", "").replace(",", ".")
            else:                              # format anglais : 1,299.00
                s = s.replace(",", "")
        elif "," in s:
            head, _, tail = s.rpartition(",")
            if len(tail) == 3 and head:        # 1,299 -> milliers
                s = s.replace(",", "")
            else:                              # 89,90 -> décimales
                s = head.replace(",", "") + "." + tail
        elif s.count(".") > 1:                 # 1.299.000 -> milliers
            s = s.replace(".", "")
        try:
            price = float(s)
        except ValueError:
            return None
    if not math.isfinite(price) or price <= 0:
        return None
    return round(price, 2)


def normalize_currency(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    return CURRENCY_SYMBOLS.get(value, value.upper())


def _load_json(text: str) -> Any:
    """json.loads tolérant : beaucoup de sites publient du JSON-LD imparfait."""
    text = text.strip()
    # Enveloppes parfois présentes : <!-- ... --> ou //<![CDATA[ ... //]]>
    text = re.sub(r"^\s*(<!--|(//\s*)?<!\[CDATA\[)", "", text)
    text = re.sub(r"(-->|(//\s*)?\]\]>)\s*$", "", text)
    try:
        # strict=False accepte les retours à la ligne bruts dans les chaînes.
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        pass
    # Virgules en trop avant } ou ] (erreur fréquente)
    return json.loads(re.sub(r",\s*([}\]])", r"\1", text), strict=False)


def _is_product(node: dict) -> bool:
    types = node.get("@type")
    types = types if isinstance(types, list) else [types]
    # Accepte "Product", "schema:Product", "https://schema.org/Product"
    return any(isinstance(t, str) and re.split(r"[/:]", t)[-1] == "Product" for t in types)


def _find_products(data: Any):
    """Parcourt tout le JSON (y compris @graph et les listes) à la recherche
    d'objets Product. On ne descend pas à l'intérieur d'un Product : ses
    "produits similaires" (isRelatedTo…) ne doivent pas être confondus avec lui."""
    if isinstance(data, dict):
        if _is_product(data):
            yield data
            return
        for value in data.values():
            yield from _find_products(value)
    elif isinstance(data, list):
        for value in data:
            yield from _find_products(value)


def _first_text(value: Any, *keys: str) -> str | None:
    """Renvoie une chaîne depuis une chaîne, une liste ou un objet ({"name": ...})."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        for v in value:
            found = _first_text(v, *keys)
            if found:
                return found
    if isinstance(value, dict):
        for key in keys:
            found = _first_text(value.get(key), *keys)
            if found:
                return found
    return None


def _extract_offer(offers: Any) -> tuple[float | None, str | None]:
    """Prix et devise depuis offers (Offer, liste d'Offer, AggregateOffer…)."""
    candidates = offers if isinstance(offers, list) else [offers]
    for offer in candidates:
        if not isinstance(offer, dict):
            continue
        price = parse_price(offer.get("price")) or parse_price(offer.get("lowPrice"))
        currency = offer.get("priceCurrency")
        spec = offer.get("priceSpecification")
        if price is None and spec:
            spec = spec[0] if isinstance(spec, list) and spec else spec
            if isinstance(spec, dict):
                price = parse_price(spec.get("price"))
                currency = currency or spec.get("priceCurrency")
        if price is None and "offers" in offer:  # AggregateOffer contenant des Offer
            price, nested_currency = _extract_offer(offer["offers"])
            currency = currency or nested_currency
        if price is not None:
            return price, normalize_currency(currency)
    return None, None


def _from_json_ld(soup: BeautifulSoup) -> PageData:
    products = []
    for script in soup.find_all("script", type=re.compile(r"application/ld\+json", re.I)):
        try:
            products.extend(_find_products(_load_json(script.get_text())))
        except (json.JSONDecodeError, ValueError):
            continue  # bloc illisible : on passe au suivant
    if not products:
        return PageData()

    # On préfère le premier Product qui a un prix.
    priced = [(p, _extract_offer(p.get("offers"))) for p in products]
    product, (price, currency) = next(
        ((p, offer) for p, offer in priced if offer[0] is not None), priced[0]
    )
    return PageData(
        name=_first_text(product.get("name")),
        brand=_first_text(product.get("brand"), "name"),
        price=price,
        currency=currency,
        image_url=_first_text(product.get("image"), "url", "contentUrl"),
    )


def _meta(soup: BeautifulSoup, key: str) -> str | None:
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    if tag and tag.get("content"):
        return tag["content"].strip() or None
    return None


def _from_meta(soup: BeautifulSoup) -> PageData:
    return PageData(
        name=_meta(soup, "og:title"),
        price=parse_price(_meta(soup, "product:price:amount") or _meta(soup, "og:price:amount")),
        currency=normalize_currency(
            _meta(soup, "product:price:currency") or _meta(soup, "og:price:currency")
        ),
        image_url=_meta(soup, "og:image"),
    )


def extract_product_data(html: str | bytes, base_url: str) -> PageData:
    """Lit une page HTML : JSON-LD d'abord, puis balises meta pour ce qui manque."""
    soup = BeautifulSoup(html, "html.parser")
    ld = _from_json_ld(soup)
    meta = _from_meta(soup)

    data = PageData(
        name=ld.name or meta.name,
        brand=ld.brand,
        image_url=ld.image_url or meta.image_url,
    )
    # Le prix et sa devise vont ensemble : on les prend à la même source.
    if ld.price is not None:
        data.price, data.currency = ld.price, ld.currency or meta.currency
    elif meta.price is not None:
        data.price, data.currency = meta.price, meta.currency

    # Images relatives ("/img/a.jpg") ou sans protocole ("//cdn…") -> URL complète
    if data.image_url:
        data.image_url = urljoin(base_url, data.image_url)
    return data


# ---------------------------------------------------------------------------
# 2. Téléchargement et vérification
# ---------------------------------------------------------------------------

def _redirected_to_homepage(original_url: str, final_url: str) -> bool:
    """Un produit retiré redirige souvent vers l'accueil (/, /fr/, /fr-fr…)."""
    home = re.compile(r"^/?([a-z]{2}([-_][a-z]{2})?/?)?$", re.I)
    return bool(home.match(urlsplit(final_url).path)) and not home.match(urlsplit(original_url).path)


async def _fetch(client: httpx.AsyncClient, url: str):
    """GET de la page. Renvoie (statut, url finale, contenu, content-type)."""
    async with client.stream("GET", url, headers=HEADERS) as response:
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400:
            return response.status_code, str(response.url), b"", content_type

        chunks, size = [], 0
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_PAGE_BYTES:
                break
        body: str | bytes = b"".join(chunks)
        # Si le serveur annonce l'encodage, on l'utilise ; sinon BeautifulSoup le devinera.
        if response.charset_encoding:
            try:
                body = body.decode(response.charset_encoding, errors="replace")
            except LookupError:
                pass
        return response.status_code, str(response.url), body, content_type


async def verify_product(client: httpx.AsyncClient, product: dict) -> dict:
    """Vérifie un produit et renvoie une COPIE enrichie (l'original n'est pas modifié)."""
    result = {**product, "link_verified": False, "price_verified": False}
    url = (product.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        logger.info("URL invalide ignorée : %r", url)
        return result

    try:
        status, final_url, body, content_type = await asyncio.wait_for(
            _fetch(client, url), timeout=TIMEOUT_SECONDS
        )
    except TimeoutError:
        logger.info("Timeout : %s", url)
        return result
    except Exception as exc:  # erreur réseau, SSL, DNS… : on n'interrompt jamais tout le lot
        logger.info("Échec de %s : %s", url, exc)
        return result

    if status >= 400:
        logger.info("Statut %s : %s", status, url)
        return result
    if _redirected_to_homepage(url, final_url):
        logger.info("Redirigé vers l'accueil (produit retiré ?) : %s", url)
        return result

    result["link_verified"] = True
    if content_type and "html" not in content_type.lower():
        return result

    page = extract_product_data(body, final_url)
    if page.price is not None:
        result["price"] = page.price
        result["price_verified"] = True
        if page.currency:
            result["currency"] = page.currency
    if page.image_url:
        result["image_url"] = page.image_url
    # Nom et marque : on garde ceux de l'IA (plus lisibles), sauf s'ils manquent.
    if not result.get("name") and page.name:
        result["name"] = page.name
    if not result.get("brand") and page.brand:
        result["brand"] = page.brand
    return result


async def verify_products(products: list[dict], client: httpx.AsyncClient | None = None) -> list[dict]:
    """Vérifie tous les produits en parallèle ; liens morts en fin de liste.

    `client` sert aux tests (on y injecte un faux réseau) ; sinon on en crée un.
    """
    if client is None:
        async with httpx.AsyncClient(follow_redirects=True, timeout=TIMEOUT_SECONDS) as own_client:
            return await verify_products(products, own_client)

    results = await asyncio.gather(*(verify_product(client, p) for p in products))
    # sorted est "stable" : l'ordre de l'IA est conservé à l'intérieur de chaque groupe.
    return sorted(results, key=lambda p: not p["link_verified"])
