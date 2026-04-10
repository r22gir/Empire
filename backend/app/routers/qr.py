"""
QR Code generation for Termly cookie consent, privacy policy, and OpenCode phone pairing.
"""
import io
import logging
import os
import socket
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import Response

logger = logging.getLogger("empire.qr")

router = APIRouter(prefix="/qr", tags=["qr"])

TERMLY_URL = "https://termly.io/privacy-policy-generator/?utm_source=badge&utm_medium=QRCode&utm_campaign={domain}"
PRIVACY_DEFAULT = "https://studio.empirebox.store/privacy"
COOKIE_DEFAULT = "https://studio.empirebox.store/cookie-policy"

OPENCODE_CLI = Path.home() / ".opencode" / "bin" / "opencode"
ACP_PORT = 8787


# ── ACP Server Management ───────────────────────────────────────────────────

_acp_proc = None
_acp_lock = threading.Lock()


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _is_port_open(port: int, host: str = "0.0.0.0") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def _is_acp_running() -> bool:
    return _is_port_open(ACP_PORT, "127.0.0.1")


@contextmanager
def _acp_lock_ctx():
    with _acp_lock:
        yield


def _start_acp_server() -> dict:
    global _acp_proc
    with _acp_lock_ctx():
        if _is_acp_running():
            ip = _get_local_ip()
            return {"status": "already_running", "url": f"http://{ip}:{ACP_PORT}", "port": ACP_PORT}

        if _acp_proc is not None:
            try:
                _acp_proc.terminate()
            except Exception:
                pass

        env = {**os.environ, "OPENCODE_SERVER_PASSWORD": ""}
        _acp_proc = subprocess.Popen(
            [str(OPENCODE_CLI), "serve", "--port", str(ACP_PORT), "--hostname", "0.0.0.0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            cwd=str(Path.home()),
        )
        for _ in range(10):
            if _is_acp_running():
                break
            import time; time.sleep(0.5)

        ip = _get_local_ip()
        status = "running" if _is_acp_running() else "failed"
        return {"status": status, "url": f"http://{ip}:{ACP_PORT}", "port": ACP_PORT}


def _stop_acp_server() -> dict:
    global _acp_proc
    with _acp_lock_ctx():
        if _acp_proc is not None:
            try:
                _acp_proc.terminate()
                _acp_proc.wait(timeout=3)
            except Exception:
                try:
                    _acp_proc.kill()
                except Exception:
                    pass
            _acp_proc = None
        return {"status": "stopped"}


def _get_pairing_url() -> str:
    ip = _get_local_ip()
    return f"http://{ip}:{ACP_PORT}"


def _generate_qr_png(url: str, size: int = 300) -> bytes:
    import qrcode
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.resize((size, size)).save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ── Termly / Privacy QR ────────────────────────────────────────────────────

@router.get("/termly")
async def termly_qr(
    domain: str = Query("empirebox.store", description="Domain for Termly URL"),
    size: int = Query(300, ge=100, le=800, description="QR code size in pixels"),
):
    """Generate a QR code for the Termly privacy policy URL of a given domain."""
    url = TERMLY_URL.format(domain=domain)
    png = _generate_qr_png(url, size)
    logger.info(f"Generated Termly QR for domain={domain}")
    return Response(content=png, media_type="image/png")


@router.get("/privacy")
async def privacy_qr(
    url: str = Query(PRIVACY_DEFAULT, description="URL to encode"),
    size: int = Query(300, ge=100, le=800, description="QR code size in pixels"),
):
    """Generate a QR code for any URL (default: privacy policy page)."""
    png = _generate_qr_png(url, size)
    return Response(content=png, media_type="image/png")


@router.get("/cookie-policy")
async def cookie_qr(
    size: int = Query(300, ge=100, le=800, description="QR code size in pixels"),
):
    """Generate a QR code for the cookie policy page."""
    png = _generate_qr_png(COOKIE_DEFAULT, size)
    return Response(content=png, media_type="image/png")


# ── OpenCode Phone Pairing ──────────────────────────────────────────────────

@router.get("/pairing/status")
async def pairing_status():
    """Check if the OpenCode ACP server is running."""
    running = _is_acp_running()
    ip = _get_local_ip() if running else None
    return {
        "status": "running" if running else "stopped",
        "url": f"http://{ip}:{ACP_PORT}" if running else None,
        "port": ACP_PORT,
        "local_ip": ip,
    }


@router.post("/pairing/start")
async def pairing_start():
    """Start the OpenCode ACP server for phone pairing.

    Returns the connection URL and a base64 preview of the QR code.
    """
    result = _start_acp_server()
    if result["status"] == "running":
        png = _generate_qr_png(result["url"], 300)
        import base64
        qr_preview = base64.b64encode(png).decode()
        result["qr_preview"] = f"data:image/png;base64,{qr_preview}"
    return result


@router.post("/pairing/stop")
async def pairing_stop():
    """Stop the OpenCode ACP server."""
    return _stop_acp_server()


@router.get("/pairing/url")
async def pairing_url():
    """Get the current pairing URL (ACP server must be running)."""
    if not _is_acp_running():
        _start_acp_server()
    return {"url": _get_pairing_url(), "port": ACP_PORT}


@router.get("/pairing/qr")
async def pairing_qr(size: int = Query(300, ge=100, le=800)):
    """Generate a QR code PNG for the OpenCode ACP server pairing URL.

    Starts the server if not already running.
    """
    if not _is_acp_running():
        _start_acp_server()
    url = _get_pairing_url()
    png = _generate_qr_png(url, size)
    return Response(content=png, media_type="image/png")


@router.get("/pairing/copy")
async def pairing_copy():
    """Return the pairing URL as plain text for programmatic use."""
    if not _is_acp_running():
        _start_acp_server()
    return {"url": _get_pairing_url(), "format": "text/plain"}
