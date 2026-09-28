# Empire Workroom — style previews

Local comparison only. These pages are not the live site and are marked `noindex`.

## Open the three styles

From this folder:

```bash
cd landing-wr-wc-preview
python3 -m http.server 4173
```

Then:

| Direction | URL |
|---|---|
| Compare door | http://127.0.0.1:4173/ |
| A — Editorial atelier | http://127.0.0.1:4173/a/ |
| B — Quiet luxury showroom | http://127.0.0.1:4173/b/ |
| C — Soft modern craft | http://127.0.0.1:4173/c/ |

Each page has a black bar that jumps between A, B, and C. The bar is preview chrome, not the brand.

Or open the HTML files directly. Image paths are relative (`../assets/portfolio/…` from A/B/C), so a static server is more reliable than `file://` in some browsers.

## Photographs

Copy the 19 consent-yes hero JPEGs into `assets/portfolio/` using the filenames in `assets/portfolio/README.md`. They already live beside the cream preview on the shop machine. This repo copy does not contain the binaries.

If a frame is empty, the page is telling the truth: that file is not next to the HTML yet.

## What is real vs mock

- Real: the Workroom sentences from the current landing, the hero filenames from the creative pack, and `mailto:workroom@empirebox.store`.
- Mock: everything else. No LeadForge form, no inbox check, no Instagram URL, no production deploy.

The short recommendation is `STYLE_REPORT.md`.
