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
from .clients_desk import ClientsDesk
from .contractors_desk import ContractorsDesk
from .it_desk import ITDesk
from .website_desk import WebsiteDesk
from .legal_desk import LegalDesk
from .lab_desk import LabDesk
from .desk_router import DeskRouter
from .desk_manager import AIDeskManager, TaskStatus

__all__ = [
    "BaseDesk", "DeskTask", "DeskAction",
    "ForgeDesk", "MarketDesk", "MarketingDesk", "SupportDesk",
    "SalesDesk", "FinanceDesk", "ClientsDesk", "ContractorsDesk",
    "ITDesk", "WebsiteDesk", "LegalDesk", "LabDesk",
    "DeskRouter", "AIDeskManager", "TaskStatus",
]
