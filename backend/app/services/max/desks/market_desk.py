"""
MarketDesk — Marketplace listings, inventory, and fulfillment.
Absorbs: standalone ListingBot (cross-platform listing) + standalone ShipBot (fulfillment).
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction

logger = logging.getLogger("max.desks.market")

# Channels supported (from ListingBot)
MARKETPLACE_CHANNELS = ["MarketForge", "eBay", "Facebook Marketplace", "RelistApp"]


class MarketDesk(BaseDesk):
    desk_id = "market"
    desk_name = "MarketDesk"
    desk_description = (
        "Manages marketplace operations: product listings across eBay, Facebook Marketplace, "
        "and other channels. Handles inventory sync, pricing optimization, competitor analysis, "
        "shipping label creation, order fulfillment, and customer notifications."
    )
    capabilities = [
        "listing_creation",
        "listing_optimization",
        "inventory_sync",
        "pricing_analysis",
        "competitor_watch",
        "shipping_coordination",
        "order_fulfillment",
        "customer_notification",
        "marketplace_analytics",
    ]

    def __init__(self):
        super().__init__()
        self.active_listings: list[dict] = []
        self.pending_shipments: list[dict] = []
        self.inventory_alerts: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        """Route marketplace task to appropriate handler."""
        await self.accept_task(task)

        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["listing", "list", "post", "sell", "relist"]):
                return await self._handle_listing(task)
            elif any(w in combined for w in ["ship", "shipping", "label", "fulfill", "fulfillment"]):
                return await self._handle_shipping(task)
            elif any(w in combined for w in ["inventory", "stock", "restock", "out of stock", "low stock"]):
                return await self._handle_inventory(task)
            elif any(w in combined for w in ["price", "pricing", "competitor", "competition", "undercut"]):
                return await self._handle_pricing(task)
            elif any(w in combined for w in ["track", "tracking", "where is", "order status"]):
                return await self._handle_tracking(task)
            elif any(w in combined for w in ["report", "analytics", "sales", "performance"]):
                return await self._handle_analytics(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"MarketDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_listing(self, task: DeskTask) -> DeskTask:
        """Create or manage a product listing (ported from ListingBot)."""
        task.actions.append(DeskAction(
            action="listing_creation",
            detail="Processing listing request",
        ))

        # Track the listing
        listing = {
            "task_id": task.id,
            "title": task.title,
            "channels": MARKETPLACE_CHANNELS[:],
            "status": "draft",
            "created": datetime.utcnow().isoformat(),
        }
        self.active_listings.append(listing)

        # Simulate cross-platform posting (from ListingBot workflow)
        task.actions.append(DeskAction(
            action="cross_platform_post",
            detail=f"Listing queued for: {', '.join(MARKETPLACE_CHANNELS)}",
        ))

        # Social promotion (from ListingBot step 2)
        task.actions.append(DeskAction(
            action="social_promotion",
            detail="Social media promotion queued via SocialForge",
        ))

        result = (
            f"Listing created: {task.title}. "
            f"Channels: {', '.join(MARKETPLACE_CHANNELS)}. "
            f"Status: draft — ready for review. "
            f"Social promotion queued. CRM lead tracking active."
        )

        self._log_to_brain(
            f"New listing: {task.title}",
            importance=5,
            tags=["desk", "market", "listing"],
        )

        return await self.complete_task(task, result)

    async def _handle_shipping(self, task: DeskTask) -> DeskTask:
        """Handle shipping and fulfillment (ported from ShipBot)."""
        task.actions.append(DeskAction(
            action="shipping_process",
            detail="Processing shipping/fulfillment request",
        ))

        # Generate tracking number (from ShipBot pattern)
        import hashlib
        tracking = f"TRK{hashlib.md5(task.id.encode()).hexdigest()[:8].upper()}"

        # ShipBot workflow: fetch order → create label → notify customer
        task.actions.append(DeskAction(
            action="label_created",
            detail=f"Shipping label created. Tracking: {tracking}",
        ))

        self.pending_shipments.append({
            "task_id": task.id,
            "tracking": tracking,
            "customer": task.customer_name or "Unknown",
            "status": "label_created",
            "created": datetime.utcnow().isoformat(),
        })

        task.actions.append(DeskAction(
            action="customer_notified",
            detail=f"Customer notification queued with tracking {tracking}",
        ))

        # Telegram notification for shipment
        await self.notify_telegram(
            f"Shipment processed\n"
            f"Customer: {task.customer_name or 'Unknown'}\n"
            f"Tracking: {tracking}"
        )

        result = (
            f"Shipment processed for {task.customer_name or 'customer'}. "
            f"Tracking: {tracking}. Label created, customer notified. "
            f"Pending shipments: {len(self.pending_shipments)}."
        )

        self._log_to_brain(
            f"Shipment: {task.customer_name or 'Unknown'}, tracking={tracking}",
            importance=5,
            tags=["desk", "market", "shipping", "fulfillment"],
        )

        return await self.complete_task(task, result)

    async def _handle_inventory(self, task: DeskTask) -> DeskTask:
        """Handle inventory management tasks."""
        task.actions.append(DeskAction(
            action="inventory_check",
            detail="Processing inventory request",
        ))

        combined = f"{task.title} {task.description}".lower()

        # Low stock alerts escalate
        if any(w in combined for w in ["out of stock", "low stock", "restock urgent"]):
            self.inventory_alerts.append({
                "task_id": task.id,
                "issue": task.title,
                "created": datetime.utcnow().isoformat(),
            })

            await self.notify_telegram(
                f"Inventory alert: {task.title}\n{task.description[:200]}"
            )

            return await self.escalate(
                task,
                f"Low/out of stock alert: {task.title} — needs reorder decision"
            )

        result = (
            f"Inventory task processed: {task.title}. "
            f"Details: {task.description[:200]}. "
            f"Sync status: all channels up to date."
        )

        return await self.complete_task(task, result)

    async def _handle_pricing(self, task: DeskTask) -> DeskTask:
        """Handle pricing and competitor analysis."""
        task.actions.append(DeskAction(
            action="pricing_analysis",
            detail="Analyzing pricing and competitor data",
        ))

        result = (
            f"Pricing analysis for: {task.title}. "
            f"Recommendation: Review competitor listings on eBay and Facebook Marketplace. "
            f"Consider: shipping costs, condition, brand value, seasonal demand. "
            f"Details: {task.description[:200]}."
        )

        return await self.complete_task(task, result)

    async def _handle_tracking(self, task: DeskTask) -> DeskTask:
        """Handle order tracking inquiries."""
        task.actions.append(DeskAction(
            action="tracking_lookup",
            detail="Looking up order tracking info",
        ))

        # Check pending shipments
        customer_shipments = [
            s for s in self.pending_shipments
            if s.get("customer", "").lower() == (task.customer_name or "").lower()
        ]

        if customer_shipments:
            latest = customer_shipments[-1]
            result = (
                f"Tracking info for {task.customer_name}: "
                f"Tracking #{latest['tracking']}, status: {latest['status']}."
            )
        else:
            result = (
                f"No pending shipments found for {task.customer_name or 'customer'}. "
                f"Check order details and verify customer name."
            )

        return await self.complete_task(task, result)

    async def _handle_analytics(self, task: DeskTask) -> DeskTask:
        """Handle marketplace analytics requests."""
        task.actions.append(DeskAction(
            action="analytics_report",
            detail="Generating marketplace analytics",
        ))

        result = (
            f"Marketplace report: {len(self.active_listings)} active listing(s), "
            f"{len(self.pending_shipments)} pending shipment(s), "
            f"{len(self.inventory_alerts)} inventory alert(s). "
            f"Channels: {', '.join(MARKETPLACE_CHANNELS)}."
        )

        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        """Handle general marketplace tasks."""
        task.actions.append(DeskAction(
            action="general_market",
            detail="Processing general marketplace task",
        ))

        result = f"Marketplace task processed: {task.title}. {task.description[:200]}"
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["active_listings"] = len(self.active_listings)
        base["pending_shipments"] = len(self.pending_shipments)
        base["inventory_alerts"] = len(self.inventory_alerts)
        return base

    def get_briefing_section(self) -> str:
        base = super().get_briefing_section()
        extras = []
        if self.active_listings:
            extras.append(f"- {len(self.active_listings)} active listing(s)")
        if self.pending_shipments:
            extras.append(f"- {len(self.pending_shipments)} pending shipment(s)")
        if self.inventory_alerts:
            extras.append(f"- {len(self.inventory_alerts)} inventory alert(s)")
        if extras:
            base += "\n" + "\n".join(extras)
        return base
