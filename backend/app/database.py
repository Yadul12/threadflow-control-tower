import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = BASE_DIR / "threadflow.db"


def resolve_database_url() -> str:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        return configured
    if os.getenv("VERCEL") or not os.access(BASE_DIR, os.W_OK):
        sqlite_path = Path("/tmp/threadflow.db")
    else:
        sqlite_path = DEFAULT_SQLITE_PATH
    return f"sqlite:///{sqlite_path.as_posix()}"


DATABASE_URL = resolve_database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
    pool_pre_ping=True,
)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
