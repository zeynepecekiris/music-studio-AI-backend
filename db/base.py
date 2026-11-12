from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import re

from config.settings import settings

def _fix_db_url(url: str) -> str:
    # Heroku returns postgres://. Pin the psycopg2 driver explicitly:
    # SQLAlchemy 2.1+ defaults postgresql:// to psycopg (v3), which isn't installed.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url

DATABASE_URL = _fix_db_url(settings.DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
