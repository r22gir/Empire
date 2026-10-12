"""
AI Desk Delegation System — autonomous task routing and execution.
Each desk handles a specific domain and can operate independently.

Imports are lazy so `from app.services.max.desks.live_data import …`
does not load every desk (and tool_executor / inpaint) at collection time.
"""

__all__ = [
    "BaseDesk", "DeskTask", "DeskAction",
    "ForgeDesk", "MarketDesk", "MarketingDesk", "SupportDesk",
    "SalesDesk", "FinanceDesk", "ClientsDesk", "ContractorsDesk",
    "ITDesk", "WebsiteDesk", "LegalDesk", "LabDesk",
    "InnovationDesk", "IntakeDesk", "AnalyticsDesk", "QualityDesk",
    "CodeForgeDesk",
    "DeskRouter", "AIDeskManager", "TaskStatus",
]

_LAZY = {
    "BaseDesk": (".base_desk", "BaseDesk"),
    "DeskTask": (".base_desk", "DeskTask"),
    "DeskAction": (".base_desk", "DeskAction"),
    "ForgeDesk": (".forge_desk", "ForgeDesk"),
    "MarketDesk": (".market_desk", "MarketDesk"),
    "MarketingDesk": (".marketing_desk", "MarketingDesk"),
    "SupportDesk": (".support_desk", "SupportDesk"),
    "SalesDesk": (".sales_desk", "SalesDesk"),
    "FinanceDesk": (".finance_desk", "FinanceDesk"),
    "ClientsDesk": (".clients_desk", "ClientsDesk"),
    "ContractorsDesk": (".contractors_desk", "ContractorsDesk"),
    "ITDesk": (".it_desk", "ITDesk"),
    "WebsiteDesk": (".website_desk", "WebsiteDesk"),
    "LegalDesk": (".legal_desk", "LegalDesk"),
    "LabDesk": (".lab_desk", "LabDesk"),
    "InnovationDesk": (".innovation_desk", "InnovationDesk"),
    "IntakeDesk": (".intake_desk", "IntakeDesk"),
    "AnalyticsDesk": (".analytics_desk", "AnalyticsDesk"),
    "QualityDesk": (".quality_desk", "QualityDesk"),
    "CodeForgeDesk": (".codeforge_desk", "CodeForgeDesk"),
    "DeskRouter": (".desk_router", "DeskRouter"),
    "AIDeskManager": (".desk_manager", "AIDeskManager"),
    "TaskStatus": (".desk_manager", "TaskStatus"),
}


def __getattr__(name: str):
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(target[0], __name__), target[1])
    globals()[name] = value
    return value
