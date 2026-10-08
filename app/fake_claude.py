"""Faux Claude pour développer sans payer (FAKE_CLAUDE=1 dans le .env).

Il imite anthropic.AsyncAnthropic : client.messages.create(...) renvoie, après
une courte attente, une réponse au même format que la vraie API, avec des
produits inventés. Coût : 0 $. Les liens (domaines .example) n'existent pas :
ils ressortent donc en link_verified = false, ce qui permet aussi de voir
comment l'application affiche des liens morts.
"""

import asyncio
import json
import re
import unicodedata
from types import SimpleNamespace

DELAY_SECONDS = 3  # pour voir passer le statut "running" côté front

PRODUCTS = [
    {"name": "Lampe Orbe en laiton", "brand": "Maison Halde", "price": 189.0},
    {"name": "Applique Arc", "brand": "Atelier Vérone", "price": 240.0},
    {"name": "Lampe Galet en céramique", "brand": "Terres Hautes", "price": 135.0},
    {"name": "Liseuse Fil", "brand": "Studio Nord", "price": 98.0},
    {"name": "Lampe Totem en noyer", "brand": "Bois Debout", "price": 310.0},
    {"name": "Suspension Voile", "brand": "Lin & Lumière", "price": 165.0},
    {"name": "Lampe Pivot", "brand": "Atelier Mécanique", "price": 275.0},
]


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _answer(iteration: int) -> str:
    # Chaque itération propose une sélection décalée, pour voir la différence.
    start = (iteration - 1) * 2
    picked = (PRODUCTS * 2)[start:start + 5]
    products = [
        {
            **p,
            "currency": "EUR",
            "url": f"https://www.{_slug(p['brand'])}.example/{_slug(p['name'])}",
            "image_url": None,
            "description": f"{p['name']} (produit fictif, mode FAKE_CLAUDE).",
            "why_it_fits": f"Exemple d'explication pour l'itération {iteration}.",
            "score": 90 - i * 5,
        }
        for i, p in enumerate(picked)
    ]
    return (
        "Mode FAKE_CLAUDE : aucune recherche réelle n'a été faite.\n\n"
        f"```json\n{json.dumps({'products': products}, ensure_ascii=False, indent=2)}\n```"
    )


class FakeAsyncClaude:
    def __init__(self):
        self.messages = self  # client.messages.create(...)

    async def create(self, messages, **kwargs):
        await asyncio.sleep(DELAY_SECONDS)
        prompt = messages[0]["content"]
        iteration = prompt.count("### Itération ") + 1  # itérations déjà résumées + 1
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=_answer(iteration))],
            stop_reason="end_turn",
            usage=SimpleNamespace(input_tokens=0, output_tokens=0, server_tool_use=None),
        )
