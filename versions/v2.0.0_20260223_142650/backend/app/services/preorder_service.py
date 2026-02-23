from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.preorder import PreOrder
from app.schemas.preorder import PreOrderCreate, PreOrderUpdate
from app.services.license_service import LicenseService
from app.schemas.license import LicenseCreate

# Bundle pricing
BUNDLE_PRICES = {
    "seeker_pro": {
        "price": 599.0,
        "plan": "pro",
        "duration_months": 12
    },
    "budget_mobile": {
        "price": 349.0,
        "plan": "lite",
        "duration_months": 12
    },
    "full_empire": {
        "price": 899.0,
        "plan": "empire",
        "duration_months": 12
    }
}

class PreOrderService:
    @staticmethod
    def create_preorder(
        db: Session,
        preorder_data: PreOrderCreate
    ) -> PreOrder:
        """
        Create a new pre-order
        """
        bundle_info = BUNDLE_PRICES.get(preorder_data.bundle_type)
        
        if not bundle_info:
            raise ValueError(f"Invalid bundle type: {preorder_data.bundle_type}")
        
        unit_price = bundle_info["price"]
        total_price = unit_price * preorder_data.quantity
        
        preorder = PreOrder(
            customer_email=preorder_data.customer_email,
            customer_name=preorder_data.customer_name,
            customer_phone=preorder_data.customer_phone,
            shipping_street1=preorder_data.shipping_street1,
            shipping_street2=preorder_data.shipping_street2,
            shipping_city=preorder_data.shipping_city,
            shipping_state=preorder_data.shipping_state,
            shipping_zip=preorder_data.shipping_zip,
            shipping_country=preorder_data.shipping_country,
            bundle_type=preorder_data.bundle_type,
            quantity=preorder_data.quantity,
            unit_price=unit_price,
            total_price=total_price,
            payment_status="pending",
            fulfillment_status="pending"
        )
        
        db.add(preorder)
        db.commit()
        db.refresh(preorder)
        
        return preorder
    
    @staticmethod
    def process_payment(
        db: Session,
        preorder_id: str,
        stripe_payment_intent_id: str
    ) -> PreOrder:
        """
        Mark pre-order as paid and generate license keys
        """
        preorder = db.query(PreOrder).filter(PreOrder.id == preorder_id).first()
        
        if not preorder:
            raise ValueError("Pre-order not found")
        
        # Update payment status
        preorder.stripe_payment_intent_id = stripe_payment_intent_id
        preorder.payment_status = "paid"
        preorder.paid_at = datetime.utcnow()
        
        # Generate license keys
        bundle_info = BUNDLE_PRICES.get(preorder.bundle_type)
        
        license_data = LicenseCreate(
            plan=bundle_info["plan"],
            duration_months=bundle_info["duration_months"],
            hardware_bundle=preorder.bundle_type,
            quantity=preorder.quantity
        )
        
        licenses = LicenseService.create_licenses(db, license_data)
        
        # Store the first license key with the pre-order
        if licenses:
            preorder.license_key = licenses[0].key
            # Link all licenses to this preorder
            for license in licenses:
                license.preorder_id = preorder.id
        
        db.commit()
        db.refresh(preorder)
        
        return preorder
    
    @staticmethod
    def update_preorder(
        db: Session,
        preorder_id: str,
        update_data: PreOrderUpdate
    ) -> Optional[PreOrder]:
        """
        Update pre-order details
        """
        preorder = db.query(PreOrder).filter(PreOrder.id == preorder_id).first()
        
        if not preorder:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        
        for key, value in update_dict.items():
            setattr(preorder, key, value)
        
        # Set shipped_at when fulfillment_status changes to shipped
        if update_data.fulfillment_status == "shipped" and not preorder.shipped_at:
            preorder.shipped_at = datetime.utcnow()
        
        db.commit()
        db.refresh(preorder)
        
        return preorder
    
    @staticmethod
    def get_preorders(
        db: Session,
        email: Optional[str] = None,
        limit: int = 50
    ) -> List[PreOrder]:
        """
        Get pre-orders, optionally filtered by email
        """
        query = db.query(PreOrder)
        
        if email:
            query = query.filter(PreOrder.customer_email == email)
        
        return query.order_by(PreOrder.created_at.desc()).limit(limit).all()
