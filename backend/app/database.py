from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

# Railway liefert Postgres-URLs teils als "postgres://" -> SQLAlchemy braucht "postgresql://"
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

# SQLite hat keinen Connection-Pool (StaticPool intern), daher nur für Postgres konfigurieren.
if db_url.startswith("sqlite"):
    engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
else:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=5,        # Max. dauerhafte Connections im Pool
        max_overflow=10,    # Zusätzliche Connections unter Last (gesamt: 15)
        pool_timeout=30,    # Sekunden warten bevor Fehler bei voller Pool
        pool_recycle=300,   # Connections nach 5 Min recyceln (verhindert stale RAM)
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
