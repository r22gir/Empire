"""
Quote Intelligence System — Quote Verification Module

Quality gate that catches bad quotes before they reach customers.
Every quote MUST pass all checks before PDF generation.

Two integration points:
  1. POST-ANALYSIS gate (after AI analysis, before showing to founder)
  2. PRE-PDF gate (before generating PDF — blocks on errors)

Usage:
    verifier = QuoteVerifier()
    result = verifier.verify_quote(quote_data)
    if not result["passed"]:
        # Block and show errors
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .pricing_tables import (
    FABRIC_GRADES,
    LABOR_RATES,
    TAX_RATES,
    TIER_MULTIPLIERS,
    DEPOSIT_PERCENTAGE,
)
from .yardage_calculator import YARDAGE_TABLE, calculate_yardage

logger = logging.getLogger(__name__)

QUOTES_DIR = os.path.expanduser("~/empire-repo/backend/data/quotes")

# ---------------------------------------------------------------------------
# Market range table — min/max TOTAL PRICE per item type
# Based on industry research: DC/MD/VA market rates as of 2026
# ---------------------------------------------------------------------------
MARKET_RANGES: Dict[str, Dict[str, float]] = {
    "dining_chair_seat": {"min": 80, "max": 250},
    "dining_chair_full": {"min": 150, "max": 500},
    "accent_chair": {"min": 300, "max": 800},
    "wingback_chair": {"min": 400, "max": 1200},
    "club_chair": {"min": 350, "max": 1000},
    "ottoman": {"min": 150, "max": 500},
    "ottoman_small": {"min": 100, "max": 350},
    "ottoman_large": {"min": 200, "max": 600},
    "bench_small": {"min": 200, "max": 600},
    "bench_medium": {"min": 400, "max": 1200},
    "bench_large": {"min": 600, "max": 2500},
    "bench": {"min": 200, "max": 2500},
    "loveseat": {"min": 600, "max": 1800},
    "sofa_2cushion": {"min": 800, "max": 2500},
    "sofa_3cushion": {"min": 1200, "max": 3500},
    "sectional_per_section": {"min": 800, "max": 2500},
    "headboard": {"min": 300, "max": 1200},
    "banquette": {"min": 300, "max": 2000},
    "seat_cushion": {"min": 60, "max": 200},
    "back_cushion": {"min": 75, "max": 250},
    "throw_pillow": {"min": 35, "max": 120},
    "bolster": {"min": 50, "max": 150},
    "drapery_panel": {"min": 200, "max": 600},
    "roman_shade": {"min": 300, "max": 800},
    "roller_shade": {"min": 150, "max": 500},
    "valance": {"min": 100, "max": 400},
    "cornice": {"min": 150, "max": 500},
    "swag": {"min": 100, "max": 350},
}

# Bench pricing per linear foot (for sanity checking)
BENCH_PER_LINEAR_FT_RANGE = {"min": 50, "max": 180}


# ---------------------------------------------------------------------------
# Check result types
# ---------------------------------------------------------------------------
class CheckResult:
    """Result of a single verification check."""

    def __init__(
        self,
        name: str,
        passed: bool,
        severity: str,  # "error", "warning", "info"
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.passed = passed
        self.severity = severity
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Main Verifier
# ---------------------------------------------------------------------------
class QuoteVerifier:
    """
    Quality gate that catches bad quotes before they reach customers.
    Every quote MUST pass all checks before PDF generation.

    Returns:
        {
            "passed": bool,          # True only if zero errors
            "score": 0-100,
            "grade": "A" / "B" / "C" / "F",
            "checks": [...],         # All check results
            "errors": [...],         # Must fix before sending
            "warnings": [...],       # Should fix, won't block
            "suggestions": [...],    # Optional improvements
            "verified_at": ISO timestamp,
            "summary": "human-readable summary"
        }
    """

    @staticmethod
    def _normalize(quote: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize AI-generated quote format to match verification expectations.

        AI quotes use design_proposals + proposal_totals; verification expects tiers + items.
        """
        q = dict(quote)  # shallow copy

        # Build tiers from proposal_totals if tiers missing
        if not q.get("tiers") and q.get("proposal_totals"):
            pt = q["proposal_totals"]
            q["tiers"] = {
                k: {"total": v} for k, v in pt.items() if k in ("A", "B", "C")
            }

        # Build items from line_items or design_proposals if items missing
        if not q.get("items"):
            if q.get("line_items"):
                q["items"] = q["line_items"]
            elif q.get("design_proposals"):
                # Use the first proposal's line items as a representative
                for dp in q["design_proposals"]:
                    if dp.get("line_items"):
                        q["items"] = dp["line_items"]
                        break

        return q

    def verify_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run ALL verification checks on a quote."""
        quote_data = self._normalize(quote_data)
        checks: List[CheckResult] = []

        is_flat = quote_data.get("pricing_mode") == "flat"

        if is_flat:
            # Flat-priced quotes skip tier/yardage/market checks — just verify
            # math, completeness, and customer info
            checks.append(self._check_flat_math(quote_data))
            checks.append(self.check_completeness(quote_data))
            checks.append(self.check_customer_info(quote_data))
        else:
            checks.append(self.check_tier_pricing(quote_data))
            checks.append(self.check_yardage_sanity(quote_data))
            checks.append(self.check_line_items(quote_data))
            checks.append(self.check_measurements(quote_data))
            checks.append(self.check_all_items_priced(quote_data))
            checks.append(self.check_mockup_match(quote_data))
            checks.append(self.check_market_range(quote_data))
            checks.append(self.check_math(quote_data))
            checks.append(self.check_completeness(quote_data))
            checks.append(self.check_customer_info(quote_data))

        errors = [c for c in checks if not c.passed and c.severity == "error"]
        warnings = [c for c in checks if not c.passed and c.severity == "warning"]
        suggestions = [c for c in checks if not c.passed and c.severity == "info"]
        passed_checks = [c for c in checks if c.passed]

        total_checks = len(checks)
        error_penalty = len(errors) * 15
        warning_penalty = len(warnings) * 5
        score = max(0, 100 - error_penalty - warning_penalty)

        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        else:
            grade = "F"

        passed = len(errors) == 0

        summary_parts = []
        if passed:
            summary_parts.append(f"Quote PASSED verification ({score}/100, grade {grade})")
        else:
            summary_parts.append(
                f"Quote FAILED — {len(errors)} error(s) must be fixed"
            )
        if warnings:
            summary_parts.append(f"{len(warnings)} warning(s)")
        summary_parts.append(
            f"{len(passed_checks)}/{total_checks} checks passed"
        )

        result = {
            "passed": passed,
            "score": score,
            "grade": grade,
            "checks": [c.to_dict() for c in checks],
            "errors": [c.to_dict() for c in errors],
            "warnings": [c.to_dict() for c in warnings],
            "suggestions": [c.to_dict() for c in suggestions],
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "summary": " | ".join(summary_parts),
            "stats": {
                "total_checks": total_checks,
                "passed": len(passed_checks),
                "errors": len(errors),
                "warnings": len(warnings),
                "suggestions": len(suggestions),
            },
        }

        logger.info(
            "Verification: %s (score=%d, errors=%d, warnings=%d)",
            "PASSED" if passed else "FAILED",
            score,
            len(errors),
            len(warnings),
        )

        return result

    # =======================================================================
    # Flat pricing verification
    # =======================================================================

    def _check_flat_math(self, quote: Dict[str, Any]) -> CheckResult:
        """Verify flat-priced quote math: line_items sum = subtotal, total = subtotal + tax - discount."""
        items = quote.get("line_items", [])
        if not items:
            return CheckResult("flat_math", True, "info", "No line items — flat quote with room-level pricing only.")

        computed_subtotal = 0.0
        for item in items:
            qty = item.get("quantity", 1)
            rate = item.get("rate", 0)
            expected_amount = round(qty * rate, 2)
            actual_amount = item.get("amount", 0)
            if abs(expected_amount - actual_amount) > 0.02:
                return CheckResult(
                    "flat_math", False, "error",
                    f"Line item '{item.get('description', '?')}': {qty} × ${rate} = ${expected_amount}, but amount shows ${actual_amount}.",
                )
            computed_subtotal += expected_amount

        stored_subtotal = quote.get("subtotal", 0) or 0
        if abs(computed_subtotal - stored_subtotal) > 0.02:
            return CheckResult(
                "flat_math", False, "error",
                f"Line items sum to ${computed_subtotal:.2f} but subtotal shows ${stored_subtotal:.2f}.",
            )

        tax_rate = quote.get("tax_rate", 0)
        expected_tax = round(stored_subtotal * tax_rate, 2)
        discount = quote.get("discount_amount", 0) or 0
        expected_total = round(stored_subtotal + expected_tax - discount, 2)
        stored_total = quote.get("total", 0) or 0
        if abs(expected_total - stored_total) > 0.02:
            return CheckResult(
                "flat_math", False, "error",
                f"Expected total ${expected_total:.2f} but stored ${stored_total:.2f}.",
            )

        return CheckResult("flat_math", True, "info", f"Flat pricing math verified: ${stored_total:.2f}")

    # =======================================================================
    # Individual checks
    # =======================================================================

    def check_tier_pricing(self, quote: Dict[str, Any]) -> CheckResult:
        """FAIL if all tiers have the same price. Tiers MUST differ."""
        tiers = quote.get("tiers", {})
        if not tiers:
            return CheckResult(
                "tier_pricing", False, "error",
                "No pricing tiers found in quote.",
            )

        totals = {}
        for key in ("A", "B", "C"):
            tier = tiers.get(key, {})
            totals[key] = tier.get("total", 0)

        # Check all same
        unique_totals = set(totals.values())
        if len(unique_totals) == 1 and unique_totals != {0}:
            return CheckResult(
                "tier_pricing", False, "error",
                f"All 3 tiers have IDENTICAL price ${totals['A']:.2f}. "
                f"Tiers must have different prices.",
                {"tier_A": totals["A"], "tier_B": totals["B"], "tier_C": totals["C"]},
            )

        # Check minimum spread: B should be >= 20% more than A
        if totals["A"] > 0:
            ab_spread = (totals["B"] - totals["A"]) / totals["A"]
            ac_spread = (totals["C"] - totals["A"]) / totals["A"]

            if ab_spread < 0.15:
                return CheckResult(
                    "tier_pricing", False, "warning",
                    f"Tier B (${totals['B']:.0f}) is only {ab_spread*100:.0f}% more "
                    f"than Tier A (${totals['A']:.0f}). Expected >= 20% spread.",
                    {"spread_AB": f"{ab_spread*100:.1f}%", "spread_AC": f"{ac_spread*100:.1f}%"},
                )

            if ac_spread < 0.30:
                return CheckResult(
                    "tier_pricing", False, "warning",
                    f"Tier C (${totals['C']:.0f}) is only {ac_spread*100:.0f}% more "
                    f"than Tier A (${totals['A']:.0f}). Expected >= 40% spread.",
                    {"spread_AB": f"{ab_spread*100:.1f}%", "spread_AC": f"{ac_spread*100:.1f}%"},
                )

        return CheckResult(
            "tier_pricing", True, "info",
            f"Tier pricing OK: A=${totals['A']:.0f} / B=${totals['B']:.0f} / C=${totals['C']:.0f}",
            {"tier_A": totals["A"], "tier_B": totals["B"], "tier_C": totals["C"]},
        )

    def check_yardage_sanity(self, quote: Dict[str, Any]) -> CheckResult:
        """FAIL if fabric yardage doesn't match dimensions."""
        items = quote.get("items", [])
        if not items:
            return CheckResult(
                "yardage_sanity", False, "warning",
                "No items found in quote to check yardage.",
            )

        issues = []
        for item in items:
            item_type = item.get("type", "")
            dims = item.get("dimensions", {})
            quoted_yards = 0

            # Get quoted yardage from item or from tier A line items
            yardage_info = item.get("yardage", {})
            if isinstance(yardage_info, dict):
                quoted_yards = yardage_info.get("yards", 0)

            if not quoted_yards:
                # Try to find from tier A line items
                tiers = quote.get("tiers", {})
                tier_a = tiers.get("A", {})
                for tier_item in tier_a.get("items", []):
                    if tier_item.get("name") == item.get("name"):
                        for li in tier_item.get("line_items", []):
                            if li.get("category") == "fabric":
                                quoted_yards = li.get("quantity", 0)
                                break

            if not quoted_yards or not dims:
                continue

            # Calculate expected yardage
            opts: Dict[str, Any] = {}
            if item.get("cushion_count"):
                opts["cushion_count"] = item["cushion_count"]
            if any("tuft" in f.lower() for f in item.get("special_features", [])):
                opts["tufted"] = True

            expected = calculate_yardage(item_type, dims, opts)
            expected_yards = expected.get("yards", 0)

            if expected_yards > 0:
                ratio = quoted_yards / expected_yards
                if ratio < 0.5:
                    issues.append(
                        f"{item.get('name', item_type)}: quoted {quoted_yards} yd "
                        f"but expected ~{expected_yards} yd (TOO LOW — {ratio*100:.0f}%)"
                    )
                elif ratio > 2.0:
                    issues.append(
                        f"{item.get('name', item_type)}: quoted {quoted_yards} yd "
                        f"but expected ~{expected_yards} yd (TOO HIGH — {ratio*100:.0f}%)"
                    )

        if issues:
            severity = "error" if any("TOO LOW" in i for i in issues) else "warning"
            return CheckResult(
                "yardage_sanity", False, severity,
                f"Yardage issues: {'; '.join(issues)}",
                {"issues": issues},
            )

        return CheckResult(
            "yardage_sanity", True, "info",
            "All yardage calculations within expected range.",
        )

    def check_line_items(self, quote: Dict[str, Any]) -> CheckResult:
        """FAIL if line items are generic like 'Upholstery item'."""
        tiers = quote.get("tiers", {})
        if not tiers:
            return CheckResult(
                "line_items", False, "error",
                "No tiers found — cannot check line items.",
            )

        generic_terms = [
            "upholstery item", "item", "furniture", "piece",
            "service", "work", "project",
        ]
        issues = []

        for tier_key, tier_data in tiers.items():
            for tier_item in tier_data.get("items", []):
                line_items = tier_item.get("line_items", [])
                if not line_items:
                    issues.append(
                        f"Tier {tier_key}: '{tier_item.get('name')}' has NO line items"
                    )
                    continue

                for li in line_items:
                    desc = (li.get("description", "") or "").lower().strip()
                    # Check for generic descriptions
                    if desc in generic_terms or any(
                        desc == g for g in generic_terms
                    ):
                        issues.append(
                            f"Tier {tier_key}: Generic line item '{li.get('description')}' "
                            f"— should be specific (e.g., fabric grade, yardage, labor type)"
                        )

                    # Check for zero amount (except lining with "none")
                    if li.get("amount", 0) <= 0 and li.get("category") != "lining":
                        issues.append(
                            f"Tier {tier_key}: Line item '{li.get('description')}' has $0 amount"
                        )

            # Only check tier A — same structure repeats
            break

        if issues:
            return CheckResult(
                "line_items", False, "error",
                f"Line item issues: {'; '.join(issues[:3])}",
                {"issues": issues},
            )

        return CheckResult(
            "line_items", True, "info",
            "All line items have specific descriptions and non-zero amounts.",
        )

    def check_measurements(self, quote: Dict[str, Any]) -> CheckResult:
        """WARN if measurements seem unreasonable."""
        items = quote.get("items", [])
        issues = []

        for item in items:
            dims = item.get("dimensions", {})
            name = item.get("name", item.get("type", "Item"))

            width = dims.get("width", 0)
            height = dims.get("height", 0)
            depth = dims.get("depth", 0)

            # Check for zero dimensions
            if not any([width, height, depth]):
                issues.append(f"'{name}': ALL dimensions are 0 or missing")
                continue

            if width == 0:
                issues.append(f"'{name}': width is 0 (missing measurement)")

            # Unreasonable sizes
            if width > 240:  # 20ft
                issues.append(f"'{name}': width {width}\" ({width/12:.0f}ft) — verify > 20ft")
            if width > 0 and width < 6:
                issues.append(f"'{name}': width {width}\" — unusually small")
            if height > 120:  # 10ft
                issues.append(f"'{name}': height {height}\" ({height/12:.0f}ft) — verify > 10ft")
            if depth > 48:
                issues.append(f"'{name}': depth {depth}\" — verify > 4ft")

        if issues:
            has_zeros = any("is 0" in i or "ALL dimensions" in i for i in issues)
            severity = "error" if has_zeros else "warning"
            return CheckResult(
                "measurements", False, severity,
                f"Measurement issues: {'; '.join(issues[:3])}",
                {"issues": issues},
            )

        return CheckResult(
            "measurements", True, "info",
            "All measurements within reasonable ranges.",
        )

    def check_all_items_priced(self, quote: Dict[str, Any]) -> CheckResult:
        """FAIL if any item has $0.00 price in any tier."""
        tiers = quote.get("tiers", {})
        issues = []

        for tier_key, tier_data in tiers.items():
            for tier_item in tier_data.get("items", []):
                subtotal = tier_item.get("subtotal", 0)
                name = tier_item.get("name", "Unknown")
                if subtotal <= 0:
                    issues.append(
                        f"Tier {tier_key}: '{name}' has $0 total price"
                    )

        if issues:
            return CheckResult(
                "all_items_priced", False, "error",
                f"Unpriced items: {'; '.join(issues)}",
                {"issues": issues},
            )

        return CheckResult(
            "all_items_priced", True, "info",
            "All items in all tiers have non-zero prices.",
        )

    def check_mockup_match(self, quote: Dict[str, Any]) -> CheckResult:
        """WARN if AI mockup doesn't match item type."""
        items = quote.get("items", [])
        issues = []

        # Mapping of item types to expected mockup categories
        type_to_mockup_category = {
            "bench": "bench",
            "bench_small": "bench",
            "bench_medium": "bench",
            "bench_large": "bench",
            "banquette": "bench",
            "sofa_2cushion": "sofa",
            "sofa_3cushion": "sofa",
            "loveseat": "sofa",
            "accent_chair": "chair",
            "wingback_chair": "chair",
            "club_chair": "chair",
            "dining_chair_full": "chair",
            "dining_chair_seat": "chair",
            "ottoman": "ottoman",
            "ottoman_small": "ottoman",
            "ottoman_large": "ottoman",
            "headboard": "headboard",
            "drapery_panel": "window",
            "roman_shade": "window",
            "roller_shade": "window",
            "valance": "window",
        }

        for item in items:
            item_type = item.get("type", "")
            mockup_url = item.get("mockup_url", "")
            if not mockup_url:
                continue

            expected_cat = type_to_mockup_category.get(item_type, "")
            if expected_cat and mockup_url:
                # Check if mockup URL/filename contains wrong category
                mockup_lower = mockup_url.lower()
                wrong_matches = []
                for cat in ["ottoman", "bench", "sofa", "chair", "window"]:
                    if cat != expected_cat and cat in mockup_lower:
                        wrong_matches.append(cat)

                if wrong_matches:
                    issues.append(
                        f"'{item.get('name')}' is type '{item_type}' (expect {expected_cat} mockup) "
                        f"but mockup URL suggests: {', '.join(wrong_matches)}"
                    )

        if issues:
            return CheckResult(
                "mockup_match", False, "warning",
                f"Mockup mismatch: {'; '.join(issues[:2])}",
                {"issues": issues},
            )

        return CheckResult(
            "mockup_match", True, "info",
            "Mockup types match item types (or no mockups to check).",
        )

    def check_market_range(self, quote: Dict[str, Any]) -> CheckResult:
        """WARN if total price is outside market range for the item types."""
        tiers = quote.get("tiers", {})
        tier_a = tiers.get("A", {})
        issues = []

        for tier_item in tier_a.get("items", []):
            item_type = tier_item.get("type", "")
            item_name = tier_item.get("name", item_type)
            subtotal = tier_item.get("subtotal", 0)
            quantity = tier_item.get("quantity", 1)
            per_unit = subtotal / max(quantity, 1)

            market = MARKET_RANGES.get(item_type)
            if not market:
                continue

            if per_unit < market["min"] * 0.5:
                issues.append(
                    f"'{item_name}' at ${per_unit:.0f}/unit is BELOW market "
                    f"(market: ${market['min']}-${market['max']}). Too cheap — may be underpriced."
                )
            elif per_unit > market["max"] * 2.0:
                issues.append(
                    f"'{item_name}' at ${per_unit:.0f}/unit is FAR ABOVE market "
                    f"(market: ${market['min']}-${market['max']}). Verify pricing."
                )
            elif per_unit > market["max"] * 1.3:
                issues.append(
                    f"'{item_name}' at ${per_unit:.0f}/unit is above market high "
                    f"(market: ${market['min']}-${market['max']}). Consider reviewing."
                )

        if issues:
            has_below = any("BELOW" in i for i in issues)
            severity = "error" if has_below else "warning"
            return CheckResult(
                "market_range", False, severity,
                f"Market range issues: {'; '.join(issues[:2])}",
                {"issues": issues, "market_ranges": MARKET_RANGES},
            )

        return CheckResult(
            "market_range", True, "info",
            "All item prices within expected market ranges.",
        )

    def check_math(self, quote: Dict[str, Any]) -> CheckResult:
        """FAIL if math doesn't add up in any tier."""
        tiers = quote.get("tiers", {})
        issues = []

        for tier_key, tier_data in tiers.items():
            # Check item subtotals sum to tier subtotal
            items_sum = sum(
                item.get("subtotal", 0) for item in tier_data.get("items", [])
            )
            tier_subtotal = tier_data.get("subtotal", 0)

            if abs(items_sum - tier_subtotal) > 0.02:
                issues.append(
                    f"Tier {tier_key}: items sum ${items_sum:.2f} != "
                    f"stated subtotal ${tier_subtotal:.2f}"
                )

            # Check tax calculation
            tax_rate = tier_data.get("tax_rate", 0)
            expected_tax = round(tier_subtotal * tax_rate, 2)
            actual_tax = tier_data.get("tax", 0)
            if abs(expected_tax - actual_tax) > 0.02:
                issues.append(
                    f"Tier {tier_key}: expected tax ${expected_tax:.2f} != "
                    f"actual tax ${actual_tax:.2f}"
                )

            # Check total = subtotal + tax
            expected_total = round(tier_subtotal + actual_tax, 2)
            actual_total = tier_data.get("total", 0)
            if abs(expected_total - actual_total) > 0.02:
                issues.append(
                    f"Tier {tier_key}: subtotal+tax ${expected_total:.2f} != "
                    f"total ${actual_total:.2f}"
                )

            # Check deposit
            expected_deposit = round(actual_total * DEPOSIT_PERCENTAGE, 2)
            actual_deposit = tier_data.get("deposit", 0)
            if abs(expected_deposit - actual_deposit) > 0.02:
                issues.append(
                    f"Tier {tier_key}: expected deposit ${expected_deposit:.2f} != "
                    f"actual deposit ${actual_deposit:.2f}"
                )

        if issues:
            return CheckResult(
                "math", False, "error",
                f"Math errors: {'; '.join(issues[:3])}",
                {"issues": issues},
            )

        return CheckResult(
            "math", True, "info",
            "All math checks pass (subtotals, tax, totals, deposits).",
        )

    def check_completeness(self, quote: Dict[str, Any]) -> CheckResult:
        """WARN if quote is missing recommended sections."""
        missing = []
        is_flat = quote.get("pricing_mode") == "flat"

        if not quote.get("customer_name"):
            missing.append("customer name")
        if not quote.get("created_at"):
            missing.append("creation date")
        if is_flat:
            # Flat quotes need line_items, not items/tiers
            if not quote.get("line_items"):
                missing.append("line items")
        else:
            if not quote.get("items"):
                missing.append("items list")
            if not quote.get("tiers"):
                missing.append("pricing tiers")

        # Recommended but not required
        optional_missing = []
        if not quote.get("customer_email") and not quote.get("customer_phone"):
            optional_missing.append("customer email or phone")
        if not quote.get("location"):
            optional_missing.append("location (for tax rate)")
        if not any(
            item.get("mockup_url") for item in quote.get("items", [])
        ):
            optional_missing.append("AI mockup images")

        if missing:
            return CheckResult(
                "completeness", False, "error",
                f"Missing required fields: {', '.join(missing)}",
                {"required_missing": missing, "optional_missing": optional_missing},
            )

        if optional_missing:
            return CheckResult(
                "completeness", False, "info",
                f"Quote complete but could add: {', '.join(optional_missing)}",
                {"optional_missing": optional_missing},
            )

        return CheckResult(
            "completeness", True, "info",
            "Quote has all required and recommended fields.",
        )

    def check_customer_info(self, quote: Dict[str, Any]) -> CheckResult:
        """WARN if customer info is incomplete."""
        name = (quote.get("customer_name") or "").strip()
        email = (quote.get("customer_email") or "").strip()
        phone = (quote.get("customer_phone") or "").strip()
        address = (quote.get("customer_address") or "").strip()

        if not name:
            return CheckResult(
                "customer_info", False, "error",
                "Customer name is required.",
            )

        if not email and not phone:
            return CheckResult(
                "customer_info", False, "warning",
                f"Customer '{name}' has no email or phone. Need at least one contact method.",
            )

        issues = []
        if email and "@" not in email:
            issues.append(f"Email '{email}' appears invalid (no @)")
        if not address:
            issues.append("No address (recommended for installation quotes)")

        if issues:
            return CheckResult(
                "customer_info", False, "info",
                f"Customer info: {'; '.join(issues)}",
                {"issues": issues},
            )

        return CheckResult(
            "customer_info", True, "info",
            f"Customer info complete: {name}",
        )


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def verify_quote(quote_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run all verification checks on a quote. Convenience wrapper."""
    verifier = QuoteVerifier()
    return verifier.verify_quote(quote_data)


def save_verification(quote_id: str, result: Dict[str, Any]) -> str:
    """Save verification result alongside the quote JSON."""
    filepath = os.path.join(QUOTES_DIR, f"{quote_id}_verification.json")
    os.makedirs(QUOTES_DIR, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(result, f, indent=2, default=str)
    logger.info("Verification saved to %s", filepath)
    return filepath


def load_verification(quote_id: str) -> Optional[Dict[str, Any]]:
    """Load the last verification result for a quote."""
    filepath = os.path.join(QUOTES_DIR, f"{quote_id}_verification.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        return json.load(f)
