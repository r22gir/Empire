# EmpireBox Voice Service

## Features

- **Speech-to-Text (STT)** – Transcribe voice messages using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Whisper `base` model by default)
- **Text-to-Speech (TTS)** – Generate natural-sounding speech using [Piper TTS](https://github.com/rhasspy/piper) (fully local, no API key needed)
- **Telegram voice messages** – Send a voice message to the bot; it transcribes it, asks OpenClaw, and can reply with voice
- **Product integration SDK** – Any EmpireBox product can add voice features in a few lines of code

## Architecture

```
┌─────────────────────────────────────────────────┐
│  VOICE SERVICE (Port 8200)                      │
├─────────────────────────────────────────────────┤
│  POST /stt     - Speech to Text (Whisper)       │
│  POST /tts     - Text to Speech (Piper)         │
│  GET  /voices  - List available voices          │
│  GET  /health  - Service health check           │
└─────────────────────────────────────────────────┘
          ↑               ↑              ↑
    Telegram Bot    Any Product    OpenClaw Skills
```

## Quick Start

The voice service starts automatically as part of the core EmpireBox stack:

```bash
# Start all core services (includes voice-service)
cd /opt/empirebox
docker compose up -d

# Or manage independently
ebox voice start
ebox voice stop
ebox voice logs
ebox voice status
```

## Telegram Voice Messages

Just send a voice message to your EmpireBox bot! The bot will:

1. Transcribe your message using Whisper STT
2. Show you the transcript (if `show_transcript: true`)
3. Send the transcript to OpenClaw AI
4. Reply with a voice message (if voice replies are enabled)

### Commands

```
/voice on   – Enable voice replies for your account
/voice off  – Disable voice replies (text replies only)
/voice      – Show current voice reply status
```

## Configuration

Edit `/opt/empirebox/voice/config.yaml`:

```yaml
voice:
  stt:
    model: "base"       # tiny, base, small, medium, large
    language: "auto"    # auto-detect or specific: en, es, fr, etc.
    device: "cpu"       # cpu or cuda

  tts:
    default_voice: "en_US-amy-medium"
    output_format: "mp3"
    speed: 1.0
    available_voices:
      - en_US-amy-medium
      - en_US-ryan-medium
      - en_GB-alan-medium
      - es_ES-mls-medium

  api:
    host: "0.0.0.0"
    port: 8200
    max_audio_size_mb: 25
    timeout_seconds: 60
```

Telegram bot voice options are in `/opt/empirebox/telegram/config.yaml`:

```yaml
voice:
  enabled: true
  service_url: "http://voice-service:8200"
  voice_replies: true
  always_voice_reply: false   # reply with voice only if user sent voice
  show_transcript: true        # show text transcript with voice reply
  reply_voice: "en_US-amy-medium"
```

## Voices Available

| Voice ID               | Description          |
|------------------------|----------------------|
| en_US-amy-medium       | Female, US English   |
| en_US-ryan-medium      | Male, US English     |
| en_GB-alan-medium      | Male, British English|
| es_ES-mls-medium       | Spanish              |

### Downloading Voices

Piper voice models are downloaded on demand. To pre-download them:

```bash
docker exec empirebox-voice python -m piper.download \
  --voice en_US-amy-medium \
  --output-dir /app/models/piper
```

## Product Integration SDK

Any EmpireBox product can use the Voice Client SDK:

```python
from empirebox_sdk import VoiceClient

voice = VoiceClient()  # defaults to http://voice-service:8200

# Text to Speech
audio_bytes = voice.speak("Your order has shipped!")
# Returns: bytes (mp3 audio)

# Speech to Text
result = voice.transcribe(audio_bytes, language="auto")
# Returns: {"text": "...", "language": "en", "confidence": 0.95}

# List available voices
voices = voice.list_voices()

# Health check
is_up = voice.health_check()
```

## API Reference

### POST /stt

Transcribe an uploaded audio file.

**Form fields:**
- `file` (required) – Audio file (`.ogg`, `.mp3`, `.wav`, `.m4a`)
- `language` (optional) – ISO language code or `"auto"` (default)

**Response:**
```json
{"text": "Hello world", "language": "en", "confidence": 0.98}
```

### POST /tts

Convert text to speech audio.

**Form fields:**
- `text` (required) – Text to synthesise
- `voice` (optional) – Voice ID (default: `en_US-amy-medium`)
- `speed` (optional) – Speed multiplier, e.g. `1.2` (default: `1.0`)

**Response:** Audio file bytes (`audio/mpeg` or `audio/ogg`)

### GET /voices

List available TTS voices.

**Response:**
```json
{"voices": ["en_US-amy-medium", "en_US-ryan-medium"], "default": "en_US-amy-medium"}
```

### GET /health

Service health check.

**Response:**
```json
{"status": "ok", "service": "voice"}
```

## Resource Requirements

| Component            | Storage  | RAM (active) |
|----------------------|----------|--------------|
| Whisper `base` model | ~1.5 GB  | ~1 GB        |
| Piper TTS voices     | ~100 MB  | ~200 MB      |
| **Total additional** | **~2 GB**| **~1.5 GB**  |

## Troubleshooting

**Voice service won't start:**
```bash
ebox voice logs
docker logs empirebox-voice
```

**Whisper model not found:** The model is downloaded automatically on first use. Ensure the container has internet access.

**Piper voice not found:** Download the voice model:
```bash
docker exec empirebox-voice python -m piper.download --voice en_US-amy-medium --output-dir /app/models/piper
```

**Telegram bot not transcribing:** Ensure `voice.enabled: true` in `/opt/empirebox/telegram/config.yaml` and the voice service is running (`ebox voice status`).
