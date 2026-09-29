"""D42 STEP 2 — build Becky's client pack from the McLean generator.

Quote: 739556e1 / EST-2026-262, subtotal $4,084.05, out-of-state, tax exempt.
Governed by issued invoice NELMA-814. Pleating $95/width (not the $110
catalog rate). All fabric COM. Bench construction rule carried on the
W1 check list per option 1 (no separate bench sheet) — drapery sheets
only: W1, W2, W3 + cover + schedule.

The spec carries job metadata from the stored row. No pricer call. No
fabrication. Per 2026-08-29 handoff §4: LENGTH=105", HEADING=pinch
pleat on ripplefold track (all rooms), OPENING WIDTH W1=6 widths and
W2=4 widths (settled). 7 dimension slots stay PENDING — DEDUCTION
and MOUNT on all three rooms, OPENING WIDTH on W3.

Cover OPEN ITEMS reads 8 (3/2/3 across W1/W2/W3): 7 are pending slots
and 1 is the bench block counted as an open item. The bench inflates
W1 because check is the sole multi-line field; tracked under D-COVER-2.
"""
import importlib.util, sys, subprocess

REPO = "/home/rg/empire-repo-main"
HERE = f"{REPO}/reference/becky"

sys.path.insert(0, HERE)
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_becky",
    f"{REPO}/reference/mclean/mclean_drapery_set_generator.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["mclean_becky"] = m
spec.loader.exec_module(m)
patch_missing_italic(m)

FABRIC_STRIP = (
    "COM — JAB CHIVASSO MY WAY CH2904/070, 122\" PLAIN"
    "  \u00b7  BATISTE 118\" LINING"
    "  \u00b7  PINCH PLEAT PENDANTS ON RIPPLEFOLD CARRIERS"
    "  \u00b7  TRACK + CARRIERS, 3 SETS"
    "  \u00b7  MOUNT TBC"
)

# Bench construction rule — option 1, no separate bench sheet. Carried
# on W1's check list as a single wrapped item. Verbatim from the
# 2026-08-29 handoff §6.
BENCH_BLOCK = (
    "BENCHES \u2014 2 EA, RYANN STYLE, 22 x 18 x 15\n"
    "Box joint frame. One continuous fabric wrap, no channels, no\n"
    "tufting, no caps. COM: Vervain PINDO 04, bolt 0086, 5.00 yd \u2014\n"
    "customer supplied, no fabric line."
)


def _drapery_room(key, name, sub, pleating_note, opening_width,
                  panel_w=80.0, panel_h=100.0):
    """opening_width is 'PENDING' or a concrete width (e.g. '6 widths').
    LENGTH (105") and HEADING (pinch pleat on ripplefold track) are
    settled globally per 2026-08-29 handoff §4. DEDUCTION and MOUNT
    stay PENDING across all rooms."""
    ow_row = (("OPENING WIDTH", "PENDING", {"pending": True})
              if opening_width == "PENDING"
              else ("OPENING WIDTH", opening_width))
    return {
        "key": key,
        "name": name,
        "sub": sub,
        "panels": [{
            "label": name,
            "w": panel_w,
            "h": panel_h,
            "items": [{"kind": "window", "w": 50.0, "x": 15.0, "v": None}],
            "dims_top": [(15.0, 65.0, "PENDING")],
            "dim_h": "PENDING",
        }],
        "data": [
            ow_row,
            ("LENGTH",    "105\""),
            ("DEDUCTION", "PENDING", {"pending": True}),
            ("MOUNT",     "PENDING", {"pending": True}),
            ("HEADING",   "pinch pleat on ripplefold track"),
        ],
        "math": pleating_note,
        "math_flag": False,
        "check": [],
        "fabric_strip": FABRIC_STRIP,
    }


becky_spec = {
    "job": {
        "project":    "BECKY — 4600 FIELDSTONE",
        "client":     "LAUREN BASSETT · LB DESIGN",
        "client_loc": "",  # street already in project; cleared to keep cover header inside page
        "scope":      "Window & Drapery Field Measurements",
        "letterhead": "NELMA'S WORKROOM",
        "poweredby":  "BY EMPIRE WORKROOM",
        "locale":     "HYATTSVILLE MD",
        "rev":        "A",
        "date":       "27 AUG 2026",
        "source":     "Quote 739556e1 (EST-2026-262) — issued NELMA-814",
        "status":     "FOR DISCUSSION",
        "pdf_title":     "Becky - Window & Drapery Field Measurements - 4600 Fieldstone",
        "pdf_author":    "Empire Workroom",
        "pdf_creator":   "Empire Workroom",
        "pdf_subject":   "Becky, 4600 Fieldstone - {rev} - {date} - {status}",
    },
    "rooms": [
        _drapery_room("W1", "W1 — LIVING ROOM",
                      "Pinch pleat pendants on ripplefold — 6 widths",
                      "PLEATING 6 WIDTHS \u00b7 NELMA-814 RATE $95 PER WIDTH",
                      "6 widths"),
        _drapery_room("W2", "W2 — DINING",
                      "Pinch pleat pendants on ripplefold — 4 widths",
                      "PLEATING 4 WIDTHS \u00b7 NELMA-814 RATE $95 PER WIDTH",
                      "4 widths"),
        _drapery_room("W3", "W3 — STUDY",
                      "Pinch pleat pendants on ripplefold — widths to confirm",
                      "PLEATING PENDING \u00b7 NELMA-814 RATE $95 PER WIDTH",
                      "PENDING"),
    ],
    "schedule": [
        ("LIVING ROOM", "W-1", 1, "6 widths", "105\"",
         "6 widths pin-pleated on ripplefold carriers"),
        ("DINING",      "W-2", 1, "4 widths", "105\"",
         "4 widths pin-pleated on ripplefold carriers"),
        ("STUDY",       "W-3", 1, "PENDING",  "105\"",
         "Widths PENDING - confirm on site"),
    ],
    "schedule_open_notes": [
        "7 of 15 dimension slots PENDING across W1, W2, W3; "
        "8 settled per 2026-08-29 handoff §4 "
        "(LENGTH 105\", HEADING pinch pleat on ripplefold track, "
        "OPENING WIDTH W1=6 widths, W2=4 widths).",
        "W3 widths PENDING - set 1 is 6 widths, set 2 is 4 widths.",
        "Mount condition not on field sheet - confirm before fabrication.",
        "All fabric on this job is COM. Customer supplies; no fabric line.",
        "Out-of-state, tax exempt. Rates governed by issued NELMA-814.",
        "Goods ordered against 98\" finished length; cutting at 105\". "
        "Railroaded 122\" face carries the drop, so yardage should not "
        "move — measure the bolt before cutting.",
    ],
    "schedule_subtitle": "All rooms - one line per opening type - per quote EST-2026-262, governed by issued NELMA-814",
    "photos": {},
    "photo_dir": f"{HERE}/audit/empty",
    "cover": {
        "open_at_glance": [
            "7 of 15 dimension slots PENDING. Field tape required on the 7; "
            "8 settled per 2026-08-29 handoff §4.",
            "Pleating: 6 widths (set 1), 4 widths (set 2). Set 3 widths PENDING.",
            "All fabric on this job is COM. Customer supplies.",
            "Out-of-state, tax exempt. Rates governed by issued NELMA-814.",
            "Status: FOR DISCUSSION.",
        ],
    },
}

# Bench rule on W1 check list (option 1). Other rooms keep the empty
# default — only W1 hosts the bench construction rule.
becky_spec["rooms"][0]["check"] = [BENCH_BLOCK]

OUT = f"{HERE}/Becky_client_pack.pdf"
m.build(OUT, spec=becky_spec, audience="client")

# Extract full text layer.
TXT = f"{HERE}/Becky_text.txt"
subprocess.run(["pdftotext", "-layout", OUT, TXT], check=True)

# Extract per-sheet text (5 sheets) for diff against reference/becky/becky/p1-p5.txt.
for n in range(1, 6):
    p = f"{HERE}/p{n}.txt"
    subprocess.run(
        ["pdftotext", "-layout", "-f", str(n), "-l", str(n), OUT, p],
        check=True,
    )

print("Becky pack written:", OUT)
print("Text layer:        ", TXT)
print("Per-sheet extracts:", f"{HERE}/p1-p5.txt")
