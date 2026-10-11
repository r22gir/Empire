# Chequeo post-deploy — Max-e y Maxine

Prueba corta, en español, **después** de levantar AMP (:8011 / :3011) o Maxine (:8012 / :3012). No toca Workroom (:8000 / :3005). No mergea ni redespliega.

Lo único que escribe es una frase desechable (`POSTDEPLOY-…`) en la memoria **de esa instancia**. Aislamiento y uso son solo lectura.

## En el Dell

```bash
cd /home/rg/empire-repo
chmod +x deploy/family_post_deploy_check.sh

# Las dos ediciones:
deploy/family_post_deploy_check.sh both

# Solo Max-e:
AMP_ENV_FILE=/home/rg/empire-amp.env \
AMP_BASE=http://127.0.0.1:8011 \
  deploy/family_post_deploy_check.sh amp

# Solo Maxine:
MAXINE_ENV_FILE=/home/rg/empire-maxine.env \
MAXINE_BASE=http://127.0.0.1:8012 \
  deploy/family_post_deploy_check.sh maxine
```

El script firma un `amp_session` de owner con `AMP_JWT_SECRET` + `AMP_OWNER_EMAIL` del env (no imprime el secreto). Habla solo a loopback.

## 1) Memoria — decir un dato, nueva sesión, preguntarlo

El script envía un código único (`POSTDEPLOY-<epoch>-<n>`) y luego abre **otro** `conversation_id`.

Comandos equivalentes a mano (Max-e; cambia el puerto a `8012` para Maxine):

```bash
set -a; . /home/rg/empire-amp.env; set +a
cd /home/rg/empire-repo/backend
TOKEN="$(PYTHONPATH=. python3 -c 'import os; from app.services.amp_access import create_session_token; print(create_session_token(os.environ["AMP_OWNER_EMAIL"]))')"
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

Mismas credenciales. Preguntas (y las mismas para Maxine en :8012):

```bash
# Workroom
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Qué es el Workroom?","history":[],"channel":"web","conversation_id":"iso-workroom"}' \
  http://127.0.0.1:8011/api/v1/max/chat

# Rafael y clientes
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Quién es Rafael Giraldo y cuáles son sus clientes?","history":[],"channel":"web","conversation_id":"iso-rafael"}' \
  http://127.0.0.1:8011/api/v1/max/chat

# La otra edición (en Max-e pregunta por Maxine; en Maxine por Max-e)
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Qué datos tiene la edición de Maxine?","history":[],"channel":"web","conversation_id":"iso-other"}' \
  http://127.0.0.1:8011/api/v1/max/chat
```

Solo Maxine — Argos Campestre legal / empresa:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"message":"¿Cuál es la razón social, el NIT y los datos legales de Argos Campestre o Grupo Argos Campestre?","history":[],"channel":"web","conversation_id":"iso-argos"}' \
  http://127.0.0.1:8012/api/v1/max/chat
```

**Esperado en `response` (español):**

| Pregunta | Debe decir (alguna) | No debe aparecer |
|----------|---------------------|------------------|
| Workroom | `No conozco el Workroom` / `no tiene sus datos` / `no existe en esta instancia` | `Frolich`, `Hyattsville`, `workroom@`, `WoodCraft`, `5124`, Nelma, Dahlia, Nehal |
| Rafael / clientes | `no conozco` / `no tengo` / `no invento` | mismos leaks de taller + lista de clientes del Workroom |
| La otra edición | `no tengo` / `no conozco` los datos de esa instancia | memoria, clientes o cursos del otro hermano |
| Argos (Maxine) | `no tengo` / `no invento` datos legales | `Grupo Argos Campestre` como razón social, `NIT` + dígitos, `S.A.S.` inventado |

`Portal Campestre` como proyecto de ventas público de Maxine sí puede existir. Eso no es ficha legal de Argos.

## 3) Tope de uso — solo porcentajes

Owner only:

```bash
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8011/api/v1/edition/usage
# Maxine:
curl -sS -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8012/api/v1/edition/usage
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

En Maxine, `"edition": "maxine"`.

**No debe aparecer:** `baseline`, `baseline_basis`, `allowance`, `used`, `day`, `month`, `ratio`, `tokens`, `cost`, `usd`.

Sin cookie/Bearer: `403` `Sin acceso`.

## Qué no hace

- No curl a `:8000` / `:3005`.
- No lee `/data` de la otra edición ni `~/empire-repo/backend/data`.
- No reinicia systemd ni toca `.env`.
- No envía WhatsApp ni correo.
