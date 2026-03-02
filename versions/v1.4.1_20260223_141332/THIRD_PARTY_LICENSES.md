# Third-Party Licenses

Copyright © 2026 EmpireBox. All rights reserved.

This document lists the third-party open source software components used by EmpireBox, along with their respective licenses. All listed packages use permissive licenses (MIT, BSD, Apache-2.0) that are compatible with proprietary use.

**Last Reviewed:** February 18, 2026
**Review Cycle:** Quarterly

---

## Backend (Python)

| Package | License | URL |
|---------|---------|-----|
| FastAPI | MIT | https://github.com/tiangolo/fastapi |
| SQLAlchemy | MIT | https://github.com/sqlalchemy/sqlalchemy |
| Pydantic | MIT | https://github.com/pydantic/pydantic |
| Uvicorn | BSD-3-Clause | https://github.com/encode/uvicorn |
| Starlette | BSD-3-Clause | https://github.com/encode/starlette |
| Alembic | MIT | https://github.com/sqlalchemy/alembic |
| stripe (Python SDK) | MIT | https://github.com/stripe/stripe-python |
| easypost (Python SDK) | MIT | https://github.com/EasyPost/easypost-python |
| boto3 (AWS SDK) | Apache-2.0 | https://github.com/boto/boto3 |
| httpx | BSD-3-Clause | https://github.com/encode/httpx |
| python-jose | MIT | https://github.com/mpdavis/python-jose |
| passlib | BSD | https://github.com/glic3rern/passlib |
| python-multipart | Apache-2.0 | https://github.com/andrew-d/python-multipart |
| python-dotenv | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| Jinja2 | BSD-3-Clause | https://github.com/pallets/jinja |
| aiofiles | Apache-2.0 | https://github.com/Tinche/aiofiles |

## Frontend (Next.js / React)

| Package | License | URL |
|---------|---------|-----|
| Next.js | MIT | https://github.com/vercel/next.js |
| React | MIT | https://github.com/facebook/react |
| React DOM | MIT | https://github.com/facebook/react |
| TypeScript | Apache-2.0 | https://github.com/microsoft/TypeScript |
| Tailwind CSS | MIT | https://github.com/tailwindlabs/tailwindcss |
| PostCSS | MIT | https://github.com/postcss/postcss |
| Autoprefixer | MIT | https://github.com/postcss/autoprefixer |
| Framer Motion | MIT | https://github.com/framer/motion |
| Axios | MIT | https://github.com/axios/axios |
| ESLint | MIT | https://github.com/eslint/eslint |

## Mobile App (Flutter / Dart)

| Package | License | URL |
|---------|---------|-----|
| Flutter SDK | BSD-3-Clause | https://github.com/flutter/flutter |
| Dart SDK | BSD-3-Clause | https://github.com/dart-lang/sdk |
| provider | MIT | https://pub.dev/packages/provider |
| http | BSD-3-Clause | https://pub.dev/packages/http |
| camera | BSD-3-Clause | https://pub.dev/packages/camera |
| image_picker | Apache-2.0 | https://pub.dev/packages/image_picker |
| qr_flutter | BSD-3-Clause | https://pub.dev/packages/qr_flutter |
| printing | Apache-2.0 | https://pub.dev/packages/printing |
| shared_preferences | BSD-3-Clause | https://pub.dev/packages/shared_preferences |
| url_launcher | BSD-3-Clause | https://pub.dev/packages/url_launcher |

---

## License Compliance Notes

- **No copyleft (GPL/AGPL) dependencies detected.** All dependencies use permissive licenses compatible with proprietary use.
- **Apache-2.0 packages** require preservation of copyright notices and a copy of the license in distributed software. The NOTICE obligations are satisfied by this document.
- **MIT and BSD packages** require preservation of copyright and license notices, which are included in each package's distribution.

## How to Verify

To verify dependency licenses in each component:

```bash
# Backend (Python)
cd backend
pip install pip-licenses
pip-licenses --format=markdown

# Frontend (Next.js)
cd website/nextjs
npx license-checker --summary

# Mobile (Flutter)
cd market_forge_app
flutter pub deps
```

---

*This document is part of EmpireBox's Software Bill of Materials (SBOM) and should be reviewed quarterly.*
