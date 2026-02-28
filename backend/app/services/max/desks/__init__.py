"""
AI Desk Delegation System — autonomous task routing and execution.
Each desk handles a specific domain and can operate independently.
"""

from .base_desk import BaseDesk, DeskTask, DeskAction
from .forge_desk import ForgeDesk
from .market_desk import MarketDesk
from .social_desk import SocialDesk
from .support_desk import SupportDesk
from .desk_router import DeskRouter
from .desk_manager import AIDeskManager, TaskStatus

__all__ = [
    "BaseDesk", "DeskTask", "DeskAction",
    "ForgeDesk", "MarketDesk", "SocialDesk", "SupportDesk",
    "DeskRouter", "AIDeskManager", "TaskStatus",
]
