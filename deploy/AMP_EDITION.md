# AMP edition (Actitud Mental Positiva)

Same codebase as Empire Workroom. Separate process, separate data, separate assistant.

Juan Diego Giraldo (Cali) is the AMP coach. The assistant in this instance is **Max-e**, not Max. Max-e has his own name, persona, memory, conversation history, and settings under the AMP data root. He is the same family of code and tools, and he can run any extra company Juan creates. He is not the coach.

The product is [actitudmentalpositiva.com](https://actitudmentalpositiva.com), also called **El Portal de la Alegría**: structured multi-week courses with audio, plus themed guided meditations and a daily mood check-in.

## Run it on the Dell

Workroom stays on port 8000. Do not restart it and do not point AMP at its `.env` or its data directory.

```bash
mkdir -p /data/amp
cp deploy/empire-amp.env.example /home/rg/empire-amp.env
# Edit /home/rg/empire-amp.env on the server. Placeholders only are in git.

mkdir -p ~/.config/systemd/user
cp deploy/empire-amp.service ~/.config/systemd/user/empire-amp.service
systemctl --user daemon-reload
systemctl --user enable --now empire-amp.service
```

The process listens on **127.0.0.1:8011**. The Next.js frontend for this instance listens on **127.0.0.1:3011**.

Check:

```bash
curl -s http://127.0.0.1:8011/health
curl -s http://127.0.0.1:8011/api/v1/edition
```

`/api/v1/edition` is public so the UI can show the edition and the Spanish "sin acceso" state. Everything else requires the allowlist.

Frontend for this instance (separate from the Workroom command center process if you want a different name in the shell):

```bash
NEXT_PUBLIC_EMPIRE_EDITION=amp \
NEXT_PUBLIC_ASSISTANT_NAME=Max-e \
NEXT_PUBLIC_API_URL=http://127.0.0.1:8011/api/v1 \
EMPIRE_API_BASE=http://127.0.0.1:8011 \
npx next dev -p 3011
```

The language switcher still toggles English. With no saved choice, this edition starts in Spanish.

## Allowlist

Ships with only the owner/admin account (`AMP_OWNER_EMAIL` / `AMP_OWNER_USERNAME` in the env file). The file lives at `/data/amp/amp/allowlist.json`.

Add a person (email or username):

```bash
cd /home/rg/empire-repo/backend
EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \
  ./venv/bin/python scripts/amp_allowlist.py add --email person@example.com
```

List or remove:

```bash
EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \
  ./venv/bin/python scripts/amp_allowlist.py list

EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp \
  ./venv/bin/python scripts/amp_allowlist.py remove --email person@example.com
```

An admin who is already allowlisted can also `POST /api/v1/amp/allowlist` with `{"email":"..."}` or `{"username":"..."}`. Anyone else gets:

```json
{"detail": "Sin acceso. Esta edición solo está disponible para cuentas autorizadas.", "code": "sin_acceso"}
```

Identity is not a request header. `X-User-Email` and the other client identity headers are ignored. A caller is allowed only when:

- Cloudflare Access presents a valid `Cf-Access-Jwt-Assertion` (checked against `https://<team>.cloudflareaccess.com/cdn-cgi/access/certs` and `CF_ACCESS_AUD`), and that email is on the allowlist; or
- the browser holds the httpOnly `amp_session` cookie from the Spanish login at `/login` (one-time code, or the magic link).

When SMTP is not configured, generate the link on the server. It is printed, not emailed:

```bash
EMPIRE_EDITION=amp EMPIRE_DATA_DIR=/data/amp AMP_JWT_SECRET=... AMP_PUBLIC_BASE_URL=https://amp.empirebox.store \
  ./venv/bin/python scripts/amp_allowlist.py login-link --email person@example.com
```

## Nueva empresa

Inside this instance Juan can create more blank companies. Each one gets ` /data/amp/businesses/<slug>/ ` and only the shared modules: CRM, LeadForge, SocialForge, quotes/invoices, scheduling, finance. Workroom, WoodCraft, LuxeForge, and drawing tools stay off.

Optional templates (service categories and CRM fields only, no prices): Ciberseguridad, Consultoría de datos y BI, GIS y mapas, Redes y VoIP, Implementación ERP/CRM.

`POST /api/v1/businesses` with `{"name","industry","description","template"}`. The UI is `/amp/empresas`.

## Cloudflare tunnel

Do not edit the live tunnel from this repo. Add this ingress entry on the existing empire tunnel (dashboard or the local config you already operate), then reload cloudflared yourself:

```yaml
- hostname: amp.empirebox.store
  service: http://localhost:8011
```

Workroom hostnames stay on port 8000. This document does not change them.

## What stays put when the variables are unset

`EMPIRE_EDITION` unset means Workroom: assistant name Max, English default, every module visible, existing data paths, no allowlist, no Max-e files, SocialForge still uses `~/empire-repo/backend/data/socialforge`.
