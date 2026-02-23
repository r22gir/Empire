"""
Workroom Forge API Router.
Provides CRUD endpoints for orders, clients, and dashboard stats.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.workroom import WorkroomOrder, WorkroomClient
from app.schemas.workroom import (
    OrderCreate, OrderUpdate, OrderResponse,
    ClientCreate, ClientUpdate, ClientResponse,
    WorkroomStats,
)

router = APIRouter(prefix="/api/workroom", tags=["workroom"])


# ---------- Orders ----------

@router.get("/orders", response_model=List[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    """List all workroom orders."""
    return db.query(WorkroomOrder).order_by(WorkroomOrder.created_at.desc()).all()


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """Create a new workroom order."""
    order = WorkroomOrder(**order_data.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    # Update client totals if client_id provided
    if order.client_id:
        client = db.query(WorkroomClient).filter(WorkroomClient.id == order.client_id).first()
        if client:
            client.total_orders += 1
            client.total_spent += order.total
            db.commit()
    return order


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a single workroom order by ID."""
    order = db.query(WorkroomOrder).filter(WorkroomOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, order_data: OrderUpdate, db: Session = Depends(get_db)):
    """Update an existing workroom order."""
    order = db.query(WorkroomOrder).filter(WorkroomOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    update_fields = order_data.model_dump(exclude_unset=True)

    # Adjust client totals when total or client_id changes
    old_client_id = order.client_id
    old_total = order.total
    new_client_id = update_fields.get("client_id", old_client_id)
    new_total = update_fields.get("total", old_total)

    if old_client_id != new_client_id or new_total != old_total:
        if old_client_id:
            old_client = db.query(WorkroomClient).filter(WorkroomClient.id == old_client_id).first()
            if old_client:
                old_client.total_orders = max(0, old_client.total_orders - 1)
                old_client.total_spent = max(0.0, old_client.total_spent - old_total)
        if new_client_id:
            new_client = db.query(WorkroomClient).filter(WorkroomClient.id == new_client_id).first()
            if new_client:
                new_client.total_orders += 1
                new_client.total_spent += new_total

    for field, value in update_fields.items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    """Delete a workroom order."""
    order = db.query(WorkroomOrder).filter(WorkroomOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    # Decrement client totals when order is deleted
    if order.client_id:
        client = db.query(WorkroomClient).filter(WorkroomClient.id == order.client_id).first()
        if client:
            client.total_orders = max(0, client.total_orders - 1)
            client.total_spent = max(0.0, client.total_spent - order.total)
    db.delete(order)
    db.commit()


# ---------- Clients ----------

@router.get("/clients", response_model=List[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    """List all workroom clients."""
    return db.query(WorkroomClient).order_by(WorkroomClient.created_at.desc()).all()


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(client_data: ClientCreate, db: Session = Depends(get_db)):
    """Create a new workroom client."""
    client = WorkroomClient(**client_data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/clients/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    """Get a single workroom client by ID."""
    client = db.query(WorkroomClient).filter(WorkroomClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.put("/clients/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, client_data: ClientUpdate, db: Session = Depends(get_db)):
    """Update an existing workroom client."""
    client = db.query(WorkroomClient).filter(WorkroomClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    update_fields = client_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    """Delete a workroom client."""
    client = db.query(WorkroomClient).filter(WorkroomClient.id == client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    db.delete(client)
    db.commit()


# ---------- Stats ----------

@router.get("/stats", response_model=WorkroomStats)
def get_stats(db: Session = Depends(get_db)):
    """Return dashboard statistics for Workroom Forge."""
    orders = db.query(WorkroomOrder).all()
    total_orders = len(orders)
    pending_orders = sum(1 for o in orders if o.status == "pending")
    in_progress_orders = sum(1 for o in orders if o.status == "in_progress")
    completed_orders = sum(1 for o in orders if o.status == "completed")
    total_revenue = sum(o.total for o in orders if o.status == "completed")
    total_clients = db.query(WorkroomClient).count()

    return WorkroomStats(
        total_orders=total_orders,
        pending_orders=pending_orders,
        in_progress_orders=in_progress_orders,
        completed_orders=completed_orders,
        total_revenue=total_revenue,
        total_clients=total_clients,
    )
