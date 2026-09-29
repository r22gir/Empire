"""D42 1c gate demo.

Three runs, calling gate_emit_client_safe directly so the demo doesn't
depend on photo files on disk.

  1. CLEAN SPEC, audience='client' - gate must PASS (no exception).
  2. OFFENDING SPEC, audience='client' - gate must RAISE (ValueError).
  3. OFFENDING SPEC, audience='shop'   - gate must PASS (skipped).

Run 2 is the one that proves the gate. A green run proves nothing.
"""
import importlib.util, sys, copy
sys.path.insert(0, "/tmp/d42")
from _font_fallback import patch_missing_italic

spec = importlib.util.spec_from_file_location(
    "mclean_gate",
    "/home/rg/empire-repo-main/reference/mclean/mclean_drapery_set_generator.py",
)
m = importlib.util.module_from_spec(spec)
sys.modules["mclean_gate"] = m
spec.loader.exec_module(m)

patch_missing_italic(m)


def make_offending_spec():
    """Take the McLean spec, add a row to the FD room's data that carries
    the token MARKUP. The gate must raise on this."""
    s = copy.deepcopy(m.SPEC_MCLEAN)
    s["rooms"][0]["data"].append(
        ("INTERNAL MARKUP REGISTER", "MARKUP 50%  -  CONFIDENTIAL")
    )
    return s


print("=" * 70)
print("RUN 1: clean spec, audience=client  (gate should PASS)")
print("=" * 70)
try:
    m.gate_emit_client_safe(m.SPEC_MCLEAN, audience="client")
    print("GATE PASSED on clean spec - correct")
except Exception as e:
    print(f"UNEXPECTED RAISE on clean spec: {e!r}")
    sys.exit(1)

print()
print("=" * 70)
print("RUN 2: offending spec (MARKUP row), audience=client")
print("        (gate should RAISE - this is the H74-class check)")
print("=" * 70)
off = make_offending_spec()
try:
    m.gate_emit_client_safe(off, audience="client")
    print("GATE FAILED TO FIRE - this is the H74-class bug")
    sys.exit(1)
except ValueError as e:
    print(f"GATE FIRED with ValueError:")
    print(f"  {e}")
    print("CORRECT - gate refuses client-facing emit on token MARKUP")
except Exception as e:
    print(f"WRONG EXCEPTION TYPE: {type(e).__name__}: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("RUN 3: offending spec, audience=shop  (gate skipped by design)")
print("=" * 70)
try:
    m.gate_emit_client_safe(off, audience="shop")
    print("GATE SKIPPED on audience=shop - correct (shop docs may carry these tokens)")
except Exception as e:
    print(f"UNEXPECTED RAISE on shop audience: {e!r}")
    sys.exit(1)

print()
print("=" * 70)
print("ALL THREE RUNS COMPLETE")
print("=" * 70)
