# McLean Reference Provenance

## Files

| File | Role | Status |
|---|---|---|
| `mclean_drapery_set_generator.py` | P1-T port source AND P1-T·f acceptance fixture | **tracked in repo** (commit `948a1fc`) |
| `McLean_Whittington_Drapery_Elevations_RevA.pdf` | Reference artifact — 11-sheet founder-approved set | **parked at `/data/reference/mclean/`** (NOT in repo) |

## PDF md5

```
f882144aefc03745533fdaae95ea86b4  McLean_Whittington_Drapery_Elevations_RevA.pdf
```

## Why the PDF is not in the repo

14 MB of raster bloats history permanently for a file that is **provenance, not
source**. The `.py` is sufficient to regenerate the set. The PDF exists to
verify the regenerated output matches the founder-approved reference.

The PDF was downloaded once (founder action — byte-exact download, never paste)
and parked at `/data/reference/mclean/`. On a fresh clone, the file is NOT
present in the repo — a founder action is required to stage it for
byte-exact diff against the regenerated set.

## What lives in this repo

The `.py` file (`mclean_drapery_set_generator.py`) — this is the
authoritative reference implementation. P1-T·a will map its functions,
P1-T·b will port them into the new template layer, and P1-T·f will
regenerate the McLean set from the new engine for acceptance.

## Restoration instructions (post-fresh-clone)

If a future session needs the PDF for byte-exact comparison:

```
mkdir -p /data/reference/mclean
# Stage the PDF from external backup (per founder's download record)
# Verify:
md5sum /data/reference/mclean/McLean_Whittington_Drapery_Elevations_RevA.pdf
# Must print: f882144aefc03745533fdaae95ea86b4
```
