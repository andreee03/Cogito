"""Routes de l'API."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlmodel import Session, select

from app.db import get_or_create_profile, get_session, init_db
from app.models import Item, ItemCreate, ItemRead, ItemUpdate, ProfileData


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # au démarrage : création des tables + profil par défaut
    yield


app = FastAPI(title="Shopping réfléchi", lifespan=lifespan)

# Raccourci : "session: SessionDep" donne une session de base à chaque route.
SessionDep = Annotated[Session, Depends(get_session)]


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def get_item_or_404(session: Session, item_id: int) -> Item:
    item = session.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Article introuvable")
    return item


def to_item_read(item: Item) -> ItemRead:
    # iterations_count n'est pas une colonne : on le calcule à partir des recherches.
    return ItemRead.model_validate(item, update={"iterations_count": len(item.searches)})


# ---------------------------------------------------------------------------
# Santé
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------

@app.get("/profile", response_model=ProfileData)
def read_profile(session: SessionDep):
    return get_or_create_profile(session)


@app.put("/profile", response_model=ProfileData)
def update_profile(data: ProfileData, session: SessionDep):
    profile = get_or_create_profile(session)
    profile.master_prompt = data.master_prompt
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------

@app.get("/items", response_model=list[ItemRead])
def list_items(session: SessionDep):
    items = session.exec(select(Item).order_by(Item.created_at.desc(), Item.id.desc())).all()
    return [to_item_read(item) for item in items]


@app.post("/items", response_model=ItemRead)
def create_item(data: ItemCreate, session: SessionDep):
    item = Item.model_validate(data)
    session.add(item)
    session.commit()
    session.refresh(item)
    return to_item_read(item)


@app.get("/items/{item_id}", response_model=ItemRead)
def read_item(item_id: int, session: SessionDep):
    return to_item_read(get_item_or_404(session, item_id))


@app.patch("/items/{item_id}", response_model=ItemRead)
def update_item(item_id: int, data: ItemUpdate, session: SessionDep):
    item = get_item_or_404(session, item_id)
    # exclude_unset : on ne modifie que les champs réellement envoyés.
    item.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(item)
    session.commit()
    session.refresh(item)
    return to_item_read(item)


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, session: SessionDep):
    item = get_item_or_404(session, item_id)
    session.delete(item)  # supprime aussi recherches et résultats (cascade)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
