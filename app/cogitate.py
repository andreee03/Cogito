"""Recherche de produits ("Cogiter") avec Claude et l'outil de recherche web.

Déroulé d'une recherche (fonction run_search, lancée en tâche de fond) :
1. on construit le message à partir du profil et de l'article ;
2. on appelle Claude Haiku 4.5 avec l'outil web_search (en gérant "pause_turn") ;
3. on extrait le bloc JSON {"products": [...]} de sa réponse ;
4. on vérifie chaque lien avec app/verify.py ;
5. on enregistre les résultats, le coût estimé et le statut.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import anthropic
from sqlmodel import Session, select

from app.db import engine, get_or_create_profile
from app.models import Item, ItemStatus, Result, Search, SearchStatus
from app.prompts import COGITATE_SYSTEM_PROMPT
from app.verify import parse_price, verify_products

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 16000

# Tarifs utilisés pour estimer le coût d'une recherche (en dollars).
INPUT_PRICE_PER_MTOK = 1.0     # 1 $ par million de tokens d'entrée
OUTPUT_PRICE_PER_MTOK = 5.0    # 5 $ par million de tokens de sortie
WEB_SEARCH_PRICE = 0.01        # 0,01 $ par recherche web

# Nombre maximum d'itérations réussies par article.
MAX_ITERATIONS = 3

# Nombre maximum de reprises après un "pause_turn" (évite une boucle infinie).
MAX_CONTINUATIONS = 5

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 20,
    "user_location": {
        "type": "approximate",
        "country": "FR",
        "timezone": "Europe/Paris",
    },
}

CATEGORY_LABELS = {
    "vetements": "vêtements",
    "outils": "outils de travail",
    "deco": "meubles / déco de chambre",
    "autre": "autre",
}


class CogitateError(Exception):
    """Erreur dont le message est montré tel quel à l'utilisateur."""


def get_client() -> anthropic.AsyncAnthropic:
    """Client Claude (la clé est lue dans ANTHROPIC_API_KEY).

    Avec FAKE_CLAUDE=1 dans le .env, on utilise un faux Claude gratuit
    (app/fake_claude.py). Les tests, eux, remplacent cette fonction par leur
    propre faux client : aucun test n'appelle la vraie API.
    """
    if os.getenv("FAKE_CLAUDE") == "1":
        from app.fake_claude import FakeAsyncClaude
        return FakeAsyncClaude()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise CogitateError("ANTHROPIC_API_KEY manquante : ajoute-la dans le fichier .env puis relance le serveur.")
    return anthropic.AsyncAnthropic()


# ---------------------------------------------------------------------------
# 1. Construction du message
# ---------------------------------------------------------------------------

REACTION_LABELS = {"like": "J'AIME", "dislike": "JE N'AIME PAS"}


def summarize_previous(searches: list[Search]) -> list[str]:
    """Résumé COMPACT des itérations précédentes : une ligne par produit
    (nom, marque, prix, réaction). Jamais les pages brutes : c'est ce qui
    garde le coût en tokens bas."""
    lines = []
    for search in searches:
        lines.append(f"### Itération {search.iteration}")
        if search.feedback:
            lines.append(f"Mon retour avant cette itération : {search.feedback.strip()}")
        for r in search.results:
            price = f"{r.price:g} {r.currency or ''}".strip() if r.price is not None else "prix inconnu"
            reaction = getattr(r.reaction, "value", r.reaction)
            label = f" — {REACTION_LABELS[reaction]}" if reaction else ""
            lines.append(f"- {r.name} ({r.brand or 'marque inconnue'}, {price}){label}")
    return lines


def build_user_prompt(
    master_prompt: str,
    item: Item,
    feedback: str | None = None,
    previous: list[Search] | None = None,
) -> str:
    """Message envoyé à Claude : mes goûts + l'article recherché
    (+ le résumé des itérations précédentes et mon retour, à partir de la 2e)."""
    category = getattr(item.category, "value", item.category)
    lines = [
        "## Mes goûts et principes d'achat",
        master_prompt.strip(),
        "",
        "## Ce que je cherche",
        f"- Article : {item.title}",
        f"- Catégorie : {CATEGORY_LABELS.get(category, category)}",
    ]
    if item.notes:
        lines.append(f"- Notes : {item.notes}")
    if item.budget_max is not None:
        lines.append(f"- Budget maximum : {item.budget_max:g} €")
    if item.custom_prompt:
        lines += ["", "## Consignes spécifiques pour cet article", item.custom_prompt.strip()]
    if previous:
        lines += [
            "",
            "## Ce que tu m'as déjà proposé",
            "Ne repropose pas ces produits. Inspire-toi de ceux que j'aime et "
            "éloigne-toi de ceux que je n'aime pas.",
            *summarize_previous(previous),
        ]
    if feedback:
        lines += ["", "## Mon retour sur la recherche précédente", feedback.strip()]
    lines += ["", "Trouve-moi entre 5 et 8 produits et termine par le bloc JSON demandé."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. Appel à Claude
# ---------------------------------------------------------------------------

def estimate_cost(usage: Any) -> float:
    """Coût estimé (en $) d'une réponse, à partir de response.usage."""
    server_tool_use = getattr(usage, "server_tool_use", None)
    searches = getattr(server_tool_use, "web_search_requests", 0) or 0
    return (
        (usage.input_tokens or 0) * INPUT_PRICE_PER_MTOK / 1_000_000
        + (usage.output_tokens or 0) * OUTPUT_PRICE_PER_MTOK / 1_000_000
        + searches * WEB_SEARCH_PRICE
    )


@dataclass
class ClaudeAnswer:
    text: str        # tout le texte écrit par Claude
    cost_usd: float  # coût cumulé de tous les appels


async def ask_claude(client: anthropic.AsyncAnthropic, user_prompt: str) -> ClaudeAnswer:
    """Appelle Claude avec la recherche web et renvoie son texte final.

    Quand la recherche web prend du temps, l'API peut s'arrêter en cours de route
    avec stop_reason == "pause_turn". On renvoie alors sa réponse telle quelle
    (comme message "assistant") et on rappelle l'API, qui reprend où elle en était.
    """
    messages: list[dict] = [{"role": "user", "content": user_prompt}]
    texts: list[str] = []
    cost = 0.0

    for _ in range(MAX_CONTINUATIONS + 1):
        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=COGITATE_SYSTEM_PROMPT,
            tools=[WEB_SEARCH_TOOL],
            messages=messages,
        )
        cost += estimate_cost(response.usage)
        texts += [block.text for block in response.content if block.type == "text"]

        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": response.content})
            continue
        if response.stop_reason == "refusal":
            raise CogitateError("Claude a refusé de traiter cette demande.")
        return ClaudeAnswer(text="\n".join(texts), cost_usd=cost)

    raise CogitateError(
        f"La recherche ne s'est pas terminée après {MAX_CONTINUATIONS} reprises (pause_turn)."
    )


# ---------------------------------------------------------------------------
# 3. Lecture du JSON renvoyé par Claude
# ---------------------------------------------------------------------------

def parse_products(text: str) -> list[dict]:
    """Extrait la liste "products" du DERNIER bloc JSON valide du texte.

    Robuste au texte autour, aux balises ```json et aux autres accolades :
    on essaie de décoder un objet JSON à partir de chaque "{", en partant de la fin.
    """
    decoder = json.JSONDecoder()
    position = len(text)
    while (position := text.rfind("{", 0, position)) != -1:
        try:
            data, _ = decoder.raw_decode(text, position)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("products"), list):
            products = [p for p in (clean_product(raw) for raw in data["products"]) if p]
            if not products:
                raise CogitateError("Claude n'a renvoyé aucun produit exploitable (nom et URL requis).")
            return products
    raise CogitateError(
        'Réponse de Claude illisible : aucun bloc JSON {"products": [...]} trouvé.'
    )


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def clean_product(raw: Any) -> dict | None:
    """Normalise un produit de l'IA (types, valeurs par défaut).

    Renvoie None si le produit n'a pas de nom ou d'URL : on ne peut rien en faire.
    """
    if not isinstance(raw, dict):
        return None
    name, url = _text_or_none(raw.get("name")), _text_or_none(raw.get("url"))
    if not name or not url:
        return None
    try:
        score = int(round(float(raw.get("score"))))
    except (TypeError, ValueError):
        score = 50
    currency = _text_or_none(raw.get("currency"))
    return {
        "name": name,
        "brand": _text_or_none(raw.get("brand")),
        "price": parse_price(raw.get("price")),
        "currency": currency.upper() if currency else None,
        "url": url,
        "image_url": _text_or_none(raw.get("image_url")),
        "description": _text_or_none(raw.get("description")),
        "why_it_fits": _text_or_none(raw.get("why_it_fits")) or "",
        "score": min(100, max(0, score)),
    }


# ---------------------------------------------------------------------------
# 4. La tâche de fond complète
# ---------------------------------------------------------------------------

RESULT_FIELDS = (
    "name", "brand", "price", "currency", "url", "image_url",
    "description", "why_it_fits", "score", "link_verified", "price_verified",
)


async def run_search(search_id: int) -> None:
    """Exécute une recherche de bout en bout et enregistre le résultat en base."""
    with Session(engine) as session:
        search = session.get(Search, search_id)
        if search is None:
            return
        search.status = SearchStatus.running
        session.add(search)
        session.commit()
        previous = [
            s for s in search.item.searches
            if s.status == SearchStatus.done and s.id != search_id
        ]
        user_prompt = build_user_prompt(
            get_or_create_profile(session).master_prompt, search.item, search.feedback, previous
        )

    cost: float | None = None
    products: list[dict] = []
    error: str | None = None
    try:
        answer = await ask_claude(get_client(), user_prompt)
        cost = answer.cost_usd
        products = await verify_products(parse_products(answer.text))
    except CogitateError as exc:
        error = str(exc)
    except anthropic.AuthenticationError:
        error = "Clé API Anthropic refusée : vérifie ANTHROPIC_API_KEY dans le fichier .env."
    except anthropic.APIError as exc:
        logger.exception("Erreur de l'API Claude (recherche %s)", search_id)
        error = f"Erreur de l'API Claude : {exc.message}"
    except Exception as exc:  # on ne laisse jamais une recherche bloquée en "running"
        logger.exception("Erreur inattendue (recherche %s)", search_id)
        error = f"Erreur inattendue : {exc}"

    with Session(engine) as session:
        search = session.get(Search, search_id)
        if search is None:  # article supprimé pendant la recherche
            return
        search.cost_usd = round(cost, 6) if cost is not None else None
        if error:
            search.status, search.error = SearchStatus.error, error
        else:
            search.status = SearchStatus.done
            for product in products:
                session.add(Result(search_id=search_id, **{k: product[k] for k in RESULT_FIELDS}))

        # L'article repasse en "resultats" s'il a au moins une recherche réussie.
        item = search.item
        has_results = any(s.status == SearchStatus.done for s in item.searches)
        item.status = ItemStatus.resultats if has_results else ItemStatus.a_chercher
        session.add_all([search, item])
        session.commit()


def fail_interrupted_searches() -> None:
    """Au démarrage : une recherche restée "pending"/"running" a été interrompue
    (serveur arrêté pendant la recherche). On la marque en erreur."""
    with Session(engine) as session:
        searches = session.exec(
            select(Search).where(Search.status.in_([SearchStatus.pending, SearchStatus.running]))
        ).all()
        for search in searches:
            search.status = SearchStatus.error
            search.error = "Recherche interrompue (le serveur a redémarré)."
            item = search.item
            if item.status == ItemStatus.en_recherche:
                done = any(s.status == SearchStatus.done for s in item.searches)
                item.status = ItemStatus.resultats if done else ItemStatus.a_chercher
            session.add_all([search, item])
        session.commit()
