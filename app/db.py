"""Connexion à la base de données.

L'URL vient de la variable d'environnement DATABASE_URL (fichier .env).
Par défaut : un fichier SQLite local, shopping.db.
"""

import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select

from app.prompts import DEFAULT_MASTER_PROMPT

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shopping.db")

# SQLite refuse par défaut qu'un même fichier soit utilisé depuis plusieurs
# threads ; FastAPI en utilise plusieurs, donc on lève cette restriction.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    """Crée les tables manquantes et le profil par défaut."""
    from app.models import Profile  # import local : évite un import circulaire

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        get_or_create_profile(session)


def get_or_create_profile(session: Session):
    """Il n'y a qu'un seul profil (id = 1). On le crée s'il n'existe pas."""
    from app.models import Profile

    profile = session.exec(select(Profile)).first()
    if profile is None:
        profile = Profile(id=1, master_prompt=DEFAULT_MASTER_PROMPT)
        session.add(profile)
        session.commit()
        session.refresh(profile)
    return profile


def get_session():
    """Dépendance FastAPI : ouvre une session par requête, puis la ferme."""
    with Session(engine) as session:
        yield session
