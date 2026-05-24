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
    lines.append("- Email truth is layered: DNS/domain setup, Cloudflare routing, Gmail delivery, backend Gmail OAuth, outbound SendGrid/SMTP, and reply threading are separate checks.")
    lines.append("- Do not claim max@empirebox.store inbox access unless check_email or /api/v1/max/gmail/inbox returns success in the current runtime.")
    lines.append("- Inbound email via /webhooks/email/inbound logs/classifies email; it is not a verified MAX auto-reply loop.")
    lines.append("- Telegram is configured/partial until a live send/receive test passes; never claim a Telegram send unless the tool result succeeds.")
    lines.append("- Hermes email is not implemented; Hermes remains supporting context beneath MAX.")
    return "\n".join(lines)
