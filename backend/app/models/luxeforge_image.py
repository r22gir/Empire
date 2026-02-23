"""
LuxeForge Image database model.
"""
from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from app.database import Base


class LuxeForgeImage(Base):
    """Model for images captured or uploaded via the LuxeForge product page."""

    __tablename__ = "luxeforge_images"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    original_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<LuxeForgeImage {self.filename}>"
