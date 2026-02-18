"""
Pydantic schemas for SupportForge models.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# Tenant Schemas
class SupportForgeTenantBase(BaseModel):
    name: str
    subdomain: str
    plan: str = "starter"
    settings: Dict[str, Any] = Field(default_factory=dict)


class SupportForgeTenantCreate(SupportForgeTenantBase):
    pass


class SupportForgeTenant(SupportForgeTenantBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Agent Schemas
class SupportForgeAgentBase(BaseModel):
    email: EmailStr
    name: str
    role: str = "agent"
    departments: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    status: str = "offline"
    max_concurrent_tickets: int = 10


class SupportForgeAgentCreate(SupportForgeAgentBase):
    tenant_id: UUID


class SupportForgeAgent(SupportForgeAgentBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Customer Schemas
class SupportForgeCustomerBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    company: Optional[str] = None
    empire_product_id: Optional[UUID] = None
    empire_product_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class SupportForgeCustomerCreate(SupportForgeCustomerBase):
    tenant_id: UUID


class SupportForgeCustomer(SupportForgeCustomerBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Ticket Schemas
class SupportForgeTicketBase(BaseModel):
    subject: str
    status: str = "new"
    priority: str = "normal"
    channel: str = "email"
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    assigned_agent_id: Optional[UUID] = None
    sla_policy_id: Optional[UUID] = None


class SupportForgeTicketCreate(SupportForgeTicketBase):
    tenant_id: UUID
    customer_id: UUID


class SupportForgeTicket(SupportForgeTicketBase):
    id: UUID
    tenant_id: UUID
    ticket_number: int
    customer_id: UUID
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Message Schemas
class SupportForgeMessageBase(BaseModel):
    content: str
    content_html: Optional[str] = None
    is_internal_note: bool = False
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    ai_suggested: bool = False


class SupportForgeMessageCreate(SupportForgeMessageBase):
    ticket_id: UUID
    sender_type: str  # customer, agent, system
    sender_id: Optional[UUID] = None


class SupportForgeMessage(SupportForgeMessageBase):
    id: UUID
    ticket_id: UUID
    sender_type: str
    sender_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Knowledge Base Article Schemas
class SupportForgeKBArticleBase(BaseModel):
    title: str
    slug: str
    content: str
    content_html: Optional[str] = None
    category_id: Optional[UUID] = None
    tags: List[str] = Field(default_factory=list)
    status: str = "draft"


class SupportForgeKBArticleCreate(SupportForgeKBArticleBase):
    tenant_id: UUID
    author_id: Optional[UUID] = None


class SupportForgeKBArticle(SupportForgeKBArticleBase):
    id: UUID
    tenant_id: UUID
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    author_id: Optional[UUID] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Automation Schemas
class SupportForgeAutomationBase(BaseModel):
    name: str
    trigger_type: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True


class SupportForgeAutomationCreate(SupportForgeAutomationBase):
    tenant_id: UUID


class SupportForgeAutomation(SupportForgeAutomationBase):
    id: UUID
    tenant_id: UUID
    execution_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# SLA Policy Schemas
class SupportForgeSLAPolicyBase(BaseModel):
    name: str
    first_response_time_minutes: int
    resolution_time_minutes: int
    business_hours_only: bool = False
    priority_multipliers: Dict[str, float] = Field(default_factory=dict)


class SupportForgeSLAPolicyCreate(SupportForgeSLAPolicyBase):
    tenant_id: UUID


class SupportForgeSLAPolicy(SupportForgeSLAPolicyBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Integration Schemas
class SupportForgeIntegrationBase(BaseModel):
    integration_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    is_active: bool = True


class SupportForgeIntegrationCreate(SupportForgeIntegrationBase):
    tenant_id: UUID


class SupportForgeIntegration(SupportForgeIntegrationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
