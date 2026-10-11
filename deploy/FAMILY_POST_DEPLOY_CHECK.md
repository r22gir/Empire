# Chequeo post-deploy — Max-e y Maxine

Prueba corta, en español, **después** de levantar AMP. Este pase despliega **solo Max-e** desde `/home/rg/empire-amp` (`empire-amp` :8011, `empire-amp-frontend` :3011). No toca Workroom (`/home/rg/empire-repo`, :8000 / :3005). Maxine no se despliega aquí; el script aún acepta `maxine` si esa instancia ya corre.

Lo único que escribe es una frase desechable (`POSTDEPLOY-…`) en la memoria **de esa instancia**. Aislamiento, home v3 y uso son solo lectura.

## En el Dell (Max-e, este pase)

```bash
cd /home/rg/empire-amp
chmod +x deploy/family_post_deploy_check.sh

AMP_ENV_FILE=/home/rg/empire-amp.env \
AMP_BASE=http://127.0.0.1:8011 \
  deploy/family_post_deploy_check.sh amp
```

No `cd /home/rg/empire-repo`. No `systemctl` a Workroom. No levantar Maxine.

El script firma un `amp_session` de owner con `AMP_JWT_SECRET` + `AMP_OWNER_EMAIL` del env (no imprime el secreto). Habla solo a loopback.

## 1) Memoria — decir un dato, nueva sesión, preguntarlo

El script envía un código único (`POSTDEPLOY-<epoch>-<n>`) y luego abre **otro** `conversation_id`.

Comandos equivalentes a mano (Max-e):

```bash
set -a; . /home/rg/empire-amp.env; set +a
cd /home/rg/empire-amp/backend
TOKEN="$(PYTHONPATH=. ./venv/bin/python3 -c 'import os; from app.services.amp_access import create_session_token; print(create_session_token(os.environ["AMP_OWNER_EMAIL"]))')"
PROBE="POSTDEPLOY-$(date +%s)"

curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"message\":\"Recuerda solo para esta prueba, no es un dato de negocio: el código POSTDEPLOY es ${PROBE}.\",\"history\":[],\"channel\":\"web\",\"conversation_id\":\"store-${PROBE}\"}" \
  http://127.0.0.1:8011/api/v1/max/chat

curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"message\":\"Nueva sesión. ¿Cuál es el código POSTDEPLOY de la prueba?\",\"history\":[],\"channel\":\"web\",\"conversation_id\":\"recall-${PROBE}\"}" \
  http://127.0.0.1:8011/api/v1/max/chat
```

**Esperado:** el segundo `response` incluye el mismo `PROBE`. Español, 2–5 oraciones. Si el modelo omite el código, el script marca `WARN` (reintenta); no es un fallo de aislamiento.

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

**Esperado en `response` (español):**

| Pregunta | Debe decir (alguna) | No debe aparecer |
|----------|---------------------|------------------|
| Workroom | `No conozco el Workroom` / `no tiene sus datos` / `no existe en esta instancia` | `Frolich`, `Hyattsville`, `workroom@`, `WoodCraft`, `5124`, Nelma, Dahlia, Nehal |
| Rafael / clientes | `no conozco` / `no tengo` / `no invento` | mismos leaks de taller + lista de clientes del Workroom |
| La otra edición | `no tengo` / `no conozco` los datos de esa instancia | memoria, clientes o cursos del otro hermano |

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
  "used_percent": 0.0,
  "remaining_percent": 100.0,
  "level": "ok",
  "message": "...",
  "limit_note_es": "Tu uso está limitado al 20% del uso total de MiniMax."
}
```

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
