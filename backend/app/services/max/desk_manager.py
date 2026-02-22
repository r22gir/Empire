"""
MAX Desk Manager - Manages 8 AI desk agents for EmpireBox.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger("max.desk_manager")


class DeskStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    ERROR = "error"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"


class Task(BaseModel):
    id: str
    title: str
    description: str
    desk_id: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5  # 1-10, 1 is highest
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Desk(BaseModel):
    """AI Desk Agent configuration."""
    id: str
    name: str
    description: str
    status: DeskStatus = DeskStatus.IDLE
    domains: List[str]  # What this desk handles
    forge_products: List[str]  # Which Forge products it can access
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0


class DeskManager:
    """
    Manages all 8 AI desk agents for EmpireBox.
    Coordinates task assignment, monitors progress, and handles escalations.
    """
    
    def __init__(self):
        self._desks: Dict[str, Desk] = {}
        self._tasks: Dict[str, Task] = {}
        self._task_counter = 0
        self._initialize_desks()
    
    def _initialize_desks(self):
        """Initialize the 8 desk agents."""
        desk_configs = [
            {
                "id": "dev_bot",
                "name": "DevBot",
                "description": "Development & Code Tasks",
                "domains": ["code", "github", "bugs", "features", "pr_review", "testing"],
                "forge_products": ["all"]
            },
            {
                "id": "ops_bot",
                "name": "OpsBot",
                "description": "Operations & Infrastructure",
                "domains": ["servers", "deployment", "monitoring", "backups", "ci_cd", "security"],
                "forge_products": ["EmpireBox", "all"]
            },
            {
                "id": "sales_bot",
                "name": "SalesBot",
                "description": "Sales & Lead Management",
                "domains": ["leads", "pipeline", "follow_ups", "quotes", "proposals"],
                "forge_products": ["LeadForge", "ForgeCRM", "MarketF"]
            },
            {
                "id": "support_bot",
                "name": "SupportBot",
                "description": "Customer Support",
                "domains": ["tickets", "inquiries", "faq", "escalations", "feedback"],
                "forge_products": ["SupportForge", "ForgeCRM"]
            },
            {
                "id": "finance_bot",
                "name": "FinanceBot",
                "description": "Finance & Billing",
                "domains": ["invoicing", "payments", "expenses", "reports", "subscriptions"],
                "forge_products": ["EmpireBox", "Empire Wallet", "MarketF"]
            },
            {
                "id": "content_bot",
                "name": "ContentBot",
                "description": "Marketing & Content",
                "domains": ["listings", "descriptions", "social_media", "seo", "images"],
                "forge_products": ["MarketForge", "SocialForge", "ContentForge"]
            },
            {
                "id": "product_bot",
                "name": "ProductBot",
                "description": "Product & Inventory Management",
                "domains": ["workroom", "designs", "inventory", "scheduling", "production"],
                "forge_products": ["LuxeForge", "ContractorForge", "Workroom"]
            },
            {
                "id": "qa_bot",
                "name": "QABot",
                "description": "Quality Assurance",
                "domains": ["testing", "code_review", "quality", "validation", "standards"],
                "forge_products": ["all"]
            }
        ]
        
        for config in desk_configs:
            desk = Desk(**config)
            self._desks[desk.id] = desk
            logger.info(f"Initialized desk: {desk.name}")
    
    def get_all_desks(self) -> List[Dict[str, Any]]:
        """Get status of all desks."""
        return [
            {
                "id": desk.id,
                "name": desk.name,
                "description": desk.description,
                "status": desk.status.value,
                "domains": desk.domains,
                "forge_products": desk.forge_products,
                "current_task": desk.current_task,
                "stats": {
                    "completed": desk.tasks_completed,
                    "failed": desk.tasks_failed
                }
            }
            for desk in self._desks.values()
        ]
    
    def get_desk(self, desk_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific desk."""
        desk = self._desks.get(desk_id)
        if not desk:
            return None
        return {
            "id": desk.id,
            "name": desk.name,
            "description": desk.description,
            "status": desk.status.value,
            "domains": desk.domains,
            "forge_products": desk.forge_products,
            "current_task": desk.current_task,
            "stats": {
                "completed": desk.tasks_completed,
                "failed": desk.tasks_failed
            }
        }
    
    def find_best_desk(self, task_description: str, domains: List[str] = None) -> Optional[str]:
        """Find the best desk to handle a task based on domains."""
        if domains:
            for desk in self._desks.values():
                if desk.status == DeskStatus.IDLE:
                    if any(d in desk.domains for d in domains):
                        return desk.id
        
        # Fallback: find any idle desk
        for desk in self._desks.values():
            if desk.status == DeskStatus.IDLE:
                return desk.id
        
        return None
    
    def create_task(
        self,
        title: str,
        description: str,
        desk_id: Optional[str] = None,
        domains: List[str] = None,
        priority: int = 5
    ) -> Task:
        """Create a new task and optionally assign to a desk."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Find appropriate desk if not specified
        if not desk_id:
            desk_id = self.find_best_desk(description, domains)
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            desk_id=desk_id or "unassigned",
            priority=priority
        )
        
        self._tasks[task_id] = task
        
        # Assign to desk
        if desk_id and desk_id in self._desks:
            self._desks[desk_id].current_task = task_id
            self._desks[desk_id].status = DeskStatus.BUSY
            task.status = TaskStatus.IN_PROGRESS
        
        logger.info(f"Created task {task_id}: {title} -> {desk_id}")
        return task
    
    def complete_task(self, task_id: str, result: Dict[str, Any] = None) -> bool:
        """Mark a task as completed."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.updated_at = datetime.utcnow()
        
        # Update desk
        if task.desk_id in self._desks:
            desk = self._desks[task.desk_id]
            desk.current_task = None
            desk.status = DeskStatus.IDLE
            desk.tasks_completed += 1
        
        logger.info(f"Task {task_id} completed")
        return True
    
    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark a task as failed."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.status = TaskStatus.FAILED
        task.error = error
        task.updated_at = datetime.utcnow()
        
        # Update desk
        if task.desk_id in self._desks:
            desk = self._desks[task.desk_id]
            desk.current_task = None
            desk.status = DeskStatus.IDLE
            desk.tasks_failed += 1
        
        logger.info(f"Task {task_id} failed: {error}")
        return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return task.dict()
    
    def get_all_tasks(self, status: TaskStatus = None, desk_id: str = None) -> List[Dict[str, Any]]:
        """Get all tasks, optionally filtered."""
        tasks = list(self._tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        if desk_id:
            tasks = [t for t in tasks if t.desk_id == desk_id]
        
        return [t.dict() for t in sorted(tasks, key=lambda x: x.priority)]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get overall stats."""
        total_completed = sum(d.tasks_completed for d in self._desks.values())
        total_failed = sum(d.tasks_failed for d in self._desks.values())
        active_tasks = len([t for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS])
        pending_tasks = len([t for t in self._tasks.values() if t.status == TaskStatus.PENDING])
        
        return {
            "total_completed": total_completed,
            "total_failed": total_failed,
            "active_tasks": active_tasks,
            "pending_tasks": pending_tasks,
            "desks_busy": len([d for d in self._desks.values() if d.status == DeskStatus.BUSY]),
            "desks_idle": len([d for d in self._desks.values() if d.status == DeskStatus.IDLE])
        }


# Global instance
desk_manager = DeskManager()
