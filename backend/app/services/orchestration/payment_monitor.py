"""
Payment Monitor — Auto-chase overdue invoices
Runs hourly, sends reminders, escalates after 7 days.
"""
import logging
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("payment_monitor")

API = "http://localhost:8000/api/v1"


class PaymentMonitor:
    def __init__(self):
        self.escalation_days = 7
        self.grace_days = 30

    async def scan_overdue_invoices(self, days: int = 30) -> list[dict]:
        """Scan for invoices overdue by `days` or more."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"{API}/invoices",
                    params={"status": "overdue", "days_overdue": days},
                )
                if r.ok:
                    data = r.json()
                    return data.get("invoices", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.warning(f"Invoice scan failed: {e}")
        return []

    def draft_reminder(self, invoice: dict) -> dict:
        """Generate personalized reminder email based on days overdue."""
        client_name = invoice.get("client_name", "there")
        invoice_id = invoice.get("id", "—")
        amount = invoice.get("amount", 0)
        days_overdue = invoice.get("days_overdue", 0)
        product = invoice.get("product", "your order")

        tone = "friendly" if days_overdue < self.escalation_days else "firm"

        body = f"""Hi {client_name},

Hope you're loving your {product}! 🙏

Just a friendly reminder that invoice #{invoice_id} for ${amount:,.2f} is now {days_overdue} days past due.

We'd love to hear from you — sometimes things slip through the cracks!
If you have any questions or need an extension, just reply and we'll sort it out.

If payment was already sent, please disregard this message!

Warm regards,
Empire Workroom
"""

        subject = f"Gentle reminder — Invoice #{invoice_id} ({days_overdue} days overdue)"

        return {
            "to": invoice.get("client_email", ""),
            "subject": subject,
            "body": body,
            "days_overdue": days_overdue,
            "tone": tone,
        }

    async def send_reminder(self, client_email: str, reminder: dict) -> dict:
        """Send reminder via email/SMS."""
        if not client_email:
            return {"sent": False}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{API}/socialforge/send_email",
                    json={
                        "to": client_email,
                        "subject": reminder["subject"],
                        "body": reminder["body"],
                    },
                )
                return {"sent": r.ok, "channel": "email"}
        except Exception as e:
            logger.warning(f"Reminder send failed: {e}")
            return {"sent": False}

    async def track_response(self, invoice_id: str, response: str):
        """Log payment response to Hermes."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{API}/hermes/log_communication",
                    json={
                        "event": "payment_reminder_response",
                        "invoice_id": invoice_id,
                        "response": response,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.warning(f"Hermes tracking failed: {e}")

    async def escalate_to_founder(self, invoice: dict) -> dict:
        """Escalate to founder when no response after escalation_days."""
        client_name = invoice.get("client_name", "Unknown")
        invoice_id = invoice.get("id", "—")
        amount = invoice.get("amount", 0)
        days_overdue = invoice.get("days_overdue", 0)
        last_reminder = invoice.get("last_reminder_at", "never")

        message = f"""[ESCALATION] Payment overdue — action needed

Client: {client_name}
Invoice: #{invoice_id}
Amount: ${amount:,.2f}
Days overdue: {days_overdue}
Last reminder: {last_reminder}

Consider:
• Direct phone call
• Payment plan offer
• Pause services until resolved"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{API}/notifications/telegram",
                    json={"message": message, "priority": "high"},
                )
                return {"escalated": r.ok}
        except Exception as e:
            logger.warning(f"Escalation failed: {e}")
            return {"escalated": False}

    async def run_hourly_scan(self) -> dict:
        """Full hourly payment monitoring cycle."""
        overdue = await self.scan_overdue_invoices(days=self.grace_days)

        results = {"invoices_scanned": len(overdue), "reminders_sent": 0, "escalations": 0}

        for invoice in overdue:
            days_overdue = invoice.get("days_overdue", 0)
            client_email = invoice.get("client_email", "")

            # Draft and send reminder
            reminder = self.draft_reminder(invoice)
            send_result = await self.send_reminder(client_email, reminder)
            if send_result.get("sent"):
                results["reminders_sent"] += 1

            # Track in Hermes
            await self.track_response(invoice.get("id", ""), "reminder_sent")

            # Escalate if past escalation threshold with no response
            if days_overdue > self.escalation_days and not invoice.get("responded"):
                esc_result = await self.escalate_to_founder(invoice)
                if esc_result.get("escalated"):
                    results["escalations"] += 1

        return results


payment_monitor = PaymentMonitor()
