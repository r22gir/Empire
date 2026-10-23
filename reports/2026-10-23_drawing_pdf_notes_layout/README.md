# Drawing PDF notes / caption layout (Night Lab yellow)

**Found:** On Max job-set PDFs (U+L banquettes), page 2 notes sat in a
fixed box that dropped overflow, and page 3 elevation captions wrapped
through mixed-number inches (`7` / `3/4"`) and sat on the next title.

**Changed:** `banquette_standard.py` now wraps inside frames, keeps
`7 3/4"` intact, shrinks type if needed, and flows leftover notes to
the next block. Elevation runs reserve caption height so the next
bench cannot collide. `text_layout.audit_drawing_layout` measures
word bboxes vs the page and neighboring words.

**Tests:** `python3 -m pytest backend/tests/test_drawing_pdf_layout_check.py
backend/tests/test_drawing_revision_nightlab.py` — all passed.

**Proof:** `before_page{2,3}.png` and `after_page{2,3}.png` from
`generate_job_drawing` with the Marley's mock quote. Long-note pages
are `after_longnotes_page{2,3}.png`.
