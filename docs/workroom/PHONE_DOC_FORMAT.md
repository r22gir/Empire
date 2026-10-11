# Workroom phone-doc format (rule from Rafael, Oct 4, 2026)

Applies to every phone-view workroom document (field sheets, final lengths, install checks) Max or anyone builds.

1. **One section per screen.** Page size 390 × 844 pt, portrait. Never squeeze two sections on one screen.
2. **Room selector first.** Page 1 is a room selector that links to each window (tap a window → its page).
3. **Back to selector everywhere.** Every page has a "◂ Room selector" button.
4. **Nothing under 14 pt.** Body text 16-18 pt.
5. **Key numbers 36 pt or larger** (finished length, track width, cut length).
6. **High contrast.** Dark ink on light ground; no light-grey text.
7. **Big tap buttons.** Navigation targets at least 44 pt tall; Next / Back at the bottom.

Reference: *Becky Fieldstone BASIC-PHONE rev B* (5 pages: room selector, W1A, W1B, W2, field check).
On the Dell (kept out of git because it has client details):
`~/empire-data/docs-reference/workroom-phone-doc/Becky_Fieldstone_BASIC-PHONE_revB.pdf`,
builder script `build_becky_basic_phone_revB.py` (ReportLab; enforces `MINF = 14` with an assert) and its data
module `build_becky_workroom.py` in the same folder.
