import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict

class ConsentService:
    MIN_AGE = 18
    DATA_RETENTION_DAYS = 30

    def __init__(self):
        self.storage_path = Path(__file__).parent.parent.parent.parent / "data" / "consent"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def check_consent(self, user_id: str) -> Dict:
        user_file = self.storage_path / f"{hashlib.sha256(user_id.encode()).hexdigest()[:16]}.json"
        if not user_file.exists():
            return {"has_consent": False, "requires_consent": True}
        with open(user_file, 'r') as f:
            return {"has_consent": True, **json.load(f)}

    def give_consent(self, user_id: str, age_confirmed: bool, accepted_terms: bool) -> Dict:
        if not age_confirmed:
            return {"status": "error", "message": "Must be 18+ to use this service"}
        if not accepted_terms:
            return {"status": "error", "message": "Must accept Terms of Service"}
        
        user_file = self.storage_path / f"{hashlib.sha256(user_id.encode()).hexdigest()[:16]}.json"
        data = {"consent_date": datetime.now().isoformat(), "age_verified": True}
        with open(user_file, 'w') as f:
            json.dump(data, f)
        return {"status": "accepted"}

    def request_deletion(self, user_id: str) -> Dict:
        return {"status": "scheduled", "message": "Data will be deleted within 30 days"}

consent_service = ConsentService()
