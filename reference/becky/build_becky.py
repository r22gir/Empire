"""D42 STEP 2 — build Becky's client pack from the McLean generator.

Quote: 739556e1 / EST-2026-262, subtotal $4,084.05, out-of-state, tax exempt.
Governed by issued invoice NELMA-814. Pleating $95/width (not the $110
catalog rate). All fabric COM. Two benches deferred pending ruling —
drapery sheets only: W1, W2, W3 + cover + schedule.

The spec carries job metadata from the stored row. No pricer call. No
fabrication: the 15 dimension slots (3 openings x 5 dims) are all
PENDING. The pleating widths 6 and 4 are recorded on the schedule's
note column, not in the FIELD DATA width slot — those slots stay PENDING.
"""
import importlib.util, sys, copy, subprocess
sys.path.insert(0, "/tmp/d42")
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_becky",
    "/home/rg/empire-repo-main/reference/mclean/mclean_drapery_set_generator.py",
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

def _drapery_room(key, name, sub, pleating_note, panel_w=80.0, panel_h=100.0):
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
            "dim_h": "PENDING\"",
        }],
        "data": [
            ("OPENING WIDTH",       "PENDING", {"pending": True}),
            ("LENGTH",              "PENDING", {"pending": True}),
            ("DEDUCTION",           "PENDING", {"pending": True}),
            ("MOUNT",               "PENDING", {"pending": True}),
            ("HEADING",             "PENDING", {"pending": True}),
        ],
        "math": pleating_note,
        "math_flag": False,
        "check": [],
        "fabric_strip": FABRIC_STRIP,
    }


becky_spec = {
    "job": {
        "project":    "BECKY",
        "client":     "BECKY",
        "client_loc": "4600 FIELDSTONE",
        "scope":      "Window & Drapery Field Measurements",
        "letterhead": "EMPIRE WORKROOM",
        "poweredby":  "POWERED BY EMPIRE WORKROOM",
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
                      "PLEATING 6 WIDTHS \u00b7 NELMA-814 RATE $95 PER WIDTH"),
        _drapery_room("W2", "W2 — DINING",
                      "Pinch pleat pendants on ripplefold — 4 widths",
                      "PLEATING 4 WIDTHS \u00b7 NELMA-814 RATE $95 PER WIDTH"),
        _drapery_room("W3", "W3 — STUDY",
                      "Pinch pleat pendants on ripplefold — widths to confirm",
                      "PLEATING PENDING \u00b7 NELMA-814 RATE $95 PER WIDTH"),
    ],
    "schedule": [
        ("BECKY",  "W-1", 1, "PENDING", "PENDING",
         "6 widths pin-pleated on ripplefold carriers"),
        ("BECKY",  "W-2", 1, "PENDING", "PENDING",
         "4 widths pin-pleated on ripplefold carriers"),
        ("BECKY",  "W-3", 1, "PENDING", "PENDING",
         "Widths PENDING - confirm on site"),
    ],
    "schedule_open_notes": [
        "All 15 dimension slots PENDING across W1, W2, W3.",
        "W3 widths PENDING - set 1 is 6 widths, set 2 is 4 widths.",
        "Mount condition not on field sheet - confirm before fabrication.",
        "All fabric on this job is COM. Customer supplies; no fabric line.",
        "Out-of-state, tax exempt. Rates governed by issued NELMA-814.",
        "2 benches (Ryann-style, 22 x 18 x 15) deferred pending bench renderer ruling.",
    ],
    "schedule_subtitle": "All rooms - one line per opening type - per quote EST-2026-262, governed by issued NELMA-814",
    "photos": {},
    "photo_dir": "/tmp/d42/audit/empty",
    "cover": {
        "open_at_glance": [
            "All 15 dimension slots PENDING. Field tape required before fabrication.",
            "Pleating: 6 widths (set 1), 4 widths (set 2). Set 3 widths PENDING.",
            "All fabric on this job is COM. Customer supplies.",
            "Out-of-state, tax exempt. Rates governed by issued NELMA-814.",
            "2 benches (Ryann-style, 22 x 18 x 15) deferred pending bench renderer ruling.",
            "Status: FOR DISCUSSION.",
        ],
    },
}

OUT = "/tmp/d42/becky/Becky_client_pack.pdf"
m.build(OUT, spec=becky_spec, audience="client")

# Extract text layer.
subprocess.run(["pdftotext", "-layout", OUT, "/tmp/d42/becky/Becky_text.txt"], check=True)
print("Becky pack written:", OUT)
print("Text layer:        ", "/tmp/d42/becky/Becky_text.txt")
