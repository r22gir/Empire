import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from enum import Enum

class ThreatLevel(Enum):
    SAFE = "safe"
    MALICIOUS = "malicious"

class GuardrailsService:
    RATE_LIMIT = 10
    RATE_WINDOW = 60

    INJECTION_PATTERNS = [
        r"ignore.*(previous|prior).*instructions",
        r"forget.*instructions",
        r"you are now.*mode",
        r"pretend.*you are",
        r"jailbreak",
        r"DAN mode",
        r"reveal.*system.*prompt",
        r"show.*system.*prompt",
    ]

    SENSITIVE_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",
        r"sk-ant-[a-zA-Z0-9-]{20,}",
        r"/home/[a-zA-Z0-9_]+/",
    ]

    def __init__(self):
        self.request_counts = defaultdict(list)
        self.blocked_sessions = {}
        self.audit_log = []
        self.injection_regex = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self.sensitive_regex = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]

    def check_rate_limit(self, session_id: str) -> Tuple[bool, int]:
        now = time.time()
        self.request_counts[session_id] = [t for t in self.request_counts[session_id] if t > now - self.RATE_WINDOW]
        if len(self.request_counts[session_id]) >= self.RATE_LIMIT:
            return False, self.RATE_WINDOW
        self.request_counts[session_id].append(now)
        return True, 0

    def analyze_input(self, text: str, session_id: str) -> Tuple[ThreatLevel, Optional[str]]:
        if session_id in self.blocked_sessions:
            if datetime.now() - self.blocked_sessions[session_id] < timedelta(hours=24):
                return ThreatLevel.MALICIOUS, "Session blocked."
        for pattern in self.injection_regex:
            if pattern.search(text):
                self.blocked_sessions[session_id] = datetime.now()
                return ThreatLevel.MALICIOUS, "Security violation. Session terminated."
        return ThreatLevel.SAFE, None

    def filter_response(self, response: str) -> str:
        for pattern in self.sensitive_regex:
            response = pattern.sub("[REDACTED]", response)
        return response

guardrails = GuardrailsService()
