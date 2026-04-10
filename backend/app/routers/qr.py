"""
QR Code generation for Termly cookie consent and privacy policy.
"""
import io
import logging
from fastapi import APIRouter, Query
from fastapi.responses import Response

logger = logging.getLogger("empire.qr")

router = APIRouter(prefix="/qr", tags=["qr"])

TERMLY_URL = "https://termly.io/privacy-policy-generator/?utm_source=badge&utm_medium=QRCode&utm_campaign={domain}"
PRIVACY_DEFAULT = "https://studio.empirebox.store/privacy"
COOKIE_DEFAULT = "https://studio.empirebox.store/cookie-policy"


@router.get("/termly")
async def termly_qr(
    domain: str = Query("empirebox.store", description="Domain for Termly URL"),
    size: int = Query(300, ge=100, le=800, description="QR code size in pixels"),
):
    """Generate a QR code for the Termly privacy policy URL of a given domain."""
    import qrcode

    url = TERMLY_URL.format(domain=domain)
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.resize((size, size)).save(buf, format="PNG")
    buf.seek(0)
    logger.info(f"Generated Termly QR for domain={domain}")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/privacy")
async def privacy_qr(
    url: str = Query(PRIVACY_DEFAULT, description="URL to encode"),
    size: int = Query(300, ge=100, le=800, description="QR code size in pixels"),
):
    """Generate a QR code for any URL (default: privacy policy page)."""
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.resize((size, size)).save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/cookie-policy")
async def cookie_qr(
    size: int = Query(300, ge=100, le=800, description="QR code size in pixels"),
):
    """Generate a QR code for the cookie policy page."""
    import qrcode

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(COOKIE_DEFAULT)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.resize((size, size)).save(buf, format="PNG")
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/png")
