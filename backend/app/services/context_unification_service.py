"""
Context Unification Service for synthesizing decision context from multiple chat sessions.
Provides unified context for consistent decision-making across AI agents.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.chat_backup import ChatSession, ChatMessage, DecisionContext, DisruptionEvent
from app.schemas.chat_backup import (
    DecisionContextCreate, DecisionContextUpdate,
    DisruptionEventCreate, DisruptionEventUpdate
)


class ContextUnificationService:
    """Service for unifying and synthesizing decision context."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============ Decision Context Operations ============

    async def create_context(self, context_data: DecisionContextCreate) -> DecisionContext:
        """Create a new decision context."""
        context = DecisionContext(
            title=context_data.title,
            category=context_data.category,
            summary=context_data.summary,
            key_decisions=context_data.key_decisions,
            action_items=context_data.action_items,
            context_data=context_data.context_data,
            source_session_ids=[str(sid) for sid in context_data.source_session_ids],
            source_count=len(context_data.source_session_ids),
            priority=context_data.priority.value if hasattr(context_data.priority, 'value') else context_data.priority,
            valid_until=context_data.valid_until
        )
        self.db.add(context)
        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def get_context(self, context_id: UUID) -> Optional[DecisionContext]:
        """Get a decision context by ID."""
        result = await self.db.execute(
            select(DecisionContext).where(DecisionContext.id == context_id)
        )
        return result.scalar_one_or_none()

    async def get_contexts(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DecisionContext]:
        """Get decision contexts with optional filters."""
        query = select(DecisionContext)

        if category:
            query = query.where(DecisionContext.category == category)
        if priority:
            query = query.where(DecisionContext.priority == priority)
        if status:
            query = query.where(DecisionContext.status == status)
        else:
            # Default to active contexts
            query = query.where(DecisionContext.status == "active")

        query = query.order_by(DecisionContext.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_active_contexts(self) -> List[DecisionContext]:
        """Get all active decision contexts."""
        now = datetime.now(timezone.utc)
        query = select(DecisionContext).where(
            and_(
                DecisionContext.status == "active",
                or_(
                    DecisionContext.valid_until.is_(None),
                    DecisionContext.valid_until > now
                )
            )
        ).order_by(
            # Order by priority (critical first) then by creation date
            DecisionContext.priority.desc(),
            DecisionContext.created_at.desc()
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_context(self, context_id: UUID, update_data: DecisionContextUpdate) -> Optional[DecisionContext]:
        """Update a decision context."""
        context = await self.get_context(context_id)
        if not context:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if key == 'priority' and hasattr(value, 'value'):
                value = value.value
            setattr(context, key, value)

        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def archive_context(self, context_id: UUID) -> Optional[DecisionContext]:
        """Archive a decision context."""
        context = await self.get_context(context_id)
        if not context:
            return None

        context.status = "archived"
        await self.db.commit()
        await self.db.refresh(context)
        return context

    # ============ Context Unification ============

    async def unify_sessions(
        self,
        session_ids: List[UUID],
        title: str,
        category: Optional[str] = None,
        priority: str = "normal",
        include_action_items: bool = True
    ) -> DecisionContext:
        """
        Unify multiple chat sessions into a single decision context.
        Extracts key decisions and action items from the conversations.
        """
        # Fetch all sessions with messages
        sessions = []
        all_messages = []
        
        for session_id in session_ids:
            result = await self.db.execute(
                select(ChatSession)
                .options(selectinload(ChatSession.messages))
                .where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                sessions.append(session)
                # Get messages sorted by sequence
                msg_result = await self.db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.sequence_number)
                )
                all_messages.extend(list(msg_result.scalars().all()))

        if not sessions:
            raise ValueError("No valid sessions found for unification")

        # Synthesize context from messages
        summary = await self._synthesize_summary(sessions, all_messages)
        key_decisions = await self._extract_key_decisions(all_messages)
        action_items = await self._extract_action_items(all_messages) if include_action_items else []

        # Create context data with source information
        context_data = {
            "session_count": len(sessions),
            "message_count": len(all_messages),
            "sources": [
                {
                    "session_id": str(s.id),
                    "source": s.source,
                    "ai_model": s.ai_model,
                    "started_at": s.started_at.isoformat() if s.started_at else None
                }
                for s in sessions
            ],
            "unified_at": datetime.now(timezone.utc).isoformat()
        }

        # Create the unified context
        context = DecisionContext(
            title=title,
            category=category,
            summary=summary,
            key_decisions=key_decisions,
            action_items=action_items,
            context_data=context_data,
            source_session_ids=[str(sid) for sid in session_ids],
            source_count=len(session_ids),
            priority=priority
        )
        self.db.add(context)
        await self.db.commit()
        await self.db.refresh(context)
        return context

    async def _synthesize_summary(self, sessions: List[ChatSession], messages: List[ChatMessage]) -> str:
        """Synthesize a summary from chat sessions and messages."""
        # Build a comprehensive summary
        summary_parts = []

        # Session overview
        summary_parts.append(f"Context unified from {len(sessions)} chat session(s):")
        
        for session in sessions:
            session_info = f"\n- {session.title or 'Untitled'} ({session.source})"
            if session.ai_model:
                session_info += f" using {session.ai_model}"
            summary_parts.append(session_info)

        # Key content extraction
        summary_parts.append(f"\n\nTotal messages analyzed: {len(messages)}")
        
        # Extract significant content (assistant responses typically contain decisions/conclusions)
        assistant_messages = [m for m in messages if m.role == "assistant"]
        if assistant_messages:
            # Take the most recent significant responses
            recent_responses = assistant_messages[-3:] if len(assistant_messages) >= 3 else assistant_messages
            summary_parts.append("\n\nKey discussion points:")
            for msg in recent_responses:
                # Truncate long messages
                content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                summary_parts.append(f"\n- {content}")

        return "".join(summary_parts)

    async def _extract_key_decisions(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Extract key decisions from messages."""
        decisions = []
        
        # Look for decision indicators in messages
        decision_keywords = [
            "decided", "decision", "agreed", "will proceed", "going to",
            "chosen", "selected", "implemented", "plan to", "strategy",
            "approach will be", "conclusion"
        ]

        for msg in messages:
            content_lower = msg.content.lower()
            for keyword in decision_keywords:
                if keyword in content_lower:
                    # Extract context around the keyword
                    decisions.append({
                        "content": msg.content[:300] if len(msg.content) > 300 else msg.content,
                        "role": msg.role,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                        "keyword_match": keyword
                    })
                    break  # One decision per message

        # Limit to most significant decisions
        return decisions[-10:] if len(decisions) > 10 else decisions

    async def _extract_action_items(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Extract action items from messages."""
        action_items = []
        
        # Look for action item indicators
        action_keywords = [
            "todo", "to do", "action item", "next step", "need to",
            "should", "must", "will", "task:", "implement", "create",
            "update", "fix", "add", "remove", "change"
        ]

        for msg in messages:
            content_lower = msg.content.lower()
            for keyword in action_keywords:
                if keyword in content_lower:
                    action_items.append({
                        "content": msg.content[:200] if len(msg.content) > 200 else msg.content,
                        "role": msg.role,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                        "status": "pending",
                        "keyword_match": keyword
                    })
                    break  # One action per message

        # Return unique action items, limited
        return action_items[-15:] if len(action_items) > 15 else action_items

    async def get_unified_context_for_agents(self) -> Dict[str, Any]:
        """
        Get a unified context object suitable for AI agents.
        Combines all active decision contexts into a single reference.
        """
        active_contexts = await self.get_active_contexts()
        
        if not active_contexts:
            return {
                "status": "no_context",
                "message": "No active decision contexts available",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Build unified context for agents
        unified = {
            "status": "active",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_count": len(active_contexts),
            "priority_summary": {},
            "key_decisions": [],
            "pending_actions": [],
            "categories": {},
            "contexts": []
        }

        for ctx in active_contexts:
            # Add to contexts
            unified["contexts"].append({
                "id": str(ctx.id),
                "title": ctx.title,
                "category": ctx.category,
                "priority": ctx.priority,
                "summary": ctx.summary[:500] if len(ctx.summary) > 500 else ctx.summary
            })

            # Aggregate key decisions
            unified["key_decisions"].extend(ctx.key_decisions)

            # Aggregate pending actions
            unified["pending_actions"].extend([
                a for a in ctx.action_items if a.get("status") == "pending"
            ])

            # Count by priority
            unified["priority_summary"][ctx.priority] = unified["priority_summary"].get(ctx.priority, 0) + 1

            # Group by category
            if ctx.category:
                if ctx.category not in unified["categories"]:
                    unified["categories"][ctx.category] = []
                unified["categories"][ctx.category].append(str(ctx.id))

        # Limit aggregated items
        unified["key_decisions"] = unified["key_decisions"][-20:]
        unified["pending_actions"] = unified["pending_actions"][-20:]

        return unified

    # ============ Disruption Event Operations ============

    async def log_disruption(self, event_data: DisruptionEventCreate) -> DisruptionEvent:
        """Log a disruption event."""
        event = DisruptionEvent(
            event_type=event_data.event_type,
            description=event_data.description,
            session_id=event_data.session_id,
            previous_state=event_data.previous_state,
            new_state=event_data.new_state,
            impact_level=event_data.impact_level.value if hasattr(event_data.impact_level, 'value') else event_data.impact_level
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_disruption_event(self, event_id: UUID) -> Optional[DisruptionEvent]:
        """Get a disruption event by ID."""
        result = await self.db.execute(
            select(DisruptionEvent).where(DisruptionEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_recent_disruptions(self, limit: int = 10) -> List[DisruptionEvent]:
        """Get recent disruption events."""
        result = await self.db.execute(
            select(DisruptionEvent)
            .order_by(DisruptionEvent.occurred_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unresolved_disruptions(self) -> List[DisruptionEvent]:
        """Get unresolved disruption events."""
        result = await self.db.execute(
            select(DisruptionEvent)
            .where(DisruptionEvent.resolved.is_(False))
            .order_by(DisruptionEvent.occurred_at.desc())
        )
        return list(result.scalars().all())

    async def resolve_disruption(
        self,
        event_id: UUID,
        resolution_notes: Optional[str] = None
    ) -> Optional[DisruptionEvent]:
        """Mark a disruption event as resolved."""
        event = await self.get_disruption_event(event_id)
        if not event:
            return None

        event.resolved = True
        event.resolution_notes = resolution_notes
        event.resolved_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(event)
        return event

    # ============ Statistics ============

    async def get_context_count(self, status: Optional[str] = None) -> int:
        """Get count of decision contexts."""
        query = select(func.count(DecisionContext.id))
        if status:
            query = query.where(DecisionContext.status == status)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_disruption_count(self, resolved: Optional[bool] = None) -> int:
        """Get count of disruption events."""
        query = select(func.count(DisruptionEvent.id))
        if resolved is not None:
            query = query.where(DisruptionEvent.resolved == resolved)
        result = await self.db.execute(query)
        return result.scalar() or 0
