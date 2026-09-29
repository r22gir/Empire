# Empire Workroom — house document format

Landscape sheets and portrait invoices/estimates in the Empire / Nelma's Workroom
house style: cream page, ink header and footer bands, gold rules and accents,
DejaVu Serif for titles, DejaVu Sans Condensed for labels, DejaVu Sans Mono for
figures.

## generators/
- `base.py`        shared portrait builder: `build(path, kind, title, sub, rows, terms, ...)`
                   supports section rows, subtotals, a Stripe pay button + QR, brand overrides.
- `build.py`       Willard payment status sheet (landscape, statement of account).
- `inv.py`         Willard invoice 909 and lobby estimate 838 (portrait, uses base.py).
- `apex.py`        Marley's estimate EST-2026-272 (portrait, uses base.py).
- `client.py`      Marley's 3-sheet client presentation (landscape).
- `pres.py`        Marley's 4-sheet internal presentation (landscape).
- `diag.py`        Marley's field diagrams — internal, with notes and pricing.
- `diag_client.py` Marley's drawings — client version, drawings only.

## Running
    pip install reportlab qrcode --break-system-packages
    python3 apex.py        # writes into /mnt/user-data/outputs

Fonts come from /usr/share/fonts/truetype/dejavu/.

## Conventions
- Inches and fractions only; no feet.
- Dimensions sit outside the seating area, never across cushions.
- Client documents carry no markup register, no base rates, no vendor names.
- Internal sheets are stamped NOT FOR CONSTRUCTION - VERIFY ON SITE.
