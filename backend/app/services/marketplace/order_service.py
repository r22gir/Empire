from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import random
import string
from app.models.marketplace.order import MarketFOrder, OrderStatus, EscrowStatus
from app.models.marketplace.product import MarketFProduct, ProductStatus
from app.schemas.marketplace.order import OrderCreate
from app.services.marketplace.fee_service import calculate_order_totals


class OrderService:
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate a unique order number (MF-XXXXXX)"""
        random_part = ''.join(random.choices(string.digits, k=6))
        return f"MF-{random_part}"
    
    @staticmethod
    def create_order(
        db: Session,
        order_data: OrderCreate,
        buyer_id: UUID
    ) -> Optional[MarketFOrder]:
        """Create a new order"""
        # Get product
        product = db.query(MarketFProduct).filter(
            MarketFProduct.id == order_data.product_id,
            MarketFProduct.status == ProductStatus.ACTIVE
        ).first()
        
        if not product:
            return None
        
        # Calculate shipping price (use product shipping or calculate)
        shipping_price = product.shipping_price if product.shipping_price else 0.0
        
        # Calculate fees and totals
        totals = calculate_order_totals(product.price, shipping_price)
        
        # Create order
        order = MarketFOrder(
            order_number=OrderService.generate_order_number(),
            buyer_id=buyer_id,
            seller_id=product.seller_id,
            product_id=product.id,
            product_title=product.title,
            product_price=product.price,
            shipping_price=shipping_price,
            shipping_address=order_data.shipping_address,
            **totals,
            status=OrderStatus.PENDING_PAYMENT,
            escrow_status=EscrowStatus.PENDING
        )
        
        db.add(order)
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def get_order(db: Session, order_id: UUID) -> Optional[MarketFOrder]:
        """Get a single order by ID"""
        return db.query(MarketFOrder).filter(MarketFOrder.id == order_id).first()
    
    @staticmethod
    def list_buyer_orders(
        db: Session,
        buyer_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[MarketFOrder], int]:
        """List orders for a buyer"""
        query = db.query(MarketFOrder).filter(MarketFOrder.buyer_id == buyer_id)
        total = query.count()
        orders = query.order_by(MarketFOrder.created_at.desc()).offset(skip).limit(limit).all()
        return orders, total
    
    @staticmethod
    def list_seller_orders(
        db: Session,
        seller_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[MarketFOrder], int]:
        """List orders for a seller"""
        query = db.query(MarketFOrder).filter(MarketFOrder.seller_id == seller_id)
        
        if status:
            query = query.filter(MarketFOrder.status == status)
        
        total = query.count()
        orders = query.order_by(MarketFOrder.created_at.desc()).offset(skip).limit(limit).all()
        return orders, total
    
    @staticmethod
    def mark_order_paid(db: Session, order_id: UUID) -> Optional[MarketFOrder]:
        """Mark order as paid and update escrow status"""
        order = db.query(MarketFOrder).filter(MarketFOrder.id == order_id).first()
        
        if not order:
            return None
        
        order.status = OrderStatus.PAID
        order.paid_at = datetime.utcnow()
        order.escrow_status = EscrowStatus.HELD
        order.escrow_held_at = datetime.utcnow()
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def mark_order_shipped(
        db: Session,
        order_id: UUID,
        tracking_number: str,
        carrier: str,
        seller_id: UUID
    ) -> Optional[MarketFOrder]:
        """Mark order as shipped (seller only)"""
        order = db.query(MarketFOrder).filter(
            MarketFOrder.id == order_id,
            MarketFOrder.seller_id == seller_id
        ).first()
        
        if not order:
            return None
        
        order.status = OrderStatus.SHIPPED
        order.tracking_number = tracking_number
        order.carrier = carrier
        order.shipped_at = datetime.utcnow()
        
        # Mark product as sold
        product = db.query(MarketFProduct).filter(MarketFProduct.id == order.product_id).first()
        if product:
            product.status = ProductStatus.SOLD
            product.sold_at = datetime.utcnow()
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def mark_order_delivered(db: Session, order_id: UUID) -> Optional[MarketFOrder]:
        """Mark order as delivered (triggered by tracking update)"""
        order = db.query(MarketFOrder).filter(MarketFOrder.id == order_id).first()
        
        if not order:
            return None
        
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.utcnow()
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def complete_order(db: Session, order_id: UUID) -> Optional[MarketFOrder]:
        """Complete order and release escrow"""
        order = db.query(MarketFOrder).filter(MarketFOrder.id == order_id).first()
        
        if not order:
            return None
        
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        order.escrow_status = EscrowStatus.RELEASED
        order.escrow_released_at = datetime.utcnow()
        
        db.commit()
        db.refresh(order)
        return order
