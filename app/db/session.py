import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

import re
from app.core.config import settings


logger = logging.getLogger("db")

safe_url = re.sub(r":([^:@/]+)@", ":***@", settings.DATABASE_URL)
logger.warning("USING DATABASE_URL = %s", safe_url)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
