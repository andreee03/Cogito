"""Import des envies depuis Notion.

Source : la base « Tasks [PT] » du PARA Dashboard, telle qu'affichée dans la
section « Task Inbox » (tâches non terminées et sans projet). On ne prend que
les entrées dont la propriété « Category » est vide : ce sont les envies
d'achat pas encore classées. Seul le titre est repris ; il devient le titre de
l'article (catégorie « autre », statut « à chercher »).

Configuration (.env) :
  NOTION_TOKEN        clé d'une intégration Notion (https://www.notion.so/my-integrations),
                      à connecter à la base « Tasks [PT] » (••• → Connexions)
  NOTION_DATABASE_ID  identifiant de la base (valeur par défaut : Tasks [PT])
"""

import os

import httpx

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_DATABASE_ID = "d072b32f4429826283d681573e8014db"
TIMEOUT_SECONDS = 20
TITLE_MAX_LENGTH = 200  # même limite que Item.title

# Filtre de la vue « Task Inbox » + catégorie non renseignée.
INBOX_FILTER = {
    "and": [
        {"property": "Category", "select": {"is_empty": True}},
        {"property": "Project", "relation": {"is_empty": True}},
        {"property": "Done", "status": {"does_not_equal": "Done"}},
    ]
}


class NotionImportError(Exception):
    """Erreur à afficher telle quelle à l'utilisateur, avec le code HTTP à renvoyer."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def get_http_client() -> httpx.Client:
    """Client HTTP vers Notion (remplacé par un faux client dans les tests)."""
    return httpx.Client(timeout=TIMEOUT_SECONDS)


def page_title(page: dict) -> str:
    """Le texte de la propriété de type « title » d'une page Notion."""
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            parts = prop.get("title") or []
            return "".join(p.get("plain_text", "") for p in parts).strip()
    return ""


def _error_message(response: httpx.Response) -> str:
    if response.status_code == 401:
        return "Notion a refusé la clé : vérifie NOTION_TOKEN dans le .env du back-end."
    if response.status_code == 404:
        return (
            "Base Notion introuvable : connecte ton intégration à la base « Tasks [PT] » "
            "(••• → Connexions) et vérifie NOTION_DATABASE_ID."
        )
    try:
        detail = response.json().get("message")
    except ValueError:
        detail = None
    return f"Erreur Notion ({response.status_code}){f' : {detail}' if detail else ''}."


def fetch_inbox_titles() -> list[str]:
    """Titres des entrées « Task Inbox » sans catégorie, dans l'ordre de Notion."""
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        raise NotionImportError(
            "Import Notion non configuré : ajoute NOTION_TOKEN dans le .env du back-end.",
            status_code=503,
        )
    database_id = os.getenv("NOTION_DATABASE_ID", "").strip() or DEFAULT_DATABASE_ID
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    titles: list[str] = []
    body: dict = {"filter": INBOX_FILTER, "page_size": 100}
    with get_http_client() as client:
        while True:  # Notion renvoie les résultats par pages de 100 au plus
            try:
                response = client.post(
                    f"{NOTION_API}/databases/{database_id}/query", headers=headers, json=body
                )
            except httpx.HTTPError as exc:
                raise NotionImportError(f"Impossible de joindre Notion ({exc.__class__.__name__}).")
            if response.status_code != 200:
                raise NotionImportError(_error_message(response))
            data = response.json()
            for page in data.get("results", []):
                title = page_title(page)
                if title:
                    titles.append(title[:TITLE_MAX_LENGTH])
            if not data.get("has_more") or not data.get("next_cursor"):
                return titles
            body["start_cursor"] = data["next_cursor"]
