"""WhatsApp Business Calling API — WebRTC bridge to Max xAI Realtime voice brain.

Handles user-initiated inbound WhatsApp calls to Max.
- Allowlist check: Only founder numbers can call; all other callers are rejected.
- WebRTC Peer: aiortc endpoint handling Meta's SDP offer, generating SDP answer.
- Graph Calls API: pre_accept (with SDP answer) -> wait for ICE+DTLS -> accept
  (same SDP answer), or reject. Every Graph response is checked and logged
  (status, success, error code/subcode/details; never the token).
- Audio Relay: Bidirectional audio bridge between WebRTC audio track (Opus 48k)
  and xAI realtime session (PCM16 24k). Outbound audio is paced in real time.
- Lifespan & cleanup: Handles terminate event, caller hangup, media failure,
  timeout cap (default 30 min), and idle timeout. When Max ends the call itself
  it tells Meta (action=terminate).
- Mid-call documents: If Max generates quotes/drawings during the call, sends them
  as draft PDFs into the founder's WhatsApp chat.

Meta specifics (developers.facebook.com/docs/whatsapp/cloud-api/calling):
- Meta's media server is ICE-lite with public host candidates and no trickle;
  the offer is a=setup:actpass, the answer must be a=setup:active.
- Graph rejects an answer that carries any fingerprint other than sha-256
  (error_subcode 2494010 "Fingerprint algo is not SHA256"). aiortc emits
  sha-256, sha-384 and sha-512, so the answer is filtered before it is sent.
- pre_accept and accept must carry the identical SDP answer.
- Media should flow only after accept returns 200.
"""
from __future__ import annotations

import asyncio
import base64
import fractions
import ipaddress
import json
import logging
import os
import re
import time
from typing import Any, Callable, Optional

import av
from aiortc import (
    MediaStreamTrack,
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)

from app.services.max.voice_live import (
    QUEUE_TOOL,
    VOICE_READ_ONLY_TOOLS,
    VOICE_TOOL_ALLOWLIST,
    fresh_instructions,
    realtime_tool_definitions,
    run_voice_tool,
    voice_model,
    voice_name,
)

logger = logging.getLogger("max.whatsapp_calling")

ENV_CALLING_ENABLED = "WHATSAPP_CALLING_ENABLED"
ENV_CALL_MAX_SECONDS = "WHATSAPP_CALL_MAX_SECONDS"
ENV_TURN_URL = "WHATSAPP_TURN_URL"
ENV_TURN_USERNAME = "WHATSAPP_TURN_USERNAME"
ENV_TURN_CREDENTIAL = "WHATSAPP_TURN_CREDENTIAL"
ENV_STUN_SERVER = "WHATSAPP_STUN_SERVER"            # "none" disables STUN
ENV_ICE_INTERFACES = "WHATSAPP_ICE_INTERFACES"      # e.g. "enp0s25" (comma list)
ENV_ACCEPT_WAIT = "WHATSAPP_ACCEPT_WAIT_SECONDS"    # wait for ICE+DTLS before accept
ENV_MEDIA_TIMEOUT = "WHATSAPP_MEDIA_TIMEOUT_SECONDS"  # give up if media never connects
ENV_SETUP_INLINE = "WHATSAPP_CALL_SETUP_INLINE"     # 1 = handle connect inside the webhook request
ENV_GREETING = "WHATSAPP_CALL_GREETING"             # 0 = do not speak first
ENV_LOG_LEVEL = "WHATSAPP_CALL_LOG_LEVEL"

DEFAULT_STUN_SERVER = "stun:stun.l.google.com:19302"
DEFAULT_MAX_CALL_SECONDS = 1800  # 30 minutes
DEFAULT_IDLE_TIMEOUT_SECONDS = 120  # 2 minutes of complete silence / inactivity
DEFAULT_ACCEPT_WAIT_SECONDS = 12.0
DEFAULT_MEDIA_TIMEOUT_SECONDS = 25.0
SAMPLE_RATE = 24000  # xAI realtime audio rate
OPUS_RATE = 48000    # WebRTC audio rate
FRAME_SAMPLES = 480  # 20 ms at 24 kHz
FRAME_BYTES = FRAME_SAMPLES * 2
UPSTREAM_CHUNK_BYTES = 1920  # 40 ms of PCM16 24k mono per input_audio_buffer.append

WHATSAPP_CALL_NOTE = (
    "\n\n## Channel: WhatsApp voice call\n"
    "You are on a live WhatsApp phone call with Rafael. The audio is a phone line. "
    "When the call connects, speak first: greet him in one short, natural sentence and ask what he needs. "
    "Keep replies short and conversational."
)

_active_whatsapp_calls: dict[str, "WhatsAppVoiceCall"] = {}
_background_tasks: set[asyncio.Task] = set()


def _configure_logging() -> None:
    """The backend root logger has no INFO handler, so call logs never reached the
    journal. Give this logger its own stderr handler (journal) once."""
    level_name = (os.getenv(ENV_LOG_LEVEL) or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    if not any(getattr(h, "_wa_call_handler", False) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler._wa_call_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False


_configure_logging()

_TOKEN_RE = re.compile(r"(EAA[A-Za-z0-9]{10,}|Bearer\s+\S+|xai-[A-Za-z0-9]{10,}|access_token=[^&\s\"]+)")


def _redact(text: Any) -> str:
    return _TOKEN_RE.sub("[REDACTED]", str(text))


def calling_enabled() -> bool:
    raw = os.getenv(ENV_CALLING_ENABLED, "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return max(0.0, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def max_call_duration_seconds() -> int:
    try:
        return max(30, int(os.getenv(ENV_CALL_MAX_SECONDS, str(DEFAULT_MAX_CALL_SECONDS))))
    except ValueError:
        return DEFAULT_MAX_CALL_SECONDS


def setup_inline() -> bool:
    return (os.getenv(ENV_SETUP_INLINE) or "").strip().lower() in ("1", "true", "yes", "on")


def greeting_enabled() -> bool:
    return (os.getenv(ENV_GREETING) or "1").strip().lower() not in ("0", "false", "no", "off")


def get_ice_servers() -> list[RTCIceServer]:
    servers: list[RTCIceServer] = []
    stun = (os.getenv(ENV_STUN_SERVER) or DEFAULT_STUN_SERVER).strip()
    if stun and stun.lower() not in ("none", "off", "0"):
        servers.append(RTCIceServer(urls=stun))
    turn_url = os.getenv(ENV_TURN_URL, "").strip()
    if turn_url:
        username = os.getenv(ENV_TURN_USERNAME, "").strip()
        credential = os.getenv(ENV_TURN_CREDENTIAL, "").strip()
        servers.append(
            RTCIceServer(
                urls=turn_url,
                username=username or None,
                credential=credential or None,
            )
        )
    return servers


# ── Host candidate filter ───────────────────────────────────────────
# aioice gathers on every interface (libvirt, Tailscale, IPv6 ULA ...). Those
# candidates can never reach Meta's public media server, they slow gathering
# (STUN timeouts) and clutter the answer. Keep real LAN/WAN interfaces only.

_VIRTUAL_IFACE_PREFIXES = ("lo", "virbr", "docker", "br-", "veth", "tailscale", "zt", "wg", "tun", "vmnet", "vboxnet")
_TAILSCALE_V4 = ipaddress.ip_network("100.64.0.0/10")
_host_filter_installed = False


def _usable_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_loopback or addr.is_link_local or addr.is_multicast:
        return False
    if addr.version == 4 and addr in _TAILSCALE_V4:
        return False
    if addr.version == 6 and not addr.is_global:
        return False  # ULA (fd00::/8) cannot reach Meta's public IPv6
    return True


def _default_route_interfaces() -> list[str]:
    """Interface(s) used for the default IPv4 route — preferred for ICE on a dual-homed box."""
    try:
        import subprocess
        out = subprocess.check_output(["ip", "-4", "route", "show", "default"], text=True, timeout=2)
    except Exception:
        return []
    names: list[str] = []
    for line in out.splitlines():
        parts = line.split()
        if "dev" in parts:
            name = parts[parts.index("dev") + 1]
            if name and name not in names:
                names.append(name)
    return names


def filtered_host_addresses(use_ipv4: bool, use_ipv6: bool) -> list[str]:
    import ifaddr

    wanted = [s.strip() for s in (os.getenv(ENV_ICE_INTERFACES) or "").split(",") if s.strip()]
    if not wanted:
        # Prefer the NIC that owns the default route so STUN/srflx matches real egress
        # (virbr/tailscale stay excluded via the virtual-prefix filter below).
        wanted = _default_route_interfaces()
    out: list[str] = []
    for adapter in ifaddr.get_adapters():
        name = adapter.nice_name or adapter.name or ""
        if wanted:
            if name not in wanted:
                continue
        elif name.startswith(_VIRTUAL_IFACE_PREFIXES):
            continue
        for ip in adapter.ips:
            if isinstance(ip.ip, str):
                if use_ipv4 and _usable_ip(ip.ip):
                    out.append(ip.ip)
            elif use_ipv6 and ip.ip[2] == 0 and _usable_ip(ip.ip[0]):
                out.append(ip.ip[0])
    return out


def install_host_filter() -> None:
    """Patch aioice's host address discovery (only aiortc user in this process)."""
    global _host_filter_installed
    if _host_filter_installed:
        return
    try:
        import aioice.ice as aioice_ice

        original = aioice_ice.get_host_addresses

        def _patched(use_ipv4: bool, use_ipv6: bool) -> list[str]:
            addrs = filtered_host_addresses(use_ipv4, use_ipv6)
            return addrs or original(use_ipv4, use_ipv6)

        aioice_ice.get_host_addresses = _patched
        _host_filter_installed = True
    except Exception as exc:  # never block a call over this
        logger.warning("whatsapp_call: host candidate filter not installed: %s", exc)


# ── SDP helpers ─────────────────────────────────────────────────────

def _sdp_lines(sdp: str) -> list[str]:
    return [line for line in (sdp or "").replace("\r\n", "\n").split("\n") if line.strip()]


def prepare_offer(sdp: str) -> str:
    """Normalize Meta's offer. Meta is ICE-lite and sends every candidate up front
    (no trickle) but omits a=end-of-candidates; without it aioice can never declare
    ICE failed and a dead call just hangs in 'checking'."""
    lines = _sdp_lines(sdp)
    has_candidates = any(line.startswith("a=candidate:") for line in lines)
    if has_candidates and not any(line.startswith("a=end-of-candidates") for line in lines):
        out: list[str] = []
        in_media = False
        media_has_cand = False

        def _close_section() -> None:
            if in_media and media_has_cand:
                out.append("a=end-of-candidates")

        for line in lines:
            if line.startswith("m="):
                _close_section()
                in_media, media_has_cand = True, False
            elif line.startswith("a=candidate:"):
                media_has_cand = True
            out.append(line)
        _close_section()
        lines = out
    return "\r\n".join(lines) + "\r\n"


def whatsapp_sdp(sdp: str) -> str:
    """Make aiortc's answer acceptable to Graph: sha-256 fingerprint only, CRLF."""
    lines = []
    for line in _sdp_lines(sdp):
        if line.startswith("a=fingerprint:") and not line.lower().startswith("a=fingerprint:sha-256"):
            continue
        lines.append(line)
    return "\r\n".join(lines) + "\r\n"


def summarize_sdp(sdp: str) -> dict[str, Any]:
    """Loggable SDP summary. Never includes ice-pwd or fingerprint values."""
    lines = _sdp_lines(sdp)
    cands = []
    for line in lines:
        if line.startswith("a=candidate:"):
            parts = line.split()
            try:
                typ = parts[parts.index("typ") + 1]
            except (ValueError, IndexError):
                typ = "?"
            if len(parts) >= 6:
                cands.append(f"{typ}:{parts[2].lower()}:{parts[4]}:{parts[5]}")
    def _vals(prefix: str) -> list[str]:
        return [line[len(prefix):] for line in lines if line.startswith(prefix)]
    return {
        "ice_lite": "a=ice-lite" in lines,
        "media": _vals("m="),
        "codecs": _vals("a=rtpmap:"),
        "setup": _vals("a=setup:"),
        "mid": _vals("a=mid:"),
        "bundle": _vals("a=group:"),
        "direction": [line[2:] for line in lines if line in ("a=sendrecv", "a=sendonly", "a=recvonly", "a=inactive")],
        "fingerprint_algos": [v.split()[0] for v in _vals("a=fingerprint:")],
        "ice_ufrag": _vals("a=ice-ufrag:"),
        "rtcp_mux": "a=rtcp-mux" in lines,
        "end_of_candidates": "a=end-of-candidates" in lines,
        "candidates": cands,
    }


def answer_problems(sdp: str) -> list[str]:
    """Checks Meta cares about. Empty list means the answer looks right."""
    s = summarize_sdp(sdp)
    problems = []
    if s["fingerprint_algos"] != ["sha-256"]:
        problems.append(f"fingerprints {s['fingerprint_algos']} (Graph accepts sha-256 only)")
    if s["setup"] != ["active"]:
        problems.append(f"setup {s['setup']} (expected active)")
    if not any(c.split(" ", 1)[-1].lower() == "opus/48000/2" for c in s["codecs"]):
        problems.append("no opus/48000/2")
    if s["direction"] != ["sendrecv"]:
        problems.append(f"direction {s['direction']} (expected sendrecv)")
    if not s["candidates"]:
        problems.append("no ICE candidates")
    return problems


class CallSetupError(RuntimeError):
    pass


class AudioTrackToXAI:
    """Consumes audio frames from WebRTC incoming track (Opus 48k) -> PCM16 24k -> xAI."""

    def __init__(self, track: MediaStreamTrack, call: "WhatsAppVoiceCall"):
        self.track = track
        self.call = call
        self.resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=SAMPLE_RATE,
        )

    async def run(self) -> None:
        pending = bytearray()
        try:
            while not self.call.closed.is_set():
                frame = await self.track.recv()
                self.call.touch_activity()
                self.call.frames_in += 1
                if self.call.frames_in == 1:
                    logger.info(
                        "whatsapp_call[%s] first inbound audio frame (rate=%s layout=%s samples=%s)",
                        self.call.call_id, frame.sample_rate, frame.layout.name, frame.samples,
                    )
                for r_frame in self.resampler.resample(frame):
                    pending.extend(bytes(r_frame.planes[0])[: r_frame.samples * 2])
                if not self.call.accepted:
                    pending.clear()  # nothing goes to xAI before Meta's accept 200
                    continue
                if len(pending) >= UPSTREAM_CHUNK_BYTES:
                    chunk = bytes(pending)
                    pending.clear()
                    self.call.bytes_to_xai += len(chunk)
                    await self.call.send_audio_to_xai(chunk)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.info("whatsapp_call[%s] incoming audio ended: %s", self.call.call_id, exc)


class XAIAudioTrack(MediaStreamTrack):
    """Feeds PCM16 24k audio received from xAI into WebRTC.

    Emits one 20 ms 24 kHz mono frame per recv(), paced in real time (aiortc pulls
    as fast as recv returns). aiortc's Opus encoder resamples to 48 kHz stereo.
    Outputs silence until the call is accepted (Meta: media only after accept 200)
    and whenever the queue runs dry.
    """

    kind = "audio"

    def __init__(self):
        super().__init__()
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._buffer = bytearray()
        self._start: Optional[float] = None
        self._timestamp = 0
        self.live = False  # set True once Meta accepted the call
        self.frames_sent = 0
        self.audio_frames_sent = 0

    def push_pcm(self, pcm: bytes) -> None:
        if pcm:
            self._buffer.extend(pcm)
            while len(self._buffer) >= FRAME_BYTES:
                chunk = bytes(self._buffer[:FRAME_BYTES])
                del self._buffer[:FRAME_BYTES]
                self.queue.put_nowait(chunk)

    def flush(self) -> None:
        self._buffer.clear()
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            from aiortc.mediastreams import MediaStreamError
            raise MediaStreamError
        if self._start is None:
            self._start = time.monotonic()
            self._timestamp = 0
        else:
            self._timestamp += FRAME_SAMPLES
            wait = self._start + (self._timestamp / SAMPLE_RATE) - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            elif wait < -0.5:
                # Event loop stalled; re-anchor instead of bursting to catch up.
                self._start = time.monotonic() - (self._timestamp / SAMPLE_RATE)

        chunk = None
        if self.live and not self.queue.empty():
            try:
                chunk = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                chunk = None
        if chunk is None:
            chunk = b"\x00" * FRAME_BYTES
        else:
            self.audio_frames_sent += 1

        frame = av.AudioFrame(format="s16", layout="mono", samples=FRAME_SAMPLES)
        frame.planes[0].update(chunk)
        frame.sample_rate = SAMPLE_RATE
        frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
        frame.pts = self._timestamp
        self.frames_sent += 1
        return frame


class WhatsAppVoiceCall:
    def __init__(
        self,
        call_id: str,
        caller: str,
        *,
        http_post: Optional[Callable[..., Any]] = None,
        upstream_ws: Any = None,
    ):
        self.call_id = call_id
        self.caller = caller
        self.started = time.monotonic()
        self.last_activity = time.monotonic()
        self.max_duration = max_call_duration_seconds()
        self.closed = asyncio.Event()
        self.media_connected = asyncio.Event()
        self.session_ready = asyncio.Event()
        self.end_reason = "unknown"
        self.http_post = http_post

        self.pc: Optional[RTCPeerConnection] = None
        self.outgoing_track = XAIAudioTrack()
        self.upstream = upstream_ws
        self.active_response: Optional[str] = None
        self.cancelled_responses: set[str] = set()
        self.pending_tools: dict[str, list[asyncio.Task]] = {}
        self.transcript = None
        self.tasks: list[asyncio.Task] = []
        self.accepted = False
        self.answer_sdp = ""
        self._terminated = False
        self._supervisor: Optional[asyncio.Task] = None
        # counters (no audio content is ever logged)
        self.frames_in = 0
        self.bytes_to_xai = 0
        self.audio_deltas = 0
        self.bytes_from_xai = 0
        self.xai_events: dict[str, int] = {}

        try:
            from app.services.max.voice_transcript import VoiceTranscript
            self.transcript = VoiceTranscript(
                self.call_id,
                user=self.caller,
                auth_via="whatsapp_call",
                model=voice_model(),
            )
        except Exception as exc:
            logger.warning("whatsapp_call[%s] transcript disabled: %s", self.call_id, exc)

    def touch_activity(self) -> None:
        self.last_activity = time.monotonic()

    @property
    def conversation_id(self) -> str:
        return self.transcript.conversation_id if self.transcript else f"wa-call-{self.call_id}"

    def record_transcript(self, method: str, *args: Any, **kwargs: Any) -> None:
        if self.transcript:
            try:
                getattr(self.transcript, method)(*args, **kwargs)
            except Exception as exc:
                logger.warning("whatsapp_call[%s] transcript error: %s", self.call_id, exc)

    async def send_audio_to_xai(self, pcm_bytes: bytes) -> None:
        if self.upstream and not self.closed.is_set():
            try:
                payload = {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(pcm_bytes).decode("ascii"),
                }
                await self.upstream.send(json.dumps(payload))
            except Exception as exc:
                logger.warning("whatsapp_call[%s] upstream send failed: %s", self.call_id, exc)
                self.close("upstream_send_error")

    async def send_upstream_json(self, payload: dict[str, Any]) -> None:
        if self.upstream and not self.closed.is_set():
            try:
                await self.upstream.send(json.dumps(payload))
            except Exception as exc:
                logger.warning("whatsapp_call[%s] upstream json failed: %s", self.call_id, exc)
                self.close("upstream_error")

    # ── Graph ────────────────────────────────────────────────────────
    async def post_calls_action(self, action: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """POST /{PHONE_NUMBER_ID}/calls with call_id and action. Logs the outcome
        (HTTP status, success, Graph error code/subcode/details). Returns the JSON
        body with `_http_status` added."""
        from app.services.max.whatsapp_channel import (
            ENV_ACCESS_TOKEN,
            ENV_PHONE_NUMBER_ID,
            GRAPH_ROOT,
            _secret,
        )
        token = _secret(ENV_ACCESS_TOKEN)
        phone_id = _secret(ENV_PHONE_NUMBER_ID)
        url = f"{GRAPH_ROOT}/{phone_id}/calls"
        body: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "call_id": self.call_id,
            "action": action,
        }
        if data:
            body.update(data)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        started = time.monotonic()
        status = 0
        payload: Any = {}
        try:
            if self.http_post is None:
                import httpx
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(url, json=body, headers=headers)
            else:
                res = self.http_post(url, body, headers)
                if hasattr(res, "__await__"):
                    res = await res
            status = int(getattr(res, "status_code", 200) or 200)
            if hasattr(res, "json"):
                try:
                    payload = res.json()
                    if hasattr(payload, "__await__"):
                        payload = await payload
                except Exception:
                    payload = {"text": _redact(getattr(res, "text", ""))[:500]}
            elif isinstance(res, dict):
                payload = res
        except Exception as exc:
            logger.error("whatsapp_call[%s] Graph %s request failed: %s", self.call_id, action, _redact(exc))
            return {"_http_status": 0, "error": {"message": _redact(exc)}}
        if not isinstance(payload, dict):
            payload = {"value": payload}
        payload["_http_status"] = status
        err = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if self._graph_ok(payload):
            logger.info("whatsapp_call[%s] Graph %s -> HTTP %s success=%s (%d ms)",
                        self.call_id, action, status, payload.get("success"), elapsed_ms)
        else:
            logger.error(
                "whatsapp_call[%s] Graph %s FAILED -> HTTP %s code=%s subcode=%s message=%s details=%s (%d ms)",
                self.call_id, action, status, err.get("code"), err.get("error_subcode"),
                _redact(err.get("message") or payload.get("text") or "")[:300],
                _redact((err.get("error_data") or {}).get("details") if isinstance(err.get("error_data"), dict) else "")[:300],
                elapsed_ms,
            )
        return payload

    @staticmethod
    def _graph_ok(payload: dict[str, Any]) -> bool:
        status = int(payload.get("_http_status") or 0)
        if status >= 400 or status == 0 or payload.get("error"):
            return False
        return payload.get("success") is not False

    # ── WebRTC ───────────────────────────────────────────────────────
    def _ice_transport(self):
        try:
            return self.pc.getTransceivers()[0].receiver.transport.transport
        except Exception:
            return None

    def _selected_pair(self) -> str:
        try:
            conn = self._ice_transport()._connection
            pair = (getattr(conn, "_nominated", {}) or {}).get(1)
            if pair is None:
                return "none"
            lc, rc = pair.local_candidate, pair.remote_candidate
            return f"local {lc.type} {lc.host}:{lc.port} -> remote {rc.type} {rc.host}:{rc.port}"
        except Exception:
            return "unknown"

    async def _setup_peer(self, sdp_offer: str) -> str:
        install_host_filter()
        config = RTCConfiguration(iceServers=get_ice_servers())
        self.pc = RTCPeerConnection(configuration=config)
        pc = self.pc
        # Outbound track first so the answer is sendrecv with our SSRC.
        pc.addTrack(self.outgoing_track)

        @pc.on("track")
        def on_track(track):
            logger.info("whatsapp_call[%s] remote track: kind=%s", self.call_id, track.kind)
            if track.kind == "audio":
                audio_sink = AudioTrackToXAI(track, self)
                t = asyncio.create_task(audio_sink.run())
                self.tasks.append(t)

        @pc.on("icegatheringstatechange")
        def on_gather():
            logger.info("whatsapp_call[%s] ICE gathering: %s", self.call_id, pc.iceGatheringState)

        @pc.on("iceconnectionstatechange")
        def on_ice():
            state = pc.iceConnectionState
            extra = f" ({self._selected_pair()})" if state in ("completed", "connected") else ""
            logger.info("whatsapp_call[%s] ICE state: %s%s", self.call_id, state, extra)
            if state in ("failed", "closed"):
                self.close("ice_" + state)

        @pc.on("connectionstatechange")
        def on_conn():
            state = pc.connectionState
            logger.info("whatsapp_call[%s] connection state (ICE+DTLS): %s", self.call_id, state)
            if state == "connected":
                self.media_connected.set()
            elif state in ("failed", "closed"):
                self.close("media_" + state)

        offer_sdp = prepare_offer(sdp_offer)
        logger.info("whatsapp_call[%s] SDP offer: %s", self.call_id, json.dumps(summarize_sdp(offer_sdp)))
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))

        for tr in pc.getTransceivers():
            try:
                dtls = tr.receiver.transport

                def _dtls_state(dtls=dtls):
                    logger.info("whatsapp_call[%s] DTLS state: %s (role=%s)",
                                self.call_id, dtls.state, getattr(dtls, "_role", "?"))

                dtls.on("statechange", _dtls_state)
            except Exception:
                pass
            logger.info("whatsapp_call[%s] transceiver mid=%s direction=%s",
                        self.call_id, tr.mid, tr.direction)

        t0 = time.monotonic()
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        answer_sdp = whatsapp_sdp(pc.localDescription.sdp)
        logger.info("whatsapp_call[%s] SDP answer (gathered in %d ms): %s", self.call_id,
                    int((time.monotonic() - t0) * 1000), json.dumps(summarize_sdp(answer_sdp)))
        ice = self._ice_transport()
        if ice is not None:
            logger.info("whatsapp_call[%s] ICE role: %s", self.call_id,
                        "controlling" if ice._connection.ice_controlling else "controlled")
        problems = answer_problems(answer_sdp)
        if problems:
            logger.warning("whatsapp_call[%s] SDP answer problems: %s", self.call_id, "; ".join(problems))
        summary = summarize_sdp(answer_sdp)
        kinds = {c.split(":", 1)[0] for c in summary.get("candidates") or []}
        if "srflx" not in kinds and "relay" not in kinds:
            logger.warning(
                "whatsapp_call[%s] SDP answer has no srflx/relay candidates (STUN/TURN failed); "
                "Meta cannot reach a private host candidate — set WHATSAPP_TURN_URL or fix STUN/UDP",
                self.call_id,
            )
        self.answer_sdp = answer_sdp
        return answer_sdp

    async def accept_call(self, sdp_offer: str, *, xai_ready: Optional[asyncio.Task] = None) -> str:
        """Create the peer, pre_accept with the answer, wait for ICE+DTLS, then accept
        with the identical answer. Raises CallSetupError when Graph refuses."""
        answer_sdp = await self._setup_peer(sdp_offer)
        session = {"session": {"sdp_type": "answer", "sdp": answer_sdp}}

        res = await self.post_calls_action("pre_accept", session)
        if not self._graph_ok(res):
            raise CallSetupError(f"pre_accept refused: {_graph_error_text(res)}")

        wait = _env_float(ENV_ACCEPT_WAIT, DEFAULT_ACCEPT_WAIT_SECONDS)
        if wait > 0 and not self.media_connected.is_set():
            try:
                await asyncio.wait_for(self.media_connected.wait(), timeout=wait)
            except asyncio.TimeoutError:
                pass
        if self.closed.is_set():
            raise CallSetupError(f"media failed before accept ({self.end_reason})")
        if self.media_connected.is_set():
            logger.info("whatsapp_call[%s] media connected before accept (%s)", self.call_id, self._selected_pair())
        else:
            logger.warning(
                "whatsapp_call[%s] media not connected after %.0fs (ICE=%s, conn=%s, pair=%s); "
                "accepting anyway — if the call is silent, configure WHATSAPP_TURN_URL "
                "(Cloudflare Calls TURN or coturn) or ensure UDP to this host is not blocked "
                "by dual-WAN NAT on the router",
                self.call_id, wait, self.pc.iceConnectionState, self.pc.connectionState, self._selected_pair(),
            )

        if xai_ready is not None:
            await xai_ready  # raises if the voice brain could not connect

        res = await self.post_calls_action("accept", session)
        if not self._graph_ok(res):
            raise CallSetupError(f"accept refused: {_graph_error_text(res)}")
        self.accepted = True
        self.outgoing_track.live = True
        return answer_sdp

    # ── xAI ──────────────────────────────────────────────────────────
    async def connect_xai(self) -> None:
        """Connect to xAI realtime voice brain (same session config as browser live voice)."""
        if self.upstream is not None:
            return
        import websockets
        from app.services.max.voice_live import XAI_REALTIME_URL, session_update_event
        key = os.getenv("XAI_API_KEY", "")
        if not key:
            raise CallSetupError("XAI_API_KEY is not set")
        url = f"{XAI_REALTIME_URL}?model={voice_model()}"
        t0 = time.monotonic()
        instr_task = asyncio.create_task(fresh_instructions())
        try:
            self.upstream = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Bearer {key}"},
                ping_interval=20,
                ping_timeout=20,
                max_size=8 * 1024 * 1024,
                open_timeout=15,
            )
        except Exception as exc:
            instr_task.cancel()
            resp = getattr(exc, "response", None)
            code = getattr(resp, "status_code", None)
            raise CallSetupError(f"xAI connect failed: {type(exc).__name__}{f' HTTP {code}' if code else ''}")
        logger.info("whatsapp_call[%s] xAI websocket open model=%s voice=%s (%d ms)",
                    self.call_id, voice_model(), voice_name(), int((time.monotonic() - t0) * 1000))
        instructions, _meta = await instr_task
        try:
            from app.services.max.voice_live import language_section, last_call_language
            instructions += language_section(last_call_language())
        except Exception:
            pass
        instructions += WHATSAPP_CALL_NOTE
        await self.send_upstream_json(session_update_event(instructions))
        logger.info("whatsapp_call[%s] xAI session.update sent (pcm 24k in/out, %d chars instructions)",
                    self.call_id, len(instructions))
        self.record_transcript("start")

    async def greet_when_ready(self) -> None:
        """Business speaks first on a WhatsApp call: one response.create after the
        call is accepted and xAI confirmed the session."""
        if not greeting_enabled():
            return
        try:
            try:
                await asyncio.wait_for(self.session_ready.wait(), timeout=6)
            except asyncio.TimeoutError:
                logger.warning("whatsapp_call[%s] no session.updated from xAI after 6s; greeting anyway", self.call_id)
            if not self.closed.is_set() and self.active_response is None:
                await self.send_upstream_json({"type": "response.create"})
                logger.info("whatsapp_call[%s] greeting requested (response.create)", self.call_id)
        except asyncio.CancelledError:
            pass

    async def pump_xai_to_webrtc(self) -> None:
        """Listen to xAI realtime responses, parse function calls & audio deltas."""
        try:
            async for raw in self.upstream:
                if self.closed.is_set():
                    break
                try:
                    event = json.loads(raw)
                except Exception:
                    continue
                etype = event.get("type", "")
                self.xai_events[etype] = self.xai_events.get(etype, 0) + 1
                if etype in ("response.output_audio.delta", "response.audio.delta"):
                    rid = event.get("response_id")
                    if rid and rid in self.cancelled_responses:
                        continue
                    try:
                        pcm = base64.b64decode(event.get("delta") or "")
                        self.audio_deltas += 1
                        self.bytes_from_xai += len(pcm)
                        if self.audio_deltas == 1:
                            logger.info("whatsapp_call[%s] first xAI audio delta", self.call_id)
                        self.outgoing_track.push_pcm(pcm)
                        self.touch_activity()
                    except Exception:
                        pass
                    continue
                if etype.endswith(".delta"):
                    continue  # transcript / argument deltas: counted, not logged
                if etype == "error":
                    err = event.get("error") or {}
                    msg = err.get("message") if isinstance(err, dict) else str(err)
                    code = err.get("code") if isinstance(err, dict) else None
                    if code in ("response_cancel_not_active",) or "no active response" in str(msg).lower():
                        continue
                    logger.warning("whatsapp_call[%s] xAI error: code=%s %s", self.call_id, code, _redact(msg)[:300])
                    continue
                logger.info("whatsapp_call[%s] xAI event: %s", self.call_id, etype)
                if etype == "session.updated":
                    self.session_ready.set()
                elif etype == "input_audio_buffer.speech_started":
                    self.touch_activity()
                    if self.active_response and self.active_response not in self.cancelled_responses:
                        self.cancelled_responses.add(self.active_response)
                        await self.send_upstream_json({"type": "response.cancel"})
                        self.outgoing_track.flush()
                elif etype == "conversation.item.input_audio_transcription.completed":
                    transcript = str(event.get("transcript") or "")
                    self.record_transcript("add_user", transcript, event.get("item_id"))
                elif etype in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
                    transcript = str(event.get("transcript") or "")
                    rid = event.get("response_id")
                    self.record_transcript("add_assistant", transcript, rid, rid in self.cancelled_responses)
                elif etype == "response.created":
                    self.active_response = (event.get("response") or {}).get("id") or event.get("response_id")
                elif etype == "response.function_call_arguments.done":
                    rid = event.get("response_id") or self.active_response or "_"
                    name = event.get("name") or ""
                    call_id = event.get("call_id") or ""
                    try:
                        args = json.loads(event.get("arguments") or "{}")
                    except Exception:
                        args = {}
                    t = asyncio.create_task(self._run_voice_tool(name, call_id, args))
                    self.pending_tools.setdefault(rid, []).append(t)
                elif etype == "response.done":
                    resp = event.get("response") or {}
                    rid = resp.get("id") or event.get("response_id") or self.active_response
                    if resp.get("status") and resp.get("status") != "completed":
                        logger.info("whatsapp_call[%s] xAI response %s status=%s", self.call_id, rid, resp.get("status"))
                    if rid == self.active_response:
                        self.active_response = None
                    tasks = self.pending_tools.pop(rid, None) or self.pending_tools.pop("_", None)
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        for r in results:
                            if isinstance(r, tuple):
                                cid, out = r
                                await self.send_upstream_json({
                                    "type": "conversation.item.create",
                                    "item": {"type": "function_call_output", "call_id": cid, "output": out},
                                })
                        if rid not in self.cancelled_responses:
                            await self.send_upstream_json({"type": "response.create"})
            if not self.closed.is_set():
                logger.info("whatsapp_call[%s] xAI websocket closed by server", self.call_id)
                self.close("xai_closed")
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.info("whatsapp_call[%s] xAI pump ended: %s", self.call_id, _redact(exc))
            self.close("xai_pump_ended")

    async def _run_voice_tool(self, name: str, call_id: str, args: dict[str, Any]) -> tuple[str, str]:
        try:
            data = await asyncio.to_thread(
                run_voice_tool, name, args, call_id=self.call_id, conversation_id=self.conversation_id
            )
        except Exception as exc:
            data = {"success": False, "error": str(exc)}
        ok = bool(data.get("success"))
        logger.info("whatsapp_call[%s] tool %s ok=%s", self.call_id, name, ok)
        self.record_transcript("add_tool", name, args, ok, "")

        # Mid-call document check: If a quote was created or fetched during the call, send as draft PDF
        await self._check_and_send_mid_call_documents(name, data)

        return call_id, json.dumps(data, default=str)

    async def _check_and_send_mid_call_documents(self, name: str, data: dict[str, Any]) -> None:
        """If Max produced/retrieved a quote, send the PDF draft to the founder's WhatsApp chat."""
        try:
            res = data.get("result") if isinstance(data, dict) else None
            quote_id = None
            quote_number = "Quote"
            if isinstance(res, dict):
                quote_id = res.get("id") or res.get("quote_id")
                quote_number = res.get("quote_number") or res.get("id") or "Quote"
            if not quote_id and name == "get_quote":
                quote_id = (data.get("result") or {}).get("id")

            if quote_id:
                from app.services.quote_pdf_service import generate_quote_pdf
                pdf_bytes = await asyncio.to_thread(generate_quote_pdf, str(quote_id))
                if pdf_bytes:
                    from app.services.max.whatsapp_channel import (
                        _pdf_filename,
                        _post_graph,
                        upload_media,
                    )
                    filename = _pdf_filename(f"{quote_number}.pdf")
                    media_id = upload_media(
                        pdf_bytes, "application/pdf", filename, http_upload=None
                    )
                    if hasattr(media_id, "__await__"):
                        media_id = await media_id
                    await _post_graph({
                        "messaging_product": "whatsapp",
                        "recipient_type": "individual",
                        "to": self.caller,
                        "type": "document",
                        "document": {
                            "id": media_id,
                            "filename": filename,
                            "caption": "Draft quote from live voice call. Not sent to client.",
                        },
                    }, http_post=self.http_post)
                    logger.info("whatsapp_call[%s] sent mid-call draft quote PDF: %s", self.call_id, filename)
        except Exception as exc:
            logger.warning("whatsapp_call[%s] mid-call document send skipped: %s", self.call_id, exc)

    # ── Lifespan ─────────────────────────────────────────────────────
    async def monitor_lifespan(self) -> None:
        """Enforces max duration, idle timeout, and media-never-connected timeout."""
        media_timeout = _env_float(ENV_MEDIA_TIMEOUT, DEFAULT_MEDIA_TIMEOUT_SECONDS)
        last_stats = time.monotonic()
        try:
            while not self.closed.is_set():
                await asyncio.sleep(1)
                now = time.monotonic()
                elapsed = now - self.started
                if elapsed >= self.max_duration:
                    self.close("max_duration_reached")
                    break
                if media_timeout and not self.media_connected.is_set() and elapsed >= media_timeout:
                    logger.error("whatsapp_call[%s] media never connected in %.0fs (ICE=%s conn=%s)",
                                 self.call_id, elapsed, self.pc.iceConnectionState if self.pc else "-",
                                 self.pc.connectionState if self.pc else "-")
                    self.close("media_timeout")
                    break
                if now - self.last_activity >= DEFAULT_IDLE_TIMEOUT_SECONDS:
                    self.close("idle_timeout")
                    break
                if now - last_stats >= 15:
                    last_stats = now
                    logger.info("whatsapp_call[%s] stats: %s", self.call_id, self.stats_line())
        except asyncio.CancelledError:
            pass

    def stats_line(self) -> str:
        return (
            f"frames_in={self.frames_in} bytes_to_xai={self.bytes_to_xai} "
            f"xai_audio_deltas={self.audio_deltas} bytes_from_xai={self.bytes_from_xai} "
            f"frames_out={self.outgoing_track.frames_sent} audio_frames_out={self.outgoing_track.audio_frames_sent} "
            f"ice={self.pc.iceConnectionState if self.pc else '-'} conn={self.pc.connectionState if self.pc else '-'}"
        )

    def close(self, reason: str = "hangup") -> None:
        if self.closed.is_set():
            return
        self.end_reason = reason
        self.closed.set()
        logger.info("whatsapp_call[%s] closing, reason: %s", self.call_id, reason)

    def start_supervisor(self) -> None:
        """When Max ends the call itself (media failure, caps, xAI gone), clean up
        and tell Meta so the caller is not left in a silent call."""
        async def _supervise() -> None:
            await self.closed.wait()
            if not self._terminated:
                await self.terminate(self.end_reason, notify_meta=self.accepted)
        self._supervisor = asyncio.create_task(_supervise())

    async def terminate(self, reason: str = "hangup", *, notify_meta: bool = False) -> None:
        self.close(reason)
        if self._terminated:
            return
        self._terminated = True
        logger.info("whatsapp_call[%s] final stats: %s xai_events=%s", self.call_id, self.stats_line(),
                    json.dumps(dict(sorted(self.xai_events.items()))))
        if notify_meta:
            await self.post_calls_action("terminate")
        # Cancel background tasks
        for t in self.tasks:
            t.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

        if self.pc:
            try:
                await self.pc.close()
            except Exception:
                pass
        if self.upstream:
            try:
                await self.upstream.close()
            except Exception:
                pass

        duration = round(time.monotonic() - self.started, 1)
        if self.transcript:
            try:
                await asyncio.to_thread(self.transcript.finish, duration, self.end_reason)
            except Exception as exc:
                logger.warning("whatsapp_call[%s] finish transcript error: %s", self.call_id, exc)

        _active_whatsapp_calls.pop(self.call_id, None)
        logger.info(
            "whatsapp_call[%s] call ended duration_s=%.1f reason=%s (no audio or secrets logged)",
            self.call_id,
            duration,
            self.end_reason,
        )


def _graph_error_text(res: dict[str, Any]) -> str:
    err = res.get("error") if isinstance(res.get("error"), dict) else {}
    details = (err.get("error_data") or {}).get("details") if isinstance(err.get("error_data"), dict) else ""
    return _redact(
        f"HTTP {res.get('_http_status')} code={err.get('code')} subcode={err.get('error_subcode')} "
        f"{err.get('message') or res.get('text') or ''} {details or ''}"
    ).strip()[:400]


async def handle_call_connect(
    call_id: str,
    from_number: str,
    sdp_offer: str,
    *,
    http_post: Optional[Callable[..., Any]] = None,
    upstream_ws: Any = None,
) -> dict[str, Any]:
    """Handles an incoming connect event with SDP offer (full setup, awaited)."""
    from app.services.max.whatsapp_channel import is_allowlisted

    # 1. Allowlist check
    if not is_allowlisted(from_number):
        logger.warning("Rejecting call %s from non-allowlisted number %s", call_id, from_number)
        temp_call = WhatsAppVoiceCall(call_id, from_number, http_post=http_post)
        await temp_call.post_calls_action("reject")
        return {"action": "rejected", "call_id": call_id, "reason": "not_allowlisted"}

    # 2. Check calling enabled feature flag
    if not calling_enabled():
        logger.warning("Rejecting call %s: WHATSAPP_CALLING_ENABLED is off", call_id)
        temp_call = WhatsAppVoiceCall(call_id, from_number, http_post=http_post)
        await temp_call.post_calls_action("reject")
        return {"action": "rejected", "call_id": call_id, "reason": "calling_disabled"}

    if call_id in _active_whatsapp_calls:
        logger.info("whatsapp_call[%s] duplicate connect webhook ignored", call_id)
        return {"action": "duplicate", "call_id": call_id}

    if not sdp_offer:
        logger.error("whatsapp_call[%s] connect webhook without an SDP offer", call_id)
        return {"action": "failed", "call_id": call_id, "error": "no sdp offer"}

    # 3. Create call session and accept
    call = WhatsAppVoiceCall(call_id, from_number, http_post=http_post, upstream_ws=upstream_ws)
    _active_whatsapp_calls[call_id] = call
    logger.info("whatsapp_call[%s] connect from=%s; setting up media + voice brain", call_id, from_number)

    xai_task = asyncio.create_task(call.connect_xai())
    try:
        sdp_answer = await call.accept_call(sdp_offer, xai_ready=xai_task)

        logger.info(
            "whatsapp_call[%s] call started from=%s (no audio or secrets logged)",
            call_id,
            from_number,
        )

        # Launch background audio pump, lifespan monitor, greeting and supervisor
        pump_task = asyncio.create_task(call.pump_xai_to_webrtc())
        monitor_task = asyncio.create_task(call.monitor_lifespan())
        greet_task = asyncio.create_task(call.greet_when_ready())
        call.tasks.extend([pump_task, monitor_task, greet_task])
        call.start_supervisor()

        return {"action": "accepted", "call_id": call_id, "sdp_answer": sdp_answer}
    except Exception as exc:
        if not xai_task.done():
            xai_task.cancel()
        logger.error("whatsapp_call[%s] setup failed: %s", call_id, _redact(exc))
        if not call.accepted and call.end_reason != "webhook_terminate":
            # Do not leave the caller ringing: reject (best effort).
            await call.post_calls_action("reject")
        await call.terminate("setup_error", notify_meta=call.accepted)
        return {"action": "failed", "call_id": call_id, "error": _redact(exc)}


async def schedule_call_connect(
    call_id: str,
    from_number: str,
    sdp_offer: str,
    *,
    http_post: Optional[Callable[..., Any]] = None,
    upstream_ws: Any = None,
) -> dict[str, Any]:
    """Webhook entry point. Rejections are answered inline; an allowlisted call is
    set up in a background task so Meta gets its 200 at once (setup takes several
    seconds: gathering, pre_accept, ICE/DTLS, accept). WHATSAPP_CALL_SETUP_INLINE=1
    awaits the full setup instead."""
    from app.services.max.whatsapp_channel import is_allowlisted

    if setup_inline() or not is_allowlisted(from_number) or not calling_enabled():
        return await handle_call_connect(call_id, from_number, sdp_offer,
                                         http_post=http_post, upstream_ws=upstream_ws)
    if call_id in _active_whatsapp_calls:
        logger.info("whatsapp_call[%s] duplicate connect webhook ignored", call_id)
        return {"action": "duplicate", "call_id": call_id}

    async def _run() -> None:
        try:
            await handle_call_connect(call_id, from_number, sdp_offer,
                                      http_post=http_post, upstream_ws=upstream_ws)
        except Exception as exc:  # handle_call_connect already logs; belt and braces
            logger.error("whatsapp_call[%s] background setup crashed: %s", call_id, _redact(exc))

    task = asyncio.create_task(_run())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return {"action": "accepting", "call_id": call_id}


async def handle_call_terminate(call_id: str, reason: str = "caller_terminate") -> dict[str, Any]:
    call = _active_whatsapp_calls.get(call_id)
    if call:
        await call.terminate(reason)
        return {"action": "terminated", "call_id": call_id, "found": True}
    return {"action": "terminated", "call_id": call_id, "found": False}
