"""Desk-aware system prompt builder — loads desk config + live task counts."""
import json
import logging
from app.db.database import get_db, dict_row, dict_rows
from .system_prompt import get_system_prompt

logger = logging.getLogger("max.desk_prompt")


def _load_desk_config(desk_id: str) -> dict | None:
    """Load desk configuration from desk_configs table."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM desk_configs WHERE desk_id = ? AND is_active = 1",
                (desk_id,),
            ).fetchone()
            return dict_row(row)
    except Exception as e:
        logger.warning(f"Could not load desk config for {desk_id}: {e}")
        return None


def _load_desk_task_counts(desk_id: str) -> dict:
    """Fetch live task status counts for a desk."""
    counts = {"todo": 0, "in_progress": 0, "waiting": 0, "done": 0}
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM tasks WHERE desk = ? AND status != 'cancelled' GROUP BY status",
                (desk_id,),
            ).fetchall()
            for r in dict_rows(rows):
                if r["status"] in counts:
                    counts[r["status"]] = r["cnt"]
    except Exception as e:
        logger.debug(f"Could not load task counts for {desk_id}: {e}")
    return counts


def get_desk_system_prompt(desk_id: str) -> str:
    """Build a composite system prompt for a specific desk.

    Falls back to the general MAX system prompt if desk is not found.
    """
    config = _load_desk_config(desk_id)
    if not config or not config.get("system_prompt"):
        # Fallback: use general prompt
        return get_system_prompt()

    counts = _load_desk_task_counts(desk_id)
    total_open = counts["todo"] + counts["in_progress"] + counts["waiting"]

    task_summary = (
        f"Current {desk_id} desk tasks: "
        f"{counts['todo']} to-do, {counts['in_progress']} in progress, "
        f"{counts['waiting']} waiting, {counts['done']} done. "
        f"({total_open} open)"
    )

    try:
        from app.services.max.tool_executor import TOOLS_DOC
        tool_instructions = f"\n\n{TOOLS_DOC}"
    except Exception:
        tool_instructions = ""

    # Inject code of conduct for this desk
    try:
        from app.services.max.conduct import get_conduct_prompt
        conduct_section = get_conduct_prompt(desk_id)
    except Exception:
        conduct_section = ""

    return f"{config['system_prompt']}\n\n## Live Context\n{task_summary}{conduct_section}{tool_instructions}"
