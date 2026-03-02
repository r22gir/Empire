from sqlalchemy import Column, String, Integer, Float, DateTime, Text
from app.database import Base
from datetime import datetime
import uuid


class InboxMessage(Base):
    __tablename__ = "inbox_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_message_id = Column(Integer, nullable=True, index=True)

    # Content
    text = Column(Text, nullable=False)
    source = Column(String, default="telegram")  # telegram, web, api

    # AI classification
    intent = Column(String, default="note")      # task, question, instruction, note
    desk_target = Column(String, nullable=True)   # which desk this routes to
    priority = Column(Integer, default=5)          # 1-10
    ai_summary = Column(Text, nullable=True)       # AI's one-line summary
    ai_response = Column(Text, nullable=True)      # AI's immediate response (for questions)

    # Status tracking
    status = Column(String, default="received")    # received, processing, done, reviewed
    result = Column(Text, nullable=True)           # outcome description

    # Task linkage (if intent=task, this is the created task ID)
    linked_task_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
