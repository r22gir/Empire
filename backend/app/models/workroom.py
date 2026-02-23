"""
Workroom Forge database models.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Text, func
from app.database import Base


class WorkroomClient(Base):
    """Client model for Workroom Forge."""

    __tablename__ = "workroom_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<WorkroomClient {self.name}>"


class WorkroomOrder(Base):
    """Order model for Workroom Forge."""

    __tablename__ = "workroom_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, nullable=True)
    product = Column(String(500), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    due_date = Column(Date, nullable=True)
    total = Column(Float, nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    images = Column(Text, nullable=True)  # JSON-encoded list of image URLs
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<WorkroomOrder {self.id} - {self.product}>"
