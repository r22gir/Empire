"""
Voiceprint Verification (v6.0)

CPU-only speaker verification for Telegram voice messages.
Uses resemblyzer (GE2E model) for speaker embedding extraction
and cosine similarity for verification.

Workflow:
  1. Founder enrolls voice via /voiceprint command (saves embedding)
  2. On each voice message, extract embedding and compare to enrolled profile
  3. If similarity < threshold, flag as unverified and alert

Falls back gracefully if resemblyzer is not installed — voice messages
still work but without identity verification.

Install: pip install resemblyzer
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger("max.security.voiceprint")

VOICEPRINT_DIR = Path.home() / "empire-repo" / "backend" / "data" / "security" / "voiceprints"
VOICEPRINT_DIR.mkdir(parents=True, exist_ok=True)

# Similarity threshold for voice verification (0.0 - 1.0)
# Higher = stricter. 0.75 is a good balance for single-speaker verification.
SIMILARITY_THRESHOLD = 0.75

# Minimum audio duration for reliable embedding (seconds)
MIN_AUDIO_DURATION = 1.5


class VoiceprintVerifier:
    """Speaker verification using GE2E voice embeddings."""

    def __init__(self):
        self._encoder = None
        self._available = None
        self._enrolled_profiles: Dict[str, np.ndarray] = {}
        self._load_enrolled_profiles()

    @property
    def available(self) -> bool:
        """Check if resemblyzer is installed and usable."""
        if self._available is None:
            try:
                from resemblyzer import VoiceEncoder
                self._available = True
            except ImportError:
                logger.info("resemblyzer not installed — voiceprint verification disabled")
                self._available = False
        return self._available

    @property
    def encoder(self):
        """Lazy-load the voice encoder (downloads model on first use)."""
        if self._encoder is None and self.available:
            try:
                from resemblyzer import VoiceEncoder
                self._encoder = VoiceEncoder("cpu")
                logger.info("VoiceEncoder loaded (CPU mode)")
            except Exception as e:
                logger.error("Failed to load VoiceEncoder: %s", e)
                self._available = False
        return self._encoder

    def _load_enrolled_profiles(self):
        """Load all enrolled voiceprints from disk."""
        for f in VOICEPRINT_DIR.glob("*.npy"):
            user_id = f.stem
            try:
                embedding = np.load(f)
                self._enrolled_profiles[user_id] = embedding
                logger.info("Loaded voiceprint for user: %s", user_id)
            except Exception as e:
                logger.error("Failed to load voiceprint %s: %s", f, e)

    def _audio_to_wav(self, audio_path: Path) -> Optional[Path]:
        """Convert audio file to WAV format using ffmpeg."""
        wav_path = audio_path.with_suffix(".wav")
        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(audio_path),
                    "-ar", "16000", "-ac", "1", "-f", "wav",
                    str(wav_path),
                ],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and wav_path.exists():
                return wav_path
            logger.error("ffmpeg conversion failed: %s", result.stderr[:200])
        except FileNotFoundError:
            logger.error("ffmpeg not found — install with: sudo apt install ffmpeg")
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg conversion timed out")
        except Exception as e:
            logger.error("Audio conversion failed: %s", e)
        return None

    def _extract_embedding(self, audio_path: Path) -> Optional[np.ndarray]:
        """Extract voice embedding from an audio file."""
        if not self.encoder:
            return None

        from resemblyzer import preprocess_wav

        # Convert to WAV if needed
        if audio_path.suffix.lower() not in (".wav",):
            wav_path = self._audio_to_wav(audio_path)
            if not wav_path:
                return None
            cleanup_wav = True
        else:
            wav_path = audio_path
            cleanup_wav = False

        try:
            wav = preprocess_wav(wav_path)

            # Check minimum duration
            duration = len(wav) / 16000  # 16kHz sample rate
            if duration < MIN_AUDIO_DURATION:
                logger.warning("Audio too short (%.1fs) for reliable embedding", duration)
                return None

            embedding = self.encoder.embed_utterance(wav)
            return embedding
        except Exception as e:
            logger.error("Embedding extraction failed: %s", e)
            return None
        finally:
            if cleanup_wav and wav_path and wav_path.exists():
                wav_path.unlink(missing_ok=True)

    def enroll(self, user_id: str, audio_path: Path) -> Dict[str, Any]:
        """Enroll a voice profile from an audio sample.

        For best results, use 5-10 seconds of clear speech.

        Returns:
            {"success": bool, "message": str, "duration": float}
        """
        if not self.available:
            return {
                "success": False,
                "message": "resemblyzer not installed. Install with: pip install resemblyzer",
            }

        embedding = self._extract_embedding(audio_path)
        if embedding is None:
            return {
                "success": False,
                "message": "Failed to extract voice embedding. Ensure clear speech, at least 2 seconds.",
            }

        # Save embedding
        npy_path = VOICEPRINT_DIR / f"{user_id}.npy"
        np.save(npy_path, embedding)
        self._enrolled_profiles[user_id] = embedding

        logger.info("Voiceprint enrolled for user: %s", user_id)
        return {
            "success": True,
            "message": f"Voice profile enrolled for {user_id}. Future voice messages will be verified.",
        }

    def verify(self, user_id: str, audio_path: Path) -> Dict[str, Any]:
        """Verify a voice sample against the enrolled profile.

        Returns:
            {
                "verified": bool,
                "similarity": float (0.0-1.0),
                "threshold": float,
                "message": str,
                "available": bool,
            }
        """
        if not self.available:
            return {
                "verified": True,  # Pass through if not available
                "similarity": 1.0,
                "threshold": SIMILARITY_THRESHOLD,
                "message": "Voiceprint verification not available (resemblyzer not installed)",
                "available": False,
            }

        if user_id not in self._enrolled_profiles:
            return {
                "verified": True,  # No profile = pass through (not enrolled yet)
                "similarity": 0.0,
                "threshold": SIMILARITY_THRESHOLD,
                "message": f"No voiceprint enrolled for {user_id}. Use /voiceprint to enroll.",
                "available": True,
            }

        embedding = self._extract_embedding(audio_path)
        if embedding is None:
            return {
                "verified": False,
                "similarity": 0.0,
                "threshold": SIMILARITY_THRESHOLD,
                "message": "Failed to extract voice embedding from audio.",
                "available": True,
            }

        # Cosine similarity
        enrolled = self._enrolled_profiles[user_id]
        similarity = float(np.dot(embedding, enrolled) / (
            np.linalg.norm(embedding) * np.linalg.norm(enrolled)
        ))

        verified = similarity >= SIMILARITY_THRESHOLD

        if not verified:
            logger.warning(
                "[VOICEPRINT] Verification FAILED for %s: similarity=%.3f (threshold=%.3f)",
                user_id, similarity, SIMILARITY_THRESHOLD,
            )
            # Log security event
            self._log_failed_verification(user_id, similarity)

        return {
            "verified": verified,
            "similarity": round(similarity, 4),
            "threshold": SIMILARITY_THRESHOLD,
            "message": "Voice verified" if verified else "Voice does NOT match enrolled profile",
            "available": True,
        }

    def is_enrolled(self, user_id: str) -> bool:
        """Check if a user has an enrolled voiceprint."""
        return user_id in self._enrolled_profiles

    def delete_profile(self, user_id: str) -> bool:
        """Delete an enrolled voiceprint."""
        npy_path = VOICEPRINT_DIR / f"{user_id}.npy"
        if npy_path.exists():
            npy_path.unlink()
        if user_id in self._enrolled_profiles:
            del self._enrolled_profiles[user_id]
            logger.info("Voiceprint deleted for user: %s", user_id)
            return True
        return False

    def _log_failed_verification(self, user_id: str, similarity: float):
        """Log failed verification to security audit."""
        try:
            from .sanitizer import AUDIT_DIR
            log_path = AUDIT_DIR / "audit_log.jsonl"
            entry = {
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
                "threat_type": "voiceprint_mismatch",
                "reason": f"Voice similarity {similarity:.3f} below threshold {SIMILARITY_THRESHOLD}",
                "channel": "telegram",
                "session_id": user_id,
                "text_preview": "",
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        # Alert via Telegram if possible
        try:
            from app.services.max.brain.memory_store import MemoryStore
            ms = MemoryStore()
            ms.add_memory(
                category="security",
                subcategory="voiceprint_alert",
                content=f"Voice verification FAILED for {user_id} (similarity={similarity:.3f})",
                subject="VoiceprintVerifier",
                importance=9,
                source="security",
                tags=["security", "voiceprint", "alert"],
            )
        except Exception:
            pass


# Singleton
voiceprint_verifier = VoiceprintVerifier()
