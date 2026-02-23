"""
LuxeForge ImageMeasurement database model.
"""
from sqlalchemy import Column, String, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
from app.database import Base


class ImageMeasurement(Base):
    """Stores calibration and measurement data for a LuxeForge image."""

    __tablename__ = "luxeforge_image_measurements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Reference line calibration
    reference_pixels = Column(Float, nullable=False)       # pixel length of reference line
    reference_real = Column(Float, nullable=False)         # real-world length of reference
    reference_unit = Column(String(10), nullable=False, default="inches")  # 'inches' or 'cm'

    # Array of {label, start, end, pixels, real_length}
    measurements = Column(JSON, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<ImageMeasurement image_id={self.image_id}>"
