"""Routes de l'API."""

import os
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from app import cogitate
from app.db import get_or_create_profile, get_session, init_db
from app.models import (
    CogitateRequest,
    CogitateResponse,
    Item,
    ItemCreate,
    ItemRead,
    ItemStatus,
    ItemUpdate,
    ProfileData,
    Result,
    ResultReactionUpdate,
    ResultRead,
    Search,
    SearchRead,
    SearchStatus,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # au démarrage : création des tables + profil par défaut
    cogitate.fail_interrupted_searches()
    yield


app = FastAPI(title="Shopping réfléchi", lifespan=lifespan)


def allowed_origins() -> list[str]:
    """ALLOWED_ORIGINS du .env : adresses du front-end, séparées par des virgules
    (ex. "http://localhost:5173,https://mon-front.onrender.com")."""
    raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


# CORS : autorise le navigateur à appeler l'API depuis le front-end, qui est
# servi depuis une autre adresse (autre port en local, autre domaine en ligne).
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def done_searches(item: Item) -> list[Search]:
    """Les itérations réussies. Une recherche en erreur ne compte pas :
    on peut la relancer sans perdre une de ses 3 itérations."""
    return [s for s in item.searches if s.status == SearchStatus.done]


def to_item_read(item: Item) -> ItemRead:
    # iterations_count n'est pas une colonne : on le calcule à partir des recherches.
    return ItemRead.model_validate(item, update={"iterations_count": len(done_searches(item))})


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


# ---------------------------------------------------------------------------
# Recherches ("Cogiter")
# ---------------------------------------------------------------------------

@app.post(
    "/items/{item_id}/cogitate",
    response_model=CogitateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def cogitate_item(
    item_id: int, data: CogitateRequest, background_tasks: BackgroundTasks, session: SessionDep
):
    item = get_item_or_404(session, item_id)
    if any(s.status in (SearchStatus.pending, SearchStatus.running) for s in item.searches):
        raise HTTPException(status_code=409, detail="Une recherche est déjà en cours pour cet article")
    done = len(done_searches(item))
    if done >= cogitate.MAX_ITERATIONS:
        raise HTTPException(
            status_code=409,
            detail=f"Limite de {cogitate.MAX_ITERATIONS} itérations atteinte pour cet article",
        )

    search = Search(item_id=item.id, iteration=done + 1, feedback=data.feedback)
    item.status = ItemStatus.en_recherche
    session.add_all([search, item])
    session.commit()
    session.refresh(search)

    # La recherche (30 s à 2 min) tourne après l'envoi de la réponse 202.
    background_tasks.add_task(cogitate.run_search, search.id)
    return CogitateResponse(search_id=search.id)


@app.get("/items/{item_id}/searches", response_model=list[SearchRead])
def list_searches(item_id: int, session: SessionDep):
    return get_item_or_404(session, item_id).searches  # ordre chronologique (par id)


@app.get("/searches/{search_id}", response_model=SearchRead)
def read_search(search_id: int, session: SessionDep):
    search = session.get(Search, search_id)
    if search is None:
        raise HTTPException(status_code=404, detail="Recherche introuvable")
    return search


# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------

@app.patch("/results/{result_id}", response_model=ResultRead)
def update_result(result_id: int, data: ResultReactionUpdate, session: SessionDep):
    result = session.get(Result, result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Résultat introuvable")
    result.reaction = data.reaction
    session.add(result)
    session.commit()
    session.refresh(result)
    return result
