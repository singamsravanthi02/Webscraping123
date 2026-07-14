from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base



class AITokenUsageLog(Base):
    __tablename__ = "ai_token_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    model_name = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    feature = Column(String, nullable=False) # e.g. "interview", "rag_chat"
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
