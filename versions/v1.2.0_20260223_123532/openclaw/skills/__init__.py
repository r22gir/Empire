"""OpenClaw skills package."""

from .base import Skill
from .general import SearchSkill, CodeSkill, FileSkill
from .empirebox import EmpireBoxSkill
from .smarthome import SmartHomeSkill
from .calendar import CalendarSkill

__all__ = [
    "Skill",
    "SearchSkill",
    "CodeSkill",
    "FileSkill",
    "EmpireBoxSkill",
    "SmartHomeSkill",
    "CalendarSkill",
]
