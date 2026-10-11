# Maxine edition (ConstructionForge)

Same codebase as Workroom Max and Max-e. Separate process, separate data, separate assistant. Nothing here is deployed by this change.

Maxine is Camilo Giraldo's assistant. The app is **Maxine · Centro de mando**. Her edition is based on ConstructionForge: that is the home dashboard and the only record of projects, phases, lots, buyers, quotes, and payment plans (COP). CRM, leads, SocialForge, and chat read and write those same rows. They do not keep a second list.

Workroom Max stays on the owner's desk. Max-e stays on the AMP command center. Shared Empire modules stay available underneath.

## What the seed loads

`deploy/seeds/maxine-seed.md` is public sales copy plus a short list of questions for Camilo. The loader:

- Stores the sales lines as **public** facts and the day-one questions as **confidential**.
- Creates two ConstructionForge projects, a phase each, and lots. Brand field is GAC. There is no legal name, NIT, or company record for GAC.
- Portal Campestre 2: 27 lots with the status counts from the file (14 disponibles, 7 vendidos, 6 consultar). Per-lot area and price stay empty. The Tipo 1 launch price stays a public fact, not a price on every lot.
- Rincón de San Jerónimo: the four units, with the areas written in the file, status en ejecución, no prices. OCMA is a contractor name only.

Run the loader once the data dir exists (also runs on the first `/api/v1/edition` call if `seed_loaded.json` is absent):

```bash
cd backend
EMPIRE_EDITION=maxine EMPIRE_DATA_DIR=/data/maxine \
  python -c "from app.services.edition_seed import load_edition_seed; print(load_edition_seed())"
```

## Run it (do not start it from this repo change)

Suggested ports: backend **8012**, frontend **3012**. Host: `maxine.empirebox.store`. Data: `/data/maxine`. Do not point this process at `/data/amp` or the Workroom database, and do not restart those services.

```bash
mkdir -p /data/maxine
cp deploy/empire-maxine.env.example /home/rg/empire-maxine.env
# Edit /home/rg/empire-maxine.env on the server. Placeholders only are in git.

mkdir -p ~/.config/systemd/user
cp deploy/empire-maxine.service ~/.config/systemd/user/empire-maxine.service
systemctl --user daemon-reload
systemctl --user enable --now empire-maxine.service

# Frontend, its own process:
cd empire-command-center
NEXT_PUBLIC_EMPIRE_EDITION=maxine \
NEXT_PUBLIC_ASSISTANT_NAME=Maxine \
NEXT_PUBLIC_API_URL=http://127.0.0.1:8012/api/v1 \
EMPIRE_API_BASE=http://127.0.0.1:8012 \
npx next start -p 3012
```

Login is the same `/login` session as Max-e. The setup interview creates a ConstructionForge project, phase, and only the lots the owner typed, then asks Confirmar datos (Publicar / Confidencial, default Confidencial).

## WhatsApp (draft only, this instance)

Spanish guide on this site: `https://maxine.empirebox.store/amp/whatsapp` (also `/ayuda/whatsapp`). Read-only chats: `/amp/whatsapp/chats`.

Camilo creates **his own new** Meta / WhatsApp account and Meta test number — not Rafael’s, not the Workroom number, not Max-e’s. Webhook:

`https://maxine.empirebox.store/api/v1/whatsapp/webhook` → uvicorn on **8012**.

Secrets (`WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_OWNER_NUMBERS`) go only through the secure secret request into `/home/rg/empire-maxine.env`. Never type them in chat or on the page. Owner allowlist is Camilo’s number only. Draft-only; 20% usage cap; no client sends.

This checkout is `feature/amp-edition` with `EMPIRE_EDITION=maxine`. There is no separate Maxine edition git branch.
