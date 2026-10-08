"""Connexion à la base de données.

L'URL vient de la variable d'environnement DATABASE_URL (fichier .env).
Par défaut : un fichier SQLite local, shopping.db.
"""

import os

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine, select

from app.prompts import DEFAULT_MASTER_PROMPT

load_dotenv()



def normalize_database_url(url: str) -> str:
    """Neon (et Render) donnent des URL "postgresql://…" ou "postgres://…".
    SQLAlchemy les associe au vieux pilote psycopg2 ; on utilise psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./shopping.db"))

if DATABASE_URL.startswith("sqlite"):
    # SQLite refuse par défaut qu'un même fichier soit utilisé depuis plusieurs
    # threads ; FastAPI en utilise plusieurs, donc on lève cette restriction.
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping : Neon coupe les connexions inactives (base mise en veille) ;
    # on vérifie donc chaque connexion avant de la réutiliser.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)


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
