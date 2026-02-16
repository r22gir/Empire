import stripe
import os
from typing import Dict
from sqlalchemy.orm import Session

from .. import models

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class PaymentService:
    @staticmethod
    def calculate_commission(sale_price: float) -> float:
        """Calculate 3% commission"""
        return round(sale_price * 0.03, 2)
    
    @staticmethod
    async def process_sale(
        db: Session,
        listing_id: int,
        platform: str,
        sale_price: float,
        buyer_info: str = None
    ) -> models.Sale:
        """
        Process a sale transaction
        Creates sale record and calculates commission
        """
        # Get listing
        listing = db.query(models.Listing).filter(
            models.Listing.id == listing_id
        ).first()
        
        if not listing:
            raise ValueError("Listing not found")
        
        # Calculate commission
        commission = PaymentService.calculate_commission(sale_price)
        
        # Create sale record
        sale = models.Sale(
            user_id=listing.user_id,
            listing_id=listing_id,
            platform=platform,
            sale_price=sale_price,
            commission=commission,
            buyer_info=buyer_info
        )
        
        db.add(sale)
        db.commit()
        db.refresh(sale)
        
        return sale
    
    @staticmethod
    async def collect_commission(sale: models.Sale) -> Dict:
        """
        Collect commission via Stripe
        """
        try:
            # Create payment intent for commission
            intent = stripe.PaymentIntent.create(
                amount=int(sale.commission * 100),  # Convert to cents
                currency="usd",
                metadata={
                    "sale_id": sale.id,
                    "user_id": sale.user_id
                }
            )
            
            sale.stripe_payment_intent_id = intent.id
            
            return {
                "success": True,
                "payment_intent_id": intent.id
            }
        except stripe.error.StripeError as e:
            return {
                "success": False,
                "error": str(e)
            }
