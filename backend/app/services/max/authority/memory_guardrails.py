"""
Memory Guardrails for v10_test MAX.

v10_test MAX can READ canonical memory but CANNOT write it directly.
All memory modifications must go through the proposal workflow.
"""
from __future__ import annotations

from typing import Optional, Tuple

from .environment_policy import get_current_policy, FOUNDER_CHANNELS


class MemoryGuardrails:
    """Enforces read-only canonical memory for v10_test environment."""

    @staticmethod
    def can_write(channel: Optional[str] = None) -> Tuple[bool, str]:
        """Check if memory write is allowed from current environment.

        Returns (allowed, reason).
        """
        policy = get_current_policy()

        if policy.is_v10_test:
            return False, (
                "v10_test MAX has read-only access to canonical memory. "
                "To improve canonical memory, create a memory patch proposal instead."
            )

        # Canonical MAX — check channel
        if channel and channel.lower() in FOUNDER_CHANNELS:
            return True, "founder channel authorized"
        return False, (
            f"canonical memory write requires verified founder channel "
            f"(one of: {', '.join(sorted(FOUNDER_CHANNELS))})"
        )

    @staticmethod
    def can_read() -> Tuple[bool, str]:
        """Check if memory read is allowed from current environment."""
        policy = get_current_policy()
        return True, "memory read is allowed in all environments"

    @staticmethod
    def create_memory_proposal(
        category: str,
        subject: str,
        content: str,
        tags: Optional[list[str]] = None,
        importance: int = 5,
        channel: Optional[str] = None,
    ) -> dict:
        """Create a memory patch proposal instead of writing directly.

        Returns a proposal dict that can be submitted for founder review.
        """
        policy = get_current_policy()
        if policy.is_v10_test:
            from datetime import datetime, timezone
            proposal_id = f"mem_proposal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            return {
                "proposal_id": proposal_id,
                "type": "memory_patch",
                "environment": policy.environment_name,
                "category": category,
                "subject": subject,
                "content": content,
                "tags": tags or [],
                "importance": importance,
                "status": "pending_review",
                "submitted_by": "v10_test_MAX",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "review_required_from": list(FOUNDER_CHANNELS),
                "instructions": (
                    "This proposal was created by v10_test MAX which has read-only "
                    "canonical memory. A founder must review and approve this proposal "
                    "to apply the memory patch to canonical memory."
                ),
            }
        else:
            return {
                "error": "canonical MAX should write memory directly, not via proposal",
                "hint": "use MemoryStore.add_memory() instead",
            }


def check_memory_write(channel: Optional[str] = None) -> Tuple[bool, str]:
    """Shorthand for MemoryGuardrails.can_write(channel)."""
    return MemoryGuardrails.can_write(channel)