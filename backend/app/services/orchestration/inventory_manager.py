"""
Inventory Manager — Auto-reorder low stock materials
Runs daily 9 AM, generates POs, sends approval requests.
"""
import logging
from datetime import datetime
import httpx

logger = logging.getLogger("inventory")

API = "http://localhost:8000/api/v1"


class InventoryManager:
    def __init__(self):
        self.reorder_threshold_factor = 0.3  # reorder when stock < 30% of capacity

    async def check_stock_levels(self) -> dict:
        """Get current inventory levels for all materials."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{API}/inventory/levels")
                if r.ok:
                    return r.json()
        except Exception as e:
            logger.warning(f"Stock check failed: {e}")
        return {}

    def identify_low_stock(self, inventory: dict) -> list[dict]:
        """Identify materials below threshold."""
        low_stock = []
        materials = inventory.get("materials", inventory.get("data", []))

        for mat in materials:
            current = mat.get("current", 0)
            capacity = mat.get("capacity", 100)
            threshold = int(capacity * self.reorder_threshold_factor)

            if current <= threshold:
                mat["threshold"] = threshold
                mat["shortage"] = threshold - current
                low_stock.append(mat)

        return low_stock

    async def find_active_jobs_needing(self, material: str) -> list[dict]:
        """Find active jobs that need a specific material."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{API}/workroom/jobs", params={"material": material, "status": "active"})
                if r.ok:
                    data = r.json()
                    return data.get("jobs", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.warning(f"Active jobs lookup failed: {e}")
        return []

    def generate_po(self, material: dict, quantity: int, supplier: str = "DEFAULT_SUPPLIER") -> dict:
        """Generate a Purchase Order document."""
        po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d')}-{material.get('id', '000')}"

        return {
            "po_number": po_number,
            "supplier": supplier,
            "material_id": material.get("id"),
            "material_name": material.get("name"),
            "quantity": quantity,
            "unit": material.get("unit", "units"),
            "estimated_cost": material.get("unit_cost", 0) * quantity,
            "status": "pending_approval",
            "created_at": datetime.utcnow().isoformat(),
        }

    async def send_for_approval(self, po: dict, founder_chat_id: str = None) -> dict:
        """Send PO to founder via Telegram for approval."""
        message = f"""[PURCHASE ORDER] — Approval Required

PO#: {po['po_number']}
Material: {po['material_name']}
Quantity: {po['quantity']} {po['unit']}
Estimated Cost: ${po['estimated_cost']:,.2f}

Reply YES to approve or NO to cancel."""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{API}/notifications/telegram",
                    json={
                        "message": message,
                        "priority": "normal",
                        "approval_request": True,
                        "po_number": po["po_number"],
                    },
                )
                return {"approval_requested": r.ok, "po": po}
        except Exception as e:
            logger.warning(f"Approval request failed: {e}")
            return {"approval_requested": False, "po": po}

    async def email_supplier(self, po: dict) -> dict:
        """Email PO to supplier via VendorOps."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(
                    f"{API}/vendorops/send_po",
                    json={
                        "po_number": po["po_number"],
                        "supplier": po.get("supplier"),
                        "material": po.get("material_name"),
                        "quantity": po["quantity"],
                    },
                )
                return {"sent": r.ok}
        except Exception as e:
            logger.warning(f"Supplier email failed: {e}")
            return {"sent": False}

    async def update_inventory_on_arrival(self, shipment_id: str, material_id: str, quantity: int) -> dict:
        """Update inventory when shipment arrives."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.patch(
                    f"{API}/inventory/update",
                    json={
                        "shipment_id": shipment_id,
                        "material_id": material_id,
                        "quantity_received": quantity,
                    },
                )
                return {"updated": r.ok}
        except Exception as e:
            logger.warning(f"Inventory update failed: {e}")
            return {"updated": False}

    async def run_daily_check(self) -> dict:
        """Daily inventory check and reorder workflow."""
        inventory = await self.check_stock_levels()
        low_stock = self.identify_low_stock(inventory)

        results = {
            "materials_checked": len(inventory.get("materials", [])),
            "low_stock_count": len(low_stock),
            "pos_generated": 0,
            "approvals_requested": 0,
        }

        for mat in low_stock:
            # Find active jobs needing this material
            jobs_affected = await self.find_active_jobs_needing(mat.get("id"))

            # Calculate reorder quantity (enough for 2 weeks + buffer)
            needed = max(mat.get("shortage", 0), int(mat.get("capacity", 100) * 0.5))

            if needed > 0:
                po = self.generate_po(mat, needed)
                results["pos_generated"] += 1

                # Send for founder approval
                approval = await self.send_for_approval(po)
                if approval.get("approval_requested"):
                    results["approvals_requested"] += 1

        return results


inventory_manager = InventoryManager()
