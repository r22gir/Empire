# Simli face (photoreal) next to TalkingHead

Simli (simli.com) renders only the face. Max's brain does not move. TTS audio and the xAI live-voice PCM feed the Simli session. TalkingHead stays available.

## Env

| Variable | Role |
| --- | --- |
| `SIMLI_API_KEY` | Server only. Used to mint a session token. Never sent to the browser. |
| `SIMLI_FACE_ID` | Optional override for the workroom Max face. |
| `SIMLI_FACE_ID_MAX_E` | Optional override for the amp / Max-e face. |
| `SIMLI_FACE_ID_MAXINE` | Optional override for the Maxine face. |

Built-in face ids (not secrets; env wins when set):

| Edition | Face |
| --- | --- |
| workroom / Max | `7e74d6e7-d559-4394-bd56-4923a3ab75ad` |
| amp / Max-e (`max_e`) | `dd10cb5a-d31d-4f12-b69f-6db3383c006e` |
| maxine / Maxine | `cace3ef7-a4c4-425d-a8cf-a5358eb0c427` |

`SIMLI_FACE_ID_WORKROOM` is accepted as an alias for the workroom face. If the API key is unset, status is `disabled`, the renderer is `talkinghead`, and `missing` lists `SIMLI_API_KEY`. Face id values are not included in status.

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
