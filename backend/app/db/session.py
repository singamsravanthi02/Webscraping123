from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

import logging

logger = logging.getLogger(__name__)

def get_engine():
    try:
        # Try to connect to Postgres
        engine = create_engine(
            settings.DATABASE_URL,
            pool_size=20,
            max_overflow=40,
            pool_timeout=60,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False
        )
        # Test connection
        connection = engine.connect()
        connection.close()
        return engine
    except Exception as e:
        logger.warning(f"Failed to connect to primary database: {e}. Falling back to SQLite.")
        sqlite_url = "sqlite:///./local_fallback.db"
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
            echo=False
        )

engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
