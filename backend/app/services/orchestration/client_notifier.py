"""
Client Notifier — Job stage changes trigger personalized updates
Webhook: /workroom/jobs/:id/stage
"""
import logging
from datetime import datetime
import httpx

logger = logging.getLogger("client_notifier")

API = "http://localhost:8000/api/v1"

STAGE_MESSAGES = {
    "quote_sent": {
        "subject": "Your proposal is ready! 🎨",
        "body": "Hi {client_name},\n\nYour custom drapery proposal is ready for review! Check out your options at the link below.\n\nQuestions? Reply to this email — we're happy to help!\n\n— Empire Workroom",
        "include_link": True,
    },
    "approved": {
        "subject": "Great news! We're moving forward 🎉",
        "body": "Hi {client_name},\n\nYour order is confirmed! We're excited to get started on your {product}.\n\nWe'll keep you updated as things progress. Sit back and relax — we've got this!\n\n— Empire Workroom",
        "include_link": True,
    },
    "in_production": {
        "subject": "Your order is being crafted! 🔨",
        "body": "Hi {client_name},\n\nGreat progress — your {product} is now being crafted!\n\nCurrent status: {stage}\nEstimated completion: {deadline}\n\nWe'll send photos as we go!\n\n— Empire Workroom",
        "include_link": True,
    },
    "complete": {
        "subject": "Your order is ready for pickup! 🎊",
        "body": "Hi {client_name},\n\nYour {product} is ready! 🥳\n\nPickup/shipping details: [link]\n\nThank you for choosing Empire Workroom!\n\n— Empire Workroom",
        "include_link": True,
    },
}


class ClientNotifier:
    def __init__(self):
        self.stage_templates = STAGE_MESSAGES

    async def on_job_stage_change(self, job_id: str, new_stage: str, old_stage: str = None) -> dict:
        """Triggered when a job changes stage. Sends client notification."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{API}/workroom/jobs/{job_id}")
                if not r.ok:
                    return {"sent": False, "error": "job not found"}
                job = r.json()
        except Exception as e:
            logger.warning(f"Failed to fetch job {job_id}: {e}")
            return {"sent": False, "error": str(e)}

        template = self.stage_templates.get(new_stage, {})
        if not template:
            return {"sent": False, "error": "no template for stage"}

        client_name = job.get("client_name", "there")
        product = job.get("product", "your order")
        client_email = job.get("client_email", "")

        if not client_email:
            return {"sent": False, "error": "no client email"}

        # Build message
        body = template["body"].format(
            client_name=client_name,
            product=product,
            stage=new_stage.replace("_", " ").title(),
            deadline=job.get("estimated_completion", "TBD"),
        )

        # Attach progress photo if available
        photo_url = await self.attach_progress_photo(job_id)

        # Send to client
        send_result = await self.send_to_client(client_email, template["subject"], body, photo_url)

        # Log to Hermes
        await self.log_communication(job_id, new_stage, body, send_result.get("sent", False))

        return send_result

    async def draft_status_update(self, job: dict, stage: str) -> dict:
        """Draft a personalized status update message."""
        template = self.stage_templates.get(stage, {})
        if not template:
            return {}

        return {
            "subject": template["subject"].format(client_name=job.get("client_name", "")),
            "body": template["body"].format(
                client_name=job.get("client_name", ""),
                product=job.get("product", "your order"),
                stage=stage.replace("_", " ").title(),
                deadline=job.get("estimated_completion", "TBD"),
            ),
        }

    async def attach_progress_photo(self, job_id: str) -> str:
        """Attach latest progress photo from Drawing Studio."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{API}/drawings/latest", params={"job_id": job_id})
                if r.ok:
                    data = r.json()
                    return data.get("photo_url", "")
        except Exception as e:
            logger.warning(f"Progress photo fetch failed: {e}")
        return ""

    async def send_to_client(self, client_email: str, subject: str, body: str, photo_url: str = None) -> dict:
        """Send message to client via email."""
        if not client_email:
            return {"sent": False}

        payload = {
            "to": client_email,
            "subject": subject,
            "body": body,
        }
        if photo_url:
            payload["attachment_url"] = photo_url

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(f"{API}/socialforge/send_email", json=payload)
                return {"sent": r.ok, "channel": "email"}
        except Exception as e:
            logger.warning(f"Client email failed: {e}")
            return {"sent": False}

    async def log_communication(self, job_id: str, stage: str, message: str, sent: bool):
        """Log communication to Hermes memory."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{API}/hermes/log_communication",
                    json={
                        "event": "client_notification",
                        "job_id": job_id,
                        "stage": stage,
                        "message": message[:200],
                        "sent": sent,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.warning(f"Hermes logging failed: {e}")


client_notifier = ClientNotifier()
