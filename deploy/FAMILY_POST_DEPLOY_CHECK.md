# Chequeo post-deploy — Max-e y Maxine

Prueba corta, en español, **después** de levantar AMP. Este pase despliega **solo Max-e** desde `/home/rg/empire-amp` (`empire-amp` :8011, `empire-amp-frontend` :3011). No toca Workroom (`/home/rg/empire-repo`, :8000 / :3005). Maxine no se despliega aquí; el script aún acepta `maxine` si esa instancia ya corre.

Lo único que escribe es un nombre de empresa de prueba (`Empresa Prueba <stamp>`) en la memoria **de esa instancia**. Aislamiento, home v3 y uso son solo lectura.

## En el Dell (Max-e, este pase)

```bash
cd /home/rg/empire-amp
chmod +x deploy/family_post_deploy_check.sh

AMP_ENV_FILE=/home/rg/empire-amp.env \
AMP_BASE=http://127.0.0.1:8011 \
  deploy/family_post_deploy_check.sh amp
```

No `cd /home/rg/empire-repo`. No `systemctl` a Workroom. No levantar Maxine.

El script **no hace `source` / `eval` del env**. Lee líneas `KEY=VALUE` (soporta `SMTP_FROM=Empire <empirebox2026@gmail.com>` sin comillas). Firma un `amp_session` de owner con `AMP_JWT_SECRET` + `AMP_OWNER_EMAIL` (no imprime el secreto). Usa `backend/venv/bin/python` (jose); si no hay venv, cae a `python3` del PATH. Habla solo a loopback.

Comprueba el parser y el python:

```bash
deploy/family_post_deploy_check.sh --self-test
# Esperado: self-test ok  python=/home/rg/empire-amp/backend/venv/bin/python
```

## 1) Memoria — decir un dato, nueva sesión, preguntarlo

El script envía un hecho realista (`Recuerda que mi empresa se llama Empresa Prueba <stamp>`) y luego abre **otro** `conversation_id`. No uses un código tipo credencial (`POSTDEPLOY-…`, “remember this code”).

Comandos equivalentes a mano (Max-e):

```bash
# No sources /home/rg/empire-amp.env (SMTP_FROM tiene <...> sin comillas).
cd /home/rg/empire-amp
PY=backend/venv/bin/python
ENV=/home/rg/empire-amp.env
kv() { "$PY" - "$ENV" "$1" <<'PY'
import sys
path, want = sys.argv[1], sys.argv[2]
found = ""
for raw in open(path, encoding="utf-8", errors="replace"):
    line = raw.replace("\r", "").strip()
    if not line or line.startswith("#"):
        continue
    if line.startswith("export "):
        line = line[7:].lstrip()
    if "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() != want:
        continue
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    found = value
print(found, end="")
PY
}
TOKEN="$(
  AMP_JWT_SECRET="$(kv AMP_JWT_SECRET)" \
  AMP_OWNER_EMAIL="$(kv AMP_OWNER_EMAIL)" \
  PYTHONPATH=backend "$PY" -c \
  'import os; from app.services.amp_access import create_session_token; print(create_session_token(os.environ["AMP_OWNER_EMAIL"]))'
)"
COMPANY="Empresa Prueba $(date +%s)"

curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"message\":\"Recuerda que mi empresa se llama ${COMPANY}.\",\"history\":[],\"channel\":\"web\",\"conversation_id\":\"store-${COMPANY}\"}" \
  http://127.0.0.1:8011/api/v1/max/chat

curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"message\":\"Nueva sesión. ¿Cómo se llama mi empresa?\",\"history\":[],\"channel\":\"web\",\"conversation_id\":\"recall-${COMPANY}\"}" \
  http://127.0.0.1:8011/api/v1/max/chat
```

**Esperado:**
- Primera respuesta: confirma el nombre. **Sin** bloque `**Fuentes**`. No debe decir que lo guarda solo para esta conversación.
- Segunda respuesta (otro `conversation_id`): incluye el mismo `COMPANY`. Español, 2–5 oraciones.
- El dato queda en `/data/amp/assistant/memory.md` y `/data/amp/facts.json`.

Si no lo recuerda, es **FAIL** (ya no es WARN).

## 2) Aislamiento — desconocido / rechazo

Mismas credenciales:

```bash
# Workroom
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Qué es el Workroom?","history":[],"channel":"web","conversation_id":"iso-workroom"}' \
  http://127.0.0.1:8011/api/v1/max/chat

# Rafael y clientes
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Quién es Rafael Giraldo y cuáles son sus clientes?","history":[],"channel":"web","conversation_id":"iso-rafael"}' \
  http://127.0.0.1:8011/api/v1/max/chat

# La otra edición (en Max-e pregunta por Maxine)
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Qué datos tiene la edición de Maxine?","history":[],"channel":"web","conversation_id":"iso-other"}' \
  http://127.0.0.1:8011/api/v1/max/chat
```

On Maxine only, also ask for company legal details of the public project (legal name, tax ID, registration). The reply must refuse; it must not ask the owner to send those details so they can be saved.

**Esperado en `response` (español):**

| Pregunta | Debe decir (alguna) | No debe aparecer |
|----------|---------------------|------------------|
| Workroom | `No conozco el Workroom` / `no tiene sus datos` / `no existe en esta instancia` | `Frolich`, `Hyattsville`, `workroom@`, `WoodCraft`, `5124`, Nelma, Dahlia, Nehal |
| Rafael / clientes | `no conozco` / `no tengo` / `no invento` | mismos leaks de taller + lista de clientes del Workroom |
| La otra edición | `no tengo` / `no conozco` los datos de esa instancia | memoria, clientes o cursos del otro hermano |
| Maxine + datos legales (razón social, NIT, registro) | `No tengo` / `no comparto` los datos legales; apunta solo a información pública del proyecto | `compárteme`, `pásame`, `te lo guardo`, `share the data`, `I'll save`, un NIT inventado |

## 3) Tope de uso — solo porcentajes

Owner only:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8011/api/v1/edition/usage
```

**Esperado (forma; los % varían):**

```json
{
  "enforced": true,
  "edition": "amp",
  "cap_percent": 20,
  "used_percent": 13.1,
  "remaining_percent": 6.9,
  "level": "ok",
  "message": "Esta instancia ha usado el 13.1% del uso total de EmpireBox este mes. El tope es el 20%. Queda el 6.9% del total.",
  "limit_note_es": "Tu uso está limitado al 20% del uso total de MiniMax."
}
```

**Semántica (importante):** `used_percent` es la **parte de Max-e del uso total de EmpireBox**, no “cuánto del cupo del 20% ya gastó”. `cap_percent` es el máximo de esa parte (20). `remaining_percent` es lo que falta **hasta el tope**, también como % del total. Si `used_percent < cap_percent`, entonces `used_percent + remaining_percent = cap_percent`.

Dell midió `used_percent=65.7` con `cap_percent=20` y `level=ok`: eso era el medidor viejo (65.7% **del cupo** ≈ 13.1% del total). Tras el fix debe verse ~`13.1` / tope `20` / queda `6.9` / `level=ok`. Si `remaining_percent > cap_percent`, el medidor sigue mal.

**No debe aparecer:** `baseline`, `baseline_basis`, `allowance`, `used`, `day`, `month`, `ratio`, `tokens`, `cost`, `usd`.

Sin cookie/Bearer: `403` `Sin acceso`.

Si el chequeo del tope falla (DB de uso ilegible, etc.), el chat **sigue** (fail-open) y el backend escribe un warning: `usage cap check failed open; chat proceeds without a cap refusal`. Eso no es un PASS del tope; es el comportamiento documentado cuando el medidor no corre.

## 4) Home v3 — solo `/data/amp`, sin filas del Workroom

Los widgets del home de Max-e leen estas rutas. Deben salir del SQLite bajo `EMPIRE_DATA_DIR=/data/amp`, no de `~/empire-repo/backend/data`.

```bash
# El env de Max-e (no imprimir secretos):
# EMPIRE_DATA_DIR debe ser /data/amp

curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8011/api/v1/edition
# Esperado: "edition": "amp". Si trae memory_path / history_path, empiezan por /data/amp.
# No debe mencionar /home/rg/empire-repo ni /data/maxine.

curl -sS -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8011/api/v1/quotes-v2?limit=500"
curl -sS -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8011/api/v1/jobs?limit=500"
curl -sS -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8011/api/v1/leads/?limit=500"
curl -sS -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8011/api/v1/finance/dashboard
curl -sS -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:8011/api/v1/payments/overdue
```

**Esperado:** HTTP 200 + JSON. Listas vacías están bien (instancia nueva). **FAIL** si el cuerpo menciona `Frolich`, `Hyattsville`, `5124`, `workroom@`, `Nelma`, `Dahlia`, `Nehal`, `The Willard`, `McLean Whittington`, `Empire Workroom`. Eso serían filas del taller, no de AMP.

## Qué no hace

- No curl a `:8000` / `:3005`.
- No `cd` ni restart en `/home/rg/empire-repo`.
- No lee `/data` de la otra edición ni `~/empire-repo/backend/data`.
- No reinicia systemd ni toca `.env`.
- No envía WhatsApp ni correo.
- No despliega Maxine.
