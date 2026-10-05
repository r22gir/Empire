"""WhatsApp Business Calling API — WebRTC bridge to Max xAI Realtime voice brain.

Handles user-initiated inbound WhatsApp calls to Max.
- Allowlist check: Only founder numbers can call; all other callers are rejected.
- WebRTC Peer: aiortc endpoint handling Meta's SDP offer, generating SDP answer.
- Graph Calls API: pre_accept -> accept with SDP answer, or reject.
- Audio Relay: Bidirectional audio bridge between WebRTC audio track (Opus 48k)
  and xAI realtime session (PCM16 24k).
- Lifespan & cleanup: Handles terminate event, caller hangup, timeout cap (default 30 min),
  and idle timeout.
- Mid-call documents: If Max generates quotes/drawings during the call, sends them
  as draft PDFs into the founder's WhatsApp chat.
"""
from __future__ import annotations

import asyncio
import fractions
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
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

DEFAULT_STUN_SERVER = "stun:stun.l.google.com:19302"
DEFAULT_MAX_CALL_SECONDS = 1800  # 30 minutes
DEFAULT_IDLE_TIMEOUT_SECONDS = 120  # 2 minutes of complete silence / inactivity
SAMPLE_RATE = 24000  # xAI realtime audio rate
OPUS_RATE = 48000    # WebRTC audio rate

_active_whatsapp_calls: dict[str, "WhatsAppVoiceCall"] = {}


def calling_enabled() -> bool:
    raw = os.getenv(ENV_CALLING_ENABLED, "0").strip().lower()
    return raw in ("1", "true", "yes", "on")


def max_call_duration_seconds() -> int:
    try:
        return max(30, int(os.getenv(ENV_CALL_MAX_SECONDS, str(DEFAULT_MAX_CALL_SECONDS))))
    except ValueError:
        return DEFAULT_MAX_CALL_SECONDS


def get_ice_servers() -> list[RTCIceServer]:
    servers = [RTCIceServer(urls=DEFAULT_STUN_SERVER)]
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
        try:
            while not self.call.closed.is_set():
                frame = await self.track.recv()
                self.call.touch_activity()
                resampled_frames = self.resampler.resample(frame)
                for r_frame in resampled_frames:
                    pcm_bytes = bytes(r_frame.planes[0])
                    if pcm_bytes:
                        await self.call.send_audio_to_xai(pcm_bytes)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.info("whatsapp_call[%s] incoming audio ended: %s", self.call.call_id, exc)


class XAIAudioTrack(MediaStreamTrack):
    """Feeds PCM16 24k audio received from xAI upstream into WebRTC as 48k audio frames."""

    kind = "audio"

    def __init__(self):
        super().__init__()
        self.queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._resampler = av.AudioResampler(
            format="s16",
            layout="mono",
            rate=OPUS_RATE,
        )
        self._timestamp = 0
        # 20ms at 24000Hz mono s16 is 480 samples = 960 bytes
        self._samples_per_frame = 480
        self._bytes_per_chunk = self._samples_per_frame * 2
        self._buffer = bytearray()

    def push_pcm(self, pcm: bytes) -> None:
        if pcm:
            self._buffer.extend(pcm)
            while len(self._buffer) >= self._bytes_per_chunk:
                chunk = bytes(self._buffer[:self._bytes_per_chunk])
                del self._buffer[:self._bytes_per_chunk]
                self.queue.put_nowait(chunk)

    def flush(self) -> None:
        self._buffer.clear()
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def recv(self) -> av.AudioFrame:
        try:
            chunk = await asyncio.wait_for(self.queue.get(), timeout=0.04)
        except asyncio.TimeoutError:
            # Output silence if queue starved
            chunk = b"\x00" * self._bytes_per_chunk

        frame = av.AudioFrame(format="s16", layout="mono", samples=self._samples_per_frame)
        frame.planes[0].update(chunk)
        frame.sample_rate = SAMPLE_RATE
        frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
        frame.pts = self._timestamp

        resampled = self._resampler.resample(frame)
        self._timestamp += self._samples_per_frame
        if resampled:
            out_frame = resampled[0]
            out_frame.pts = self._timestamp
            out_frame.time_base = fractions.Fraction(1, OPUS_RATE)
            return out_frame

        silence = av.AudioFrame(format="s16", layout="mono", samples=960)
        silence.planes[0].update(b"\x00" * 1920)
        silence.sample_rate = OPUS_RATE
        silence.time_base = fractions.Fraction(1, OPUS_RATE)
        silence.pts = self._timestamp
        return silence


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
            import base64
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

    async def post_calls_action(self, action: str, data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """POST /{PHONE_NUMBER_ID}/calls with call_id and action."""
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
        if self.http_post is None:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=body, headers=headers)
                return res.json() if res.status_code < 400 else {"status": res.status_code, "text": res.text}
        else:
            res = self.http_post(url, body, headers)
            if hasattr(res, "__await__"):
                res = await res
            if hasattr(res, "json"):
                data = res.json()
                if hasattr(data, "__await__"):
                    data = await data
                return data
            return res if isinstance(res, dict) else {"status": 200}

    async def accept_call(self, sdp_offer: str) -> str:
        """Create RTCPeerConnection, set remote offer, create answer, pre_accept & accept."""
        config = RTCConfiguration(iceServers=get_ice_servers())
        self.pc = RTCPeerConnection(configuration=config)
        self.pc.addTrack(self.outgoing_track)

        @self.pc.on("track")
        def on_track(track):
            if track.kind == "audio":
                audio_sink = AudioTrackToXAI(track, self)
                t = asyncio.create_task(audio_sink.run())
                self.tasks.append(t)

        @self.pc.on("iceconnectionstatechange")
        def on_ice():
            logger.info("whatsapp_call[%s] ICE state: %s", self.call_id, self.pc.iceConnectionState)
            if self.pc.iceConnectionState in ("failed", "disconnected", "closed"):
                self.close("ice_disconnected")

        # 1. Set Remote Description
        offer = RTCSessionDescription(sdp=sdp_offer, type="offer")
        await self.pc.setRemoteDescription(offer)

        # 2. Create and set Local Description (Answer)
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        # 3. Graph API: pre_accept
        await self.post_calls_action("pre_accept")

        # 4. Graph API: accept with SDP answer
        await self.post_calls_action("accept", {
            "session": {
                "sdp_type": "answer",
                "sdp": self.pc.localDescription.sdp,
            }
        })

        return self.pc.localDescription.sdp

    async def connect_xai(self) -> None:
        """Connect to xAI realtime voice brain."""
        if self.upstream is not None:
            return
        import websockets
        from app.services.max.voice_live import XAI_REALTIME_URL, session_update_event
        key = os.getenv("XAI_API_KEY", "")
        url = f"{XAI_REALTIME_URL}?model={voice_model()}"
        instr_task = asyncio.create_task(fresh_instructions())
        self.upstream = await websockets.connect(
            url,
            additional_headers={"Authorization": f"Bearer {key}"},
            ping_interval=20,
            ping_timeout=20,
            max_size=8 * 1024 * 1024,
            open_timeout=15,
        )
        instructions, _ = await instr_task
        await self.send_upstream_json(session_update_event(instructions))
        self.record_transcript("start")

    async def pump_xai_to_webrtc(self) -> None:
        """Listen to xAI realtime responses, parse function calls & audio deltas."""
        import base64
        try:
            async for raw in self.upstream:
                if self.closed.is_set():
                    break
                try:
                    event = json.loads(raw)
                except Exception:
                    continue
                etype = event.get("type", "")
                if etype in ("response.output_audio.delta", "response.audio.delta"):
                    rid = event.get("response_id")
                    if rid and rid in self.cancelled_responses:
                        continue
                    try:
                        pcm = base64.b64decode(event.get("delta") or "")
                        self.outgoing_track.push_pcm(pcm)
                        self.touch_activity()
                    except Exception:
                        pass
                elif etype == "input_audio_buffer.speech_started":
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
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.info("whatsapp_call[%s] xAI pump ended: %s", self.call_id, exc)
            self.close("xai_pump_ended")

    async def _run_voice_tool(self, name: str, call_id: str, args: dict[str, Any]) -> tuple[str, str]:
        try:
            data = await asyncio.to_thread(
                run_voice_tool, name, args, call_id=self.call_id, conversation_id=self.conversation_id
            )
        except Exception as exc:
            data = {"success": False, "error": str(exc)}
        ok = bool(data.get("success"))
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

    async def monitor_lifespan(self) -> None:
        """Enforces max duration and idle timeouts."""
        try:
            while not self.closed.is_set():
                await asyncio.sleep(5)
                elapsed = time.monotonic() - self.started
                if elapsed >= self.max_duration:
                    self.close("max_duration_reached")
                    break
                idle = time.monotonic() - self.last_activity
                if idle >= DEFAULT_IDLE_TIMEOUT_SECONDS:
                    self.close("idle_timeout")
                    break
        except asyncio.CancelledError:
            pass

    def close(self, reason: str = "hangup") -> None:
        if self.closed.is_set():
            return
        self.end_reason = reason
        self.closed.set()
        logger.info("whatsapp_call[%s] closing, reason: %s", self.call_id, reason)

    async def terminate(self, reason: str = "hangup") -> None:
        self.close(reason)
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


async def handle_call_connect(
    call_id: str,
    from_number: str,
    sdp_offer: str,
    *,
    http_post: Optional[Callable[..., Any]] = None,
    upstream_ws: Any = None,
) -> dict[str, Any]:
    """Handles an incoming connect event with SDP offer."""
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

    # 3. Create call session and accept
    call = WhatsAppVoiceCall(call_id, from_number, http_post=http_post, upstream_ws=upstream_ws)
    _active_whatsapp_calls[call_id] = call

    try:
        await call.connect_xai()
        sdp_answer = await call.accept_call(sdp_offer)

        logger.info(
            "whatsapp_call[%s] call started from=%s (no audio or secrets logged)",
            call_id,
            from_number,
        )

        # Launch background audio pump and lifespan monitor
        pump_task = asyncio.create_task(call.pump_xai_to_webrtc())
        monitor_task = asyncio.create_task(call.monitor_lifespan())
        call.tasks.extend([pump_task, monitor_task])

        return {"action": "accepted", "call_id": call_id, "sdp_answer": sdp_answer}
    except Exception as exc:
        logger.exception("Failed to accept call %s: %s", call_id, exc)
        await call.terminate("error")
        return {"action": "failed", "call_id": call_id, "error": str(exc)}


async def handle_call_terminate(call_id: str, reason: str = "caller_terminate") -> dict[str, Any]:
    call = _active_whatsapp_calls.get(call_id)
    if call:
        await call.terminate(reason)
        return {"action": "terminated", "call_id": call_id, "found": True}
    return {"action": "terminated", "call_id": call_id, "found": False}
