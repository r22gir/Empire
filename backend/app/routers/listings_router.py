from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from datetime import datetime

from .. import models, schemas, auth
from ..database import get_db
from ..services.marketplace_service import MarketplaceService

router = APIRouter(prefix="/listings", tags=["listings"])

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=schemas.Listing)
async def create_listing(
    title: str,
    description: str,
    price: float,
    platforms: str,  # Comma-separated: "ebay,facebook,poshmark"
    photo: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Save photo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{current_user.id}_{timestamp}_{photo.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(photo.file, buffer)
    
    # Create listing in database
    db_listing = models.Listing(
        user_id=current_user.id,
        title=title,
        description=description,
        price=price,
        photo_url=file_path
    )
    
    # Parse platforms
    platform_list = [p.strip() for p in platforms.split(",")]
    
    # Post to marketplaces
    marketplace_service = MarketplaceService(current_user, db)
    results = await marketplace_service.post_to_platforms(
        listing=db_listing,
        platforms=platform_list
    )
    
    # Update listing with platform statuses
    for platform, result in results.items():
        if platform == "ebay":
            db_listing.posted_ebay = result["success"]
            if result.get("listing_id"):
                db_listing.ebay_listing_id = result["listing_id"]
        elif platform == "facebook":
            db_listing.posted_facebook = result["success"]
            if result.get("listing_id"):
                db_listing.facebook_listing_id = result["listing_id"]
        elif platform == "poshmark":
            db_listing.posted_poshmark = result["success"]
            if result.get("listing_id"):
                db_listing.poshmark_listing_id = result["listing_id"]
        elif platform == "mercari":
            db_listing.posted_mercari = result["success"]
            if result.get("listing_id"):
                db_listing.mercari_listing_id = result["listing_id"]
    
    db.add(db_listing)
    db.commit()
    db.refresh(db_listing)
    
    return db_listing

@router.get("/", response_model=List[schemas.Listing])
def get_listings(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    listings = db.query(models.Listing).filter(
        models.Listing.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return listings

@router.get("/{listing_id}", response_model=schemas.Listing)
def get_listing(
    listing_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(models.Listing).filter(
        models.Listing.id == listing_id,
        models.Listing.user_id == current_user.id
    ).first()
    
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return listing
