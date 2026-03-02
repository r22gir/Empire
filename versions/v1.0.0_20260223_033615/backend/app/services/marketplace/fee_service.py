from app.core.config import settings


def calculate_marketplace_fee(subtotal: float) -> float:
    """Calculate the MarketF marketplace fee (8% of subtotal)"""
    return round(subtotal * (settings.MARKETF_FEE_PERCENT / 100), 2)


def calculate_payment_processing_fee(subtotal: float) -> float:
    """Calculate payment processing fee (Stripe: 2.9% + $0.30)"""
    return round(
        (subtotal * (settings.PAYMENT_PROCESSING_FEE_PERCENT / 100)) + 
        settings.PAYMENT_PROCESSING_FEE_FIXED, 
        2
    )


def calculate_seller_payout(subtotal: float) -> float:
    """Calculate what the seller will receive after fees"""
    marketplace_fee = calculate_marketplace_fee(subtotal)
    payment_fee = calculate_payment_processing_fee(subtotal)
    return round(subtotal - marketplace_fee - payment_fee, 2)


def calculate_order_totals(product_price: float, shipping_price: float) -> dict:
    """
    Calculate all order totals and fees
    
    Returns:
        dict with keys: subtotal, marketplace_fee, payment_processing_fee, total, seller_payout
    """
    subtotal = product_price + shipping_price
    marketplace_fee = calculate_marketplace_fee(product_price)
    payment_processing_fee = calculate_payment_processing_fee(subtotal)
    total = subtotal
    seller_payout = round(product_price - marketplace_fee, 2)
    
    return {
        "subtotal": round(subtotal, 2),
        "marketplace_fee": marketplace_fee,
        "payment_processing_fee": payment_processing_fee,
        "total": total,
        "seller_payout": seller_payout
    }
