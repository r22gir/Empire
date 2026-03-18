"""
Extract quote information from photos of handwritten field notes.
Uses Grok Vision API to read measurements, client info, and item specs.
"""
import os
import re
import json
import base64
import logging
from pathlib import Path
from difflib import SequenceMatcher

import httpx

from app.db.database import get_db, dict_row, dict_rows

log = logging.getLogger("notes_extractor")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
VISION_MODEL = "grok-4-fast-non-reasoning"

EXTRACTION_PROMPT = """You are analyzing a professional workroom technician's handwritten field notes
from a client site visit. These notes contain measurement data, client information,
and project specifications for custom drapery, upholstery, or window treatments.

Extract ALL information you can find and return ONLY valid JSON (no markdown,
no explanation, no preamble):

{
  "customer": {
    "name": "string or null",
    "phone": "string or null",
    "email": "string or null",
    "address": "string or null"
  },
  "project": {
    "location": "string — room name or description",
    "date": "string or null — if a date is written",
    "general_notes": "string — any overall project notes"
  },
  "items": [
    {
      "room": "string — which room this item is in",
      "type": "drapery|upholstery|cushions|pillows|cornices|valance|roman_shade|other",
      "subtype": "string — pinch_pleat, rod_pocket, grommet, tab_top, etc. or null",
      "description": "string — full description of the item",
      "measurements": {
        "width_inches": null,
        "height_inches": null,
        "depth_inches": null,
        "additional": {}
      },
      "fabric": {
        "name": "string or null — fabric name if specified",
        "color": "string or null",
        "notes": "string — any fabric notes"
      },
      "hardware": "string or null — rod type, rings, brackets, etc.",
      "quantity": 1,
      "lining": "string or null — blackout, thermal, standard, none",
      "price_noted": null,
      "special_instructions": "string or null",
      "confidence": 0.85
    }
  ],
  "sketches_detected": false,
  "handwriting_quality": "clear|readable|difficult|partial",
  "pages_analyzed": 1
}

IMPORTANT:
- Extract EVERY measurement you can find, even partial ones
- If you see "72x36" interpret as width 72 inches x height 36 inches
- Common abbreviations: PP=pinch pleat, RP=rod pocket, BL=blackout,
  BO=blackout, ROM=roman shade, FAB=fabric, HW=hardware, INST=installation,
  LR=living room, BR=bedroom, DR=dining room, MBR=master bedroom,
  KIT=kitchen, BAT=bathroom, OFF=office, DEN=den
- If unsure about a value, include it with lower confidence
- Numbers near sketches are likely measurements in inches
- Dollar amounts are prices
- Names at the top of a page are likely the client
- Return ONLY the JSON object, nothing else"""


class NotesExtractor:
    """Extract quote information from photos of handwritten field notes."""

    async def extract_from_photos(self, photo_paths: list[str]) -> dict:
        """
        Send each photo to Grok Vision API.
        Merge results across all photos.
        Match against existing DB records.
        Return structured draft quote data.
        """
        if not XAI_API_KEY:
            return {"error": "XAI_API_KEY not configured", "items": []}

        extractions = []
        for path in photo_paths:
            try:
                result = await self._extract_single(path)
                extractions.append(result)
            except Exception as e:
                log.error(f"Extraction failed for {path}: {e}")
                extractions.append({"error": str(e), "items": []})

        # Merge all extractions
        merged = self._merge_extractions(extractions)

        # Match against DB
        merged["customer_match"] = await self.match_customer(
            merged.get("customer", {}).get("name"),
            merged.get("customer", {}).get("phone"),
        )
        merged["inventory_matches"] = []
        for item in merged.get("items", []):
            fabric_name = (item.get("fabric") or {}).get("name")
            if fabric_name:
                match = await self.match_inventory(fabric_name)
                if match:
                    item["fabric_match"] = match
                    merged["inventory_matches"].append(match)

        merged["pages_analyzed"] = len(photo_paths)
        return merged

    async def _extract_single(self, photo_path: str) -> dict:
        """Extract from a single photo via Grok Vision."""
        # Read and encode image
        img_path = Path(photo_path)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {photo_path}")

        with open(img_path, "rb") as f:
            img_bytes = f.read()

        # Detect mime type from magic bytes
        if img_bytes[:3] == b'\xff\xd8\xff':
            mime = "image/jpeg"
        elif img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            mime = "image/png"
        elif img_bytes[:4] == b'RIFF' and img_bytes[8:12] == b'WEBP':
            mime = "image/webp"
        else:
            mime = "image/jpeg"  # fallback

        b64 = base64.b64encode(img_bytes).decode()
        image_url = f"data:{mime};base64,{b64}"

        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": VISION_MODEL,
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ]}],
                    "max_tokens": 6000,
                    "temperature": 0.2,
                },
            )

        if res.status_code != 200:
            raise RuntimeError(f"Vision API error {res.status_code}: {res.text[:300]}")

        content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        m = re.search(r"\{[\s\S]*\}", content)
        if not m:
            raise RuntimeError(f"Could not parse JSON from vision response")

        return json.loads(m.group(0))

    def _merge_extractions(self, extractions: list[dict]) -> dict:
        """Merge results from multiple photo extractions."""
        if not extractions:
            return {"customer": {}, "project": {}, "items": []}

        if len(extractions) == 1:
            return extractions[0]

        # Start with first extraction as base
        merged = {
            "customer": {},
            "project": {"general_notes": ""},
            "items": [],
            "sketches_detected": False,
            "handwriting_quality": "readable",
        }

        best_customer = {}
        best_customer_confidence = 0

        for ext in extractions:
            if "error" in ext:
                continue

            # Merge customer — take the most complete one
            cust = ext.get("customer", {})
            filled = sum(1 for v in cust.values() if v)
            if filled > best_customer_confidence:
                best_customer = cust
                best_customer_confidence = filled

            # Merge project notes
            proj = ext.get("project", {})
            if proj.get("location") and not merged["project"].get("location"):
                merged["project"]["location"] = proj["location"]
            if proj.get("date") and not merged["project"].get("date"):
                merged["project"]["date"] = proj["date"]
            if proj.get("general_notes"):
                if merged["project"]["general_notes"]:
                    merged["project"]["general_notes"] += "; "
                merged["project"]["general_notes"] += proj["general_notes"]

            # Collect items
            for item in ext.get("items", []):
                # Dedup: check if same room + type + similar measurements already exists
                duplicate = False
                for existing in merged["items"]:
                    if (existing.get("room", "").lower() == item.get("room", "").lower()
                            and existing.get("type") == item.get("type")):
                        e_m = existing.get("measurements", {})
                        i_m = item.get("measurements", {})
                        if (e_m.get("width_inches") == i_m.get("width_inches")
                                and e_m.get("height_inches") == i_m.get("height_inches")):
                            # Same item — keep higher confidence
                            if item.get("confidence", 0) > existing.get("confidence", 0):
                                existing.update(item)
                            duplicate = True
                            break
                if not duplicate:
                    merged["items"].append(item)

            if ext.get("sketches_detected"):
                merged["sketches_detected"] = True

        merged["customer"] = best_customer
        return merged

    async def match_customer(self, name: str | None, phone: str | None) -> dict | None:
        """Match extracted customer against empire.db customers table."""
        if not name and not phone:
            return None

        with get_db() as conn:
            # Try exact phone match first
            if phone:
                clean_phone = re.sub(r'[^\d]', '', phone)
                if len(clean_phone) >= 7:
                    rows = conn.execute(
                        "SELECT id, name, email, phone, address FROM customers"
                    ).fetchall()
                    for row in rows:
                        db_phone = re.sub(r'[^\d]', '', row["phone"] or "")
                        if db_phone and (clean_phone in db_phone or db_phone in clean_phone):
                            return {
                                "matched_id": row["id"],
                                "matched_name": row["name"],
                                "matched_email": row["email"],
                                "matched_phone": row["phone"],
                                "matched_address": row["address"],
                                "match_type": "phone",
                                "confidence": 0.95,
                            }

            # Fuzzy name match
            if name:
                rows = conn.execute(
                    "SELECT id, name, email, phone, address FROM customers"
                ).fetchall()
                best_match = None
                best_ratio = 0.0
                name_lower = name.lower().strip()

                for row in rows:
                    db_name = (row["name"] or "").lower().strip()
                    if not db_name:
                        continue

                    # Exact substring
                    if name_lower in db_name or db_name in name_lower:
                        ratio = 0.90
                    else:
                        ratio = SequenceMatcher(None, name_lower, db_name).ratio()

                    if ratio > best_ratio and ratio >= 0.55:
                        best_ratio = ratio
                        best_match = row

                if best_match:
                    return {
                        "matched_id": best_match["id"],
                        "matched_name": best_match["name"],
                        "matched_email": best_match["email"],
                        "matched_phone": best_match["phone"],
                        "matched_address": best_match["address"],
                        "match_type": "name_fuzzy",
                        "confidence": round(best_ratio, 2),
                    }

        return None

    async def match_inventory(self, fabric_name: str) -> dict | None:
        """Match extracted fabric against inventory_items table."""
        if not fabric_name:
            return None

        fabric_lower = fabric_name.lower().strip()

        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, name, sku, category, quantity, unit, cost_per_unit, sell_price "
                "FROM inventory_items WHERE category = 'fabric'"
            ).fetchall()

            best_match = None
            best_ratio = 0.0

            for row in rows:
                db_name = (row["name"] or "").lower().strip()
                if not db_name:
                    continue

                # Exact substring match
                if fabric_lower in db_name or db_name in fabric_lower:
                    ratio = 0.90
                else:
                    ratio = SequenceMatcher(None, fabric_lower, db_name).ratio()

                if ratio > best_ratio and ratio >= 0.50:
                    best_ratio = ratio
                    best_match = row

            if best_match:
                return {
                    "matched_id": best_match["id"],
                    "item_name": best_match["name"],
                    "sku": best_match["sku"],
                    "price": best_match["sell_price"] or best_match["cost_per_unit"],
                    "quantity_in_stock": best_match["quantity"],
                    "unit": best_match["unit"],
                    "confidence": round(best_ratio, 2),
                }

        return None


# Singleton
notes_extractor = NotesExtractor()
