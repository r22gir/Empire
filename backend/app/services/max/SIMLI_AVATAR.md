# Simli face (photoreal) next to TalkingHead

Simli (simli.com) renders only the face. Max's brain does not move. TTS audio and the xAI live-voice PCM feed the Simli session. TalkingHead stays available.

## Env

| Variable | Role |
| --- | --- |
| `SIMLI_API_KEY` | Server only. Used to mint a session token. Never sent to the browser. |
| `SIMLI_FACE_ID` | Workroom Max face. |
| `SIMLI_FACE_ID_MAX_E` | Max-e face. |
| `SIMLI_FACE_ID_MAXINE` | Maxine face. |

`SIMLI_FACE_ID_WORKROOM` is accepted as an alias for the workroom face. If the key or that edition's face id is unset, status is `disabled`, the renderer is `talkinghead`, and `missing` lists the names. Values are not included.

Session limits are fixed in the module: `maxSessionLength` 600 seconds, `maxIdleTime` 60 seconds.

## HTTP

- `GET /api/v1/avatar/simli/status?edition=workroom`
- `POST /api/v1/avatar/simli/session` `{ "edition": "workroom" }` returns `session_token`, `webrtc_url`, and `ice_servers`
- `GET /api/v1/avatar/simli/usage?edition=workroom` is the usage card (minutes)
- `POST /api/v1/avatar/simli/usage` `{ "edition", "seconds", "source" }` logs a capped session

The browser opens `wss://api.simli.ai/compose/webrtc/p2p?session_token=...` and sends PCM16 at 16 kHz. It does not call Simli with the API key.

## TalkingHead placeholder

`public/max-avatar.glb` is TalkingHead's female brunette sample, CC BY-NC 4.0, non-commercial, loaded with body `M`. The UI says so.

`avatar.html?edition=workroom|max_e|maxine` selects `/avatars/workroom.glb` (body M), `/avatars/max-e.glb` (body M), or `/avatars/maxine.glb` (body F). Those files are not in the repo yet. Until one is installed, the page uses the brunette placeholder.

## Files that port together

- `backend/app/services/max/simli_avatar.py`
- `backend/app/routers/simli_avatar.py`
- `empire-command-center/public/simli-face.js`
- `empire-command-center/public/avatar.html` (`?edition=` picks the GLB and body; Simli or TalkingHead)
- this file
