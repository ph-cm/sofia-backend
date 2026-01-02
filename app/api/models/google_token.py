from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.base_class import Base

class GoogleToken(Base):
    __tablename__ = "google_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    google_access_token = Column(String, nullable=False)
    google_refresh_token = Column(String, nullable=False)
    google_token_expiry = Column(DateTime(timezone=True), nullable=True)
    scope = Column(String, nullable=True)

