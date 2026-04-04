# MAX Web Chat UX Regression Table
## From 37 Real Exchanges — April 3, 2026

| Issue | Expected | Old Behavior | Files Fixed | Status |
|-------|----------|-------------|-------------|--------|
| Premature quoting | Stay in design mode | Auto-quoted after draw request | conversation_mode.py, system_prompt.py | FIXED |
| PIN on web_cc | No PIN on Command Center | Asked for 7777 on code requests | founder_auth.py (centralized) | FIXED |
| False attachment claims | Only claim if proof | "I sent the PDF" with nothing | transport_matrix.py, system_prompt.py | FIXED |
| Non-inline drawings | SVG in chat on web | Emailed/Telegrammed instead | system_prompt.py (inline default rule) | FIXED |
| Capability amnesia | Know own capabilities | Argued can't show drawings | capability_registry.json, capability_loader.py | FIXED |
