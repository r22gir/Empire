"""
LuxeForge ImageMeasurement database model.
"""
from sqlalchemy import Column, String, Float, DateTime, Text, func
import uuid
import json
from app.database import Base


class ImageMeasurement(Base):
    """Stores calibration and measurement data for a LuxeForge image."""

    __tablename__ = "luxeforge_image_measurements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id = Column(String(36), nullable=False, index=True)

    # Reference line calibration
    reference_pixels = Column(Float, nullable=False)       # pixel length of reference line
    reference_real = Column(Float, nullable=False)         # real-world length of reference
    reference_unit = Column(String(10), nullable=False, default="inches")  # 'inches' or 'cm'

    # Array of {label, start, end, pixels, real_length} stored as JSON text
    _measurements = Column("measurements", Text, default="[]")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    @property
    def measurements(self):
        if self._measurements:
            return json.loads(self._measurements) if isinstance(self._measurements, str) else self._measurements
        return []

    @measurements.setter
    def measurements(self, value):
        self._measurements = json.dumps(value) if isinstance(value, (list, dict)) else value

    def __repr__(self):
        return f"<ImageMeasurement image_id={self.image_id}>"
