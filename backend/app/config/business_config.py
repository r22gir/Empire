"""
Business configuration — loads from business.json.
Provides all customizable business values (tax rate, labor rate, markup, identity, etc.)
so nothing is hardcoded across the codebase.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

CONFIG_PATH = Path(__file__).parent / "business.json"


@dataclass
class BusinessConfig:
    business_name: str = "Empire"
    business_tagline: str = "Founder's Command Center"
    industry: str = "custom_drapery"
    owner_name: str = "Founder"
    timezone: str = "America/New_York"
    currency: str = "USD"
    tax_rate: float = 0.06
    labor_rate: float = 50.0
    install_rate_per_window: float = 85.0
    fabric_markup: float = 2.0
    quote_escalation_threshold: float = 5000.0
    followup_days_overdue: int = 7
    tier: str = "empire"
    ai_assistant_name: str = "MAX"
    ai_assistant_role: str = "AI Assistant Manager"
    telegram_enabled: bool = True
    services: Dict[str, int] = field(default_factory=lambda: {
        "backend_port": 8000,
        "dashboard_port": 3009,
        "workroom_port": 3001,
    })

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "BusinessConfig":
        """Load config from JSON file, falling back to defaults."""
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self, path: Path = CONFIG_PATH) -> None:
        """Persist current config to JSON."""
        from dataclasses import asdict
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
            f.write("\n")


# Singleton — loaded once at import time, reloadable via load()
biz = BusinessConfig.load()
