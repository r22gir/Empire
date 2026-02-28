"""
AI Desk Delegation System — autonomous task routing and execution.
Each desk handles a specific domain and can operate independently.
"""

from .base_desk import BaseDesk, DeskTask, DeskAction
from .forge_desk import ForgeDesk
from .market_desk import MarketDesk
from .marketing_desk import MarketingDesk
from .support_desk import SupportDesk
from .sales_desk import SalesDesk
from .finance_desk import FinanceDesk
from .desk_router import DeskRouter
from .desk_manager import AIDeskManager, TaskStatus

__all__ = [
    "BaseDesk", "DeskTask", "DeskAction",
    "ForgeDesk", "MarketDesk", "MarketingDesk", "SupportDesk",
    "SalesDesk", "FinanceDesk",
    "DeskRouter", "AIDeskManager", "TaskStatus",
]
