"""Tables de la base (table=True) et schémas d'entrée/sortie de l'API.

Convention :
- les classes avec table=True sont stockées en base ;
- les classes ...Create / ...Update / ...Read décrivent le JSON reçu ou renvoyé.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import AfterValidator, field_validator
from sqlmodel import AutoString, Field, Relationship, SQLModel


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    # SQLite oublie le fuseau horaire : on le rétablit (on stocke toujours en UTC)
    # pour que l'API renvoie par ex. "2026-10-01T17:36:00Z".
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]


# ---------------------------------------------------------------------------
# Valeurs autorisées
# ---------------------------------------------------------------------------

class Category(str, Enum):
    vetements = "vetements"
    outils = "outils"
    deco = "deco"
    autre = "autre"


class ItemStatus(str, Enum):
    a_chercher = "a_chercher"
    en_recherche = "en_recherche"
    resultats = "resultats"
    achete = "achete"


class SearchStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class Reaction(str, Enum):
    like = "like"
    dislike = "dislike"


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------

class ProfileData(SQLModel):
    """Schéma JSON du profil, en entrée (PUT) comme en sortie."""
    master_prompt: str = Field(min_length=1)


class Profile(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    master_prompt: str


# ---------------------------------------------------------------------------
# Articles (items)
# ---------------------------------------------------------------------------

class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    # sa_type=AutoString : stocké comme simple texte (plus souple qu'un ENUM Postgres)
    category: Category = Field(sa_type=AutoString)
    notes: str | None = None
    custom_prompt: str | None = None
    budget_max: float | None = Field(default=None, ge=0)


class Item(ItemBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    status: ItemStatus = Field(default=ItemStatus.a_chercher, sa_type=AutoString)
    created_at: datetime = Field(default_factory=utcnow)

    # Supprimer un article supprime aussi ses recherches (et leurs résultats).
    searches: list["Search"] = Relationship(
        back_populates="item",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Search.id"},
    )


class ItemCreate(ItemBase):
    """Corps de POST /items."""


class ItemUpdate(SQLModel):
    """Corps de PATCH /items/{id} : tous les champs sont facultatifs."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: Category | None = None
    notes: str | None = None
    custom_prompt: str | None = None
    budget_max: float | None = Field(default=None, ge=0)
    status: ItemStatus | None = None

    @field_validator("title", "category", "status")
    @classmethod
    def _not_null(cls, value):
        # On peut omettre ces champs, mais pas les mettre explicitement à null.
        if value is None:
            raise ValueError("ce champ ne peut pas être null")
        return value


class ItemRead(ItemBase):
    """Réponse JSON pour un article."""
    id: int
    status: ItemStatus
    created_at: UTCDatetime
    iterations_count: int


# ---------------------------------------------------------------------------
# Recherches et résultats (tables créées dès maintenant, utilisées au jalon 3)
# ---------------------------------------------------------------------------

class Search(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="item.id", ondelete="CASCADE", index=True)
    iteration: int
    feedback: str | None = None
    status: SearchStatus = Field(default=SearchStatus.pending, sa_type=AutoString)
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    cost_usd: float | None = None

    item: Item = Relationship(back_populates="searches")
    results: list["Result"] = Relationship(
        back_populates="search",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "Result.id"},
    )


class Result(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    search_id: int = Field(foreign_key="search.id", ondelete="CASCADE", index=True)
    name: str
    brand: str | None = None
    price: float | None = None
    currency: str | None = None
    url: str
    image_url: str | None = None
    description: str | None = None
    why_it_fits: str
    score: int = Field(ge=0, le=100)
    link_verified: bool = False
    price_verified: bool = False
    reaction: Reaction | None = Field(default=None, sa_type=AutoString)

    search: Search = Relationship(back_populates="results")
