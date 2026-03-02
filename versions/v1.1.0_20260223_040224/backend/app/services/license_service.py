import string
import random
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.license import License
from app.schemas.license import LicenseCreate, LicenseActivation

class LicenseService:
    @staticmethod
    def generate_license_key() -> str:
        """
        Generate a license key in format: EMPIRE-XXXX-XXXX-XXXX
        16 characters total (alphanumeric, uppercase)
        """
        chars = string.ascii_uppercase + string.digits
        # Remove confusing characters
        chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
        
        part1 = ''.join(random.choices(chars, k=4))
        part2 = ''.join(random.choices(chars, k=4))
        part3 = ''.join(random.choices(chars, k=4))
        
        return f"EMPIRE-{part1}-{part2}-{part3}"
    
    @staticmethod
    def create_licenses(
        db: Session,
        license_data: LicenseCreate
    ) -> List[License]:
        """
        Generate one or more license keys
        """
        licenses = []
        for _ in range(license_data.quantity):
            key = LicenseService.generate_license_key()
            
            # Ensure unique key
            while db.query(License).filter(License.key == key).first():
                key = LicenseService.generate_license_key()
            
            license = License(
                key=key,
                plan=license_data.plan,
                duration_months=license_data.duration_months,
                hardware_bundle=license_data.hardware_bundle,
                status="pending"
            )
            db.add(license)
            licenses.append(license)
        
        db.commit()
        for license in licenses:
            db.refresh(license)
        
        return licenses
    
    @staticmethod
    def validate_license(db: Session, key: str) -> Optional[License]:
        """
        Validate a license key
        """
        return db.query(License).filter(License.key == key).first()
    
    @staticmethod
    def activate_license(
        db: Session,
        key: str,
        activation_data: LicenseActivation
    ) -> tuple[bool, str, Optional[dict]]:
        """
        Activate a license for a user
        Returns: (success, message, subscription_details)
        """
        license = db.query(License).filter(License.key == key).first()
        
        if not license:
            return False, "License key not found", None
        
        if license.status == "activated":
            return False, "License key already activated", None
        
        if license.status == "expired":
            return False, "License key expired", None
        
        if license.status == "revoked":
            return False, "License key revoked", None
        
        # Activate the license
        license.status = "activated"
        license.user_id = activation_data.user_id
        license.activated_at = datetime.utcnow()
        license.expires_at = datetime.utcnow() + timedelta(days=30 * license.duration_months)
        
        db.commit()
        db.refresh(license)
        
        subscription_details = {
            "plan": license.plan,
            "duration_months": license.duration_months,
            "expires_at": license.expires_at.isoformat(),
            "hardware_bundle": license.hardware_bundle
        }
        
        return True, "License activated successfully", subscription_details
    
    @staticmethod
    def get_user_licenses(db: Session, user_id: str) -> List[License]:
        """
        Get all licenses for a user
        """
        return db.query(License).filter(License.user_id == user_id).all()
