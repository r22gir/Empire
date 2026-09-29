"""
Quote PDF Service — SQL quotes (quotes_v2) rendered in the Empire Workroom
house format (cream / ink / gold), the same letterhead as workroom estimates.
"""
import logging
import os

from app.services.data_paths import quote_pdf_dir
from app.services.house_pdf import render_estimate, render_pdf, render_shop_ticket
from app.services.quote_service import get_quote

logger = logging.getLogger(__name__)


def _write_pdf(quote_id: str, quote: dict, pdf_bytes: bytes, suffix: str = "") -> None:
    pdf_dir = str(quote_pdf_dir())
    os.makedirs(pdf_dir, exist_ok=True)
    number = quote.get("quote_number", quote_id)
    filename = f"{number}{suffix}.pdf"
    pdf_path = os.path.join(pdf_dir, filename)
    with open(pdf_path, "wb") as handle:
        handle.write(pdf_bytes)
    if not suffix:
        try:
            from app.db.database import get_db
            with get_db() as conn:
                conn.execute(
                    "UPDATE quotes_v2 SET pdf_path = ? WHERE id = ?",
                    (pdf_path, quote_id),
                )
        except Exception:
            logger.debug("Could not store pdf_path for %s", quote_id)
    logger.info("Generated PDF for quote %s: %s", quote_id, pdf_path)


def generate_quote_pdf(quote_id: str) -> bytes:

    """Generate a house-format estimate PDF. Returns PDF bytes."""
    quote = get_quote(quote_id)
    if not quote:
        raise FileNotFoundError(f"Quote {quote_id} not found")
    pdf_bytes = render_pdf(render_estimate(quote))
    _write_pdf(quote_id, quote, pdf_bytes)
    return pdf_bytes


def generate_shop_pdf(quote_id: str) -> bytes:
    """Shop copy of a SQL quote, same house format, fractional inches."""
    quote = get_quote(quote_id)
    if not quote:
        raise FileNotFoundError(f"Quote {quote_id} not found")
    pdf_bytes = render_pdf(render_shop_ticket(quote))
    _write_pdf(quote_id, quote, pdf_bytes, suffix="-shop")


def generate_quote_pdf_legacy_portrait(quote_id: str) -> bytes:
    """Legacy McLean gold portrait PDF (Willard-era). Retained for explicit opt-in."""
    from app.services.estimates.mclean_estimate_pdf import generate_mclean_estimate_pdf
    return generate_mclean_estimate_pdf(quote_id, save=True)

    return pdf_bytes
