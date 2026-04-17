"""Loads capability registry and generates system prompt capabilities section."""
import json, os

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "capability_registry.json")

def load_registry():
    with open(REGISTRY_PATH) as f:
        return json.load(f)["capabilities"]

def get_capabilities_for_channel(channel: str) -> list:
    return [c for c in load_registry() if c["enabled"] and channel in c["channel_scope"]]

def generate_capability_prompt(channel: str) -> str:
    caps = get_capabilities_for_channel(channel)
    if not caps:
        return ""
    lines = ["\n## VERIFIED CAPABILITIES (from registry — do not claim others):"]
    for c in caps:
        lines.append(f"- {c['display_name']}: {c['notes']}")
    lines.append("\n## WHAT I CANNOT DO:")
    lines.append("- I cannot attach files directly to chat messages. I generate files that you download separately.")
    lines.append("- I will NEVER claim I sent/attached something unless the tool returned proof it succeeded.")
    lines.append("- On web chat: drawings display INLINE by default. I do NOT email/Telegram them unless asked.")
    lines.append("- MAX inbox (max@empirebox.store) is readable via Gmail OAuth. Founder email (empirebox2026@gmail.com) is also visible in the same Gmail inbox as emails to max@empirebox.store — they share the same Google account (empirebox2026@gmail.com) configured to receive for max@.")
    lines.append("- Inbound email via SendGrid webhook (/webhooks/email/inbound) is a separate intake path — both routes store to unified_messages.")
    lines.append("- Reply threading: MAX can send reply via SendGrid outbound but thread continuity depends on message-id/in-reply-to headers; not independently proven end-to-end.")
    return "\n".join(lines)
