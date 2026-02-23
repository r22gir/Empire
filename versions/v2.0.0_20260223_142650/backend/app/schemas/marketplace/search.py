from pydantic import BaseModel
from typing import Optional, List


class SearchRequest(BaseModel):
    q: Optional[str] = None
    category: Optional[str] = None
    condition: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort: Optional[str] = "newest"  # newest, price_asc, price_desc, relevance
    page: int = 1
    per_page: int = 24


class ShippingEstimateRequest(BaseModel):
    product_id: str
    destination_zip: str


class ShippingRate(BaseModel):
    carrier: str
    service: str
    price: float
    days: int


class ShippingEstimateResponse(BaseModel):
    rates: List[ShippingRate]
