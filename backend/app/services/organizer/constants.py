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
}

ITEM_STATUSES = {"open", "planned", "confirmed", "done", "cancelled", "snoozed"}
EVENT_STATUSES = {"planned", "confirmed", "done", "cancelled"}

DEFAULT_TRAVEL_GAP_MINUTES = 30
DEFAULT_EVENT_MINUTES = 60

# Never auto-send anything to a customer. Reminders stay drafts.
OUTBOUND_POLICY = (
    "Draft only. Nothing is sent to a customer without founder approval."
)
