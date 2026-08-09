import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_db_path = Path(os.getenv("MONITORING_DB_PATH", "./monitoring.db")).expanduser()
if not _db_path.is_absolute():
    _db_path = Path.cwd() / _db_path
_db_path.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{_db_path.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
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
