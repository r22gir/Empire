"""
Amazon Product Validator — MarketF scaffolding (Phase 0)

Validates product data against Amazon listing requirements before
pushing to SP-API. Returns a structured result with field-level errors
and warnings so the Partner Dashboard can display actionable feedback.

Reference: docs/MARKETF_AMAZON_SPEC.md — Product Data Requirements table.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# -----------------------------------------------------------------------
# Validation constants (from Amazon listing requirements)
# -----------------------------------------------------------------------

TITLE_MAX_CHARS = 200
BULLET_POINT_MAX_COUNT = 5
BULLET_POINT_MAX_CHARS = 300
DESCRIPTION_MAX_CHARS = 1000
IMAGE_MIN_COUNT = 7
IMAGE_MIN_DIMENSION_PX = 1000

# Characters not allowed in Amazon listing titles
TITLE_FORBIDDEN_PATTERN = re.compile(r"[!$?_{}\^~`|<>]")

# GTIN lengths: UPC-A=12, EAN-13=13, ISBN-13=13, GTIN-14=14
GTIN_VALID_LENGTHS = {12, 13, 14}


# -----------------------------------------------------------------------
# Result types
# -----------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Aggregated result of a full product validation pass."""

    is_valid: bool = True
    errors: Dict[str, List[str]] = field(default_factory=dict)
    warnings: Dict[str, List[str]] = field(default_factory=dict)

    def add_error(self, field_name: str, message: str) -> None:
        self.is_valid = False
        self.errors.setdefault(field_name, []).append(message)

    def add_warning(self, field_name: str, message: str) -> None:
        self.warnings.setdefault(field_name, []).append(message)


# -----------------------------------------------------------------------
# Individual field validators
# -----------------------------------------------------------------------


def validate_gtin(gtin: Optional[str], result: ValidationResult) -> None:
    """Validate UPC/EAN/GTIN: numeric, correct length, Luhn checksum."""
    if not gtin:
        result.add_error("gtin", "GTIN/UPC/EAN is required")
        return

    digits = re.sub(r"\D", "", gtin)

    if len(digits) not in GTIN_VALID_LENGTHS:
        result.add_error(
            "gtin",
            f"GTIN must be 12, 13, or 14 digits (got {len(digits)}). "
            "Use a GS1-verified UPC/EAN.",
        )
        return

    if not _luhn_check(digits):
        result.add_error(
            "gtin",
            "GTIN checksum is invalid. Verify your UPC/EAN with your GS1 barcode.",
        )


def validate_title(title: Optional[str], result: ValidationResult) -> None:
    """Validate Amazon listing title."""
    if not title:
        result.add_error("title", "Title is required")
        return

    if len(title) > TITLE_MAX_CHARS:
        result.add_error(
            "title",
            f"Title exceeds {TITLE_MAX_CHARS} characters (got {len(title)})",
        )

    if TITLE_FORBIDDEN_PATTERN.search(title):
        result.add_error(
            "title",
            "Title contains forbidden characters (!$?_{}^~`|<>). Remove them.",
        )

    if title != title.strip():
        result.add_warning("title", "Title has leading or trailing whitespace")


def validate_bullet_points(
    bullet_points: Optional[List[str]], result: ValidationResult
) -> None:
    """Validate Amazon bullet points (feature highlights)."""
    if not bullet_points:
        result.add_warning("bullet_points", "No bullet points provided (recommended: 5)")
        return

    if len(bullet_points) > BULLET_POINT_MAX_COUNT:
        result.add_error(
            "bullet_points",
            f"Maximum {BULLET_POINT_MAX_COUNT} bullet points allowed "
            f"(got {len(bullet_points)})",
        )

    for i, point in enumerate(bullet_points, start=1):
        if len(point) > BULLET_POINT_MAX_CHARS:
            result.add_error(
                "bullet_points",
                f"Bullet point {i} exceeds {BULLET_POINT_MAX_CHARS} characters "
                f"(got {len(point)})",
            )


def validate_description(description: Optional[str], result: ValidationResult) -> None:
    """Validate Amazon product description."""
    if not description:
        result.add_warning("description", "No description provided")
        return

    if len(description) > DESCRIPTION_MAX_CHARS:
        result.add_error(
            "description",
            f"Description exceeds {DESCRIPTION_MAX_CHARS} characters "
            f"(got {len(description)})",
        )


def validate_images(images: Optional[List[str]], result: ValidationResult) -> None:
    """
    Validate image list meets Amazon requirements.

    Full image analysis (white background check, pixel dimensions, product fill)
    requires image processing and is done server-side. This validator checks
    the structural requirements (count, non-empty URLs).
    """
    if not images:
        result.add_error("images", "At least one image URL is required")
        return

    if len(images) < IMAGE_MIN_COUNT:
        result.add_error(
            "images",
            f"Amazon recommends {IMAGE_MIN_COUNT}+ images (got {len(images)}). "
            "Add more product images (angles, lifestyle, detail shots).",
        )

    for i, url in enumerate(images, start=1):
        if not url or not url.strip():
            result.add_error("images", f"Image {i} URL is empty")
        elif not url.startswith(("http://", "https://")):
            result.add_error("images", f"Image {i} has an invalid URL (must be http/https)")

    result.add_warning(
        "images",
        "Ensure main image has pure white background (RGB 255,255,255), "
        f"≥{IMAGE_MIN_DIMENSION_PX}px longest side, no watermarks or text overlays.",
    )


def validate_price(price: Any, result: ValidationResult) -> None:
    """Validate listing price."""
    if price is None:
        result.add_error("price", "Price is required")
        return

    try:
        price_val = float(price)
    except (TypeError, ValueError):
        result.add_error("price", f"Price must be a number (got {price!r})")
        return

    if price_val <= 0:
        result.add_error("price", "Price must be greater than zero")

    # Warn if more than 2 decimal places (Amazon rounds but it's best practice)
    if round(price_val, 2) != price_val:
        result.add_warning("price", "Price has more than 2 decimal places; it will be rounded")


def validate_inventory(quantity: Any, result: ValidationResult) -> None:
    """Validate inventory quantity."""
    if quantity is None:
        result.add_error("inventory", "Inventory quantity is required")
        return

    try:
        qty = int(quantity)
    except (TypeError, ValueError):
        result.add_error("inventory", f"Inventory must be an integer (got {quantity!r})")
        return

    if qty < 0:
        result.add_error("inventory", "Inventory quantity cannot be negative")


def validate_dimensions(
    weight: Any,
    length: Any,
    width: Any,
    height: Any,
    result: ValidationResult,
) -> None:
    """Validate shipping weight and package dimensions (required for FBA)."""
    for label, val in [("weight", weight), ("length", length), ("width", width), ("height", height)]:
        if val is None:
            result.add_error("dimensions", f"{label.capitalize()} is required")
        else:
            try:
                if float(val) <= 0:
                    result.add_error("dimensions", f"{label.capitalize()} must be greater than zero")
            except (TypeError, ValueError):
                result.add_error(
                    "dimensions", f"{label.capitalize()} must be a number (got {val!r})"
                )


def validate_category(category_id: Optional[str], result: ValidationResult) -> None:
    """Validate Amazon category ID is present (full whitelist TBD in Phase 3)."""
    if not category_id:
        result.add_error("category", "Amazon category ID is required")


def validate_brand(
    brand_name: Optional[str],
    brand_authorized: Optional[bool],
    result: ValidationResult,
) -> None:
    """Validate brand name and authorization status."""
    if not brand_name:
        result.add_error("brand", "Brand name is required")
        return

    if brand_authorized is False:
        result.add_error(
            "brand",
            "Brand is not authorized. Upload brand authorization document before listing. "
            "If this is a generic product, set brand to 'Generic'.",
        )


def validate_manufacturer(manufacturer: Optional[str], result: ValidationResult) -> None:
    """Validate manufacturer name."""
    if not manufacturer:
        result.add_error("manufacturer", "Manufacturer name is required")


# -----------------------------------------------------------------------
# Main validator
# -----------------------------------------------------------------------


class ProductValidator:
    """
    Validates a product data dict against Amazon listing requirements.

    Usage:
        validator = ProductValidator()
        result = validator.validate(product_data)
        if not result.is_valid:
            print(result.errors)
    """

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Run all field validators on the supplied product data.

        Args:
            data: Dictionary with product fields. Expected keys:
                gtin, title, bullet_points, description, images, price,
                inventory, weight, length, width, height, category_id,
                brand_name, brand_authorized, manufacturer

        Returns:
            ValidationResult with is_valid flag, errors, and warnings.
        """
        result = ValidationResult()

        validate_gtin(data.get("gtin"), result)
        validate_title(data.get("title"), result)
        validate_bullet_points(data.get("bullet_points"), result)
        validate_description(data.get("description"), result)
        validate_images(data.get("images"), result)
        validate_price(data.get("price"), result)
        validate_inventory(data.get("inventory"), result)
        validate_dimensions(
            data.get("weight"),
            data.get("length"),
            data.get("width"),
            data.get("height"),
            result,
        )
        validate_category(data.get("category_id"), result)
        validate_brand(data.get("brand_name"), data.get("brand_authorized"), result)
        validate_manufacturer(data.get("manufacturer"), result)

        return result


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------


def _luhn_check(digits: str) -> bool:
    """
    Validate a numeric string using the Luhn algorithm.
    Used for UPC/EAN/GTIN checksum verification.
    """
    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
