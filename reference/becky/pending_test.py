"""Verify PENDING rendering works as specified.

Construct a tiny spec with one pending row. Render it. Confirm:
  - FIELD DATA shows value "PENDING"
  - FIELD CHECK contains a PENDING bullet for that label
"""
import importlib.util, sys, copy, subprocess
sys.path.insert(0, "/tmp/d42")
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_pending",
    "/home/rg/empire-repo-main/reference/mclean/mclean_drapery_set_generator.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["mclean_pending"] = m
spec.loader.exec_module(m)
patch_missing_italic(m)

# Tiny spec with one room, one panel, one PENDING row
test_spec = copy.deepcopy(m.SPEC_MCLEAN)
# Wipe the rooms and replace with a single test room
test_spec["rooms"] = [{
    "key": "T1",
    "name": "TEST ROOM",
    "sub": "Test",
    "panels": [{
        "label": "TEST PANEL",
        "w": 100.0,
        "h": 80.0,
        "items": [{"kind": "window", "w": 50.0, "v": None}],
        "dims_top": [(0.0, 50.0, "50\"")],
        "dim_h": "80\"",
    }],
    "data": [
        ("WINDOW WIDTH", "PENDING", {"pending": True}),
        ("FLOOR TO CEILING", "PENDING", {"pending": True}),
        ("MOUNT", "rod mount"),
    ],
    "math": "test math",
    "math_flag": False,
    "check": ["original hand-curated bullet"],
}]
test_spec["photos"] = {"T1": []}
test_spec["photo_dir"] = "/tmp/d42/audit/empty"
test_spec["job"]["status"] = "FOR DISCUSSION"

m.build("/tmp/d42/after/pending_test.pdf", spec=test_spec, audience="client")
subprocess.run(["pdftotext", "-layout", "/tmp/d42/after/pending_test.pdf", "/tmp/d42/after/pending_text.txt"], check=True)
with open("/tmp/d42/after/pending_text.txt") as f:
    text = f.read()

# Assertions
expected = [
    "WINDOW WIDTH",
    "PENDING",
    "WINDOW WIDTH: PENDING - confirm on site",
    "FLOOR TO CEILING: PENDING - confirm on site",
    "MOUNT",
    "rod mount",
    "original hand-curated bullet",
    "FOR DISCUSSION",
]
failures = []
for e in expected:
    if e not in text:
        failures.append(e)

if failures:
    print("FAIL: missing expected strings in pending render:")
    for f in failures:
        print(f"  - {f!r}")
    sys.exit(1)

print("PENDING render verified. Expected strings all present.")
print()
print("--- TEXT LAYER ---")
print(text)
