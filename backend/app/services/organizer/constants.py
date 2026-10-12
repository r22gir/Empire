"""Shared Organizer vocab: people roles, item kinds, and legacy calendar types."""

# Existing schedule_events.type CHECK values — never write unknown values here.
LEGACY_EVENT_TYPES = {
    "install",
    "delivery",
    "pickup",
    "drop_off",
    "fabric_pickup",
    "measure",
    "loading_dock",
    "errand",
    "other",
}

# Public calendar / appointment kinds Rafael asked for, plus the legacy set.
CALENDAR_EVENT_TYPES = {
    "job_milestone",
    "measure",
    "install",
    "pickup",
    "drop_off",
    "fitting",
    "delivery",
    "meeting",
    "appointment",
    "fabric_pickup",
    "loading_dock",
    "errand",
    "travel",
    "medical",
    "school",
    "legal",
    "admin",
    "social",
    "other",
}

# Non-appointment organizer items (still appear on the unified board).
ORGANIZER_ITEM_KINDS = {
    "todo",
    "reminder",
    "followup",
    "material_order",
    "call",
    "deadline",
}

ITEM_KINDS = CALENDAR_EVENT_TYPES | ORGANIZER_ITEM_KINDS

FOLLOWUP_KINDS = {"quote", "payment", "deposit", "general"}

RESOURCE_ROLES = {
    "installer",
    "seamstress",
    "upholsterer",
    "driver",
    "designer",
    "client",
    "vendor",
    "supplier",
    "inspector",
    "family",
    "friend",
    "doctor",
    "teacher",
    "coach",
    "teammate",
    "partner",
    "other",
}

# Roles we hydrate from existing customers / contacts / vendors.
DIRECTORY_ROLES = {
    "client": "client",
    "designer": "designer",
    "contractor": "installer",
    "vendor": "vendor",
    "other": "supplier",
}

# Map a public kind onto a CHECK-safe schedule_events.type value.
KIND_TO_LEGACY_TYPE = {
    "job_milestone": "other",
    "fitting": "other",
    "meeting": "other",
    "appointment": "other",
    "todo": "other",
    "reminder": "other",
    "followup": "other",
    "material_order": "other",
    "call": "errand",
    "deadline": "other",
    "travel": "errand",
    "medical": "other",
    "school": "other",
    "legal": "other",
    "admin": "other",
    "social": "other",
}

ITEM_STATUSES = {"open", "planned", "confirmed", "in_progress", "done", "cancelled", "snoozed"}
EVENT_STATUSES = {"planned", "confirmed", "done", "cancelled"}

BOARD_COLUMNS = (
    {"id": "open", "label": "Open", "statuses": ("open", "planned", "snoozed")},
    {"id": "doing", "label": "Doing", "statuses": ("in_progress", "confirmed")},
    {"id": "done", "label": "Done", "statuses": ("done",)},
)
TODAY_COLUMNS = ("overdue", "today", "upcoming")

DEFAULT_TRAVEL_GAP_MINUTES = 30
DEFAULT_EVENT_MINUTES = 60

# Never auto-send. The owner's tap is required on every edition.
OUTBOUND_POLICY = (
    "Draft only. Nothing is sent without the owner's tap."
)
