"""
H53 family regression guard.

The H53 family of bugs — appending `[SYSTEM: ...]` content to the user
channel as `AIMessage(role="user", ...)` — was a recurring pattern
across four sites in `backend/app/routers/max/router.py`:

  - H53 replay block           (fixed in 28dcb42)
  - H64 pre-search guard       (fixed in e9c18cc)
  - H65 inter-round follow-up  (fixed in c67dce0)
  - H66 factual_guard          (fixed in this commit)

Each was a separate fix and each was a separate diagnostic round. The
last fix closed the fourth; this test makes sure the fifth cannot come
back silently. It is worth more than the four fixes combined: it
turns a pattern nobody was looking for into one that fails CI.

The check walks the AST of every `.py` file under `backend/app/` and
finds every `AIMessage(role="user", ...)` call whose `content`
expression contains the literal substring `[SYSTEM:`. Comments and
docstrings are excluded by the AST walk — Python's `ast` module does
not include comments, and docstrings appear as `Expr(value=Constant(...))`
at the start of a module/class/function body, never as a keyword
argument to a function call.

If this test fails, a `[SYSTEM:]` injection on the user channel has
returned. The fix is the same shape every time: `role="user"` →
`role="system"`, drop the `[SYSTEM:]` prefix, suppress the empty
branch. See the H64/H65/H66 commits for the canonical application.
"""

import ast
import pathlib


_BACKEND_APP_ROOT = (
    pathlib.Path(__file__).resolve().parent.parent / "app"
)


def _content_has_system_prefix(node: ast.AST) -> bool:
    """Static-check whether an AST expression contains the literal
    substring `[SYSTEM:`. Handles string constants, f-strings (joined
    string with literal parts), and string concatenation.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return "[SYSTEM:" in node.value
    if isinstance(node, ast.JoinedStr):  # f-string
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                if "[SYSTEM:" in v.value:
                    return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return (
            _content_has_system_prefix(node.left)
            or _content_has_system_prefix(node.right)
        )
    return False


def _find_suspicious_user_role_system_injections():
    """Yield (relpath, lineno) for every AIMessage(role='user', ...) call
    whose content expression has a [SYSTEM:] literal.
    """
    findings = []
    for path in sorted(_BACKEND_APP_ROOT.rglob("*.py")):
        if "__pycache__" in str(path):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # Files that fail to parse are caught by other tests; we don't
            # fail here because that would mask the real assertion.
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not (
                isinstance(node.func, ast.Name)
                and node.func.id == "AIMessage"
            ):
                continue
            role = None
            content = None
            for kw in node.keywords:
                if kw.arg == "role" and isinstance(kw.value, ast.Constant):
                    role = kw.value.value
                elif kw.arg == "content":
                    content = kw.value
            if role != "user":
                continue
            if _content_has_system_prefix(content):
                findings.append(
                    (str(path.relative_to(path.parents[2])), node.lineno)
                )
    return findings


def test_no_system_injection_on_user_role():
    """No AIMessage(role='user', ...) call in backend/app/ may carry
    `[SYSTEM:` in its content expression. Comments and docstrings are
    excluded by the AST walk.
    """
    findings = _find_suspicious_user_role_system_injections()
    assert findings == [], (
        f"Found {len(findings)} AIMessage(role='user', ...) call(s) "
        f"carrying [SYSTEM:] content. This is the H53 family of bugs — "
        f"silent prompt-injection shape on the user channel. Fix: "
        f"role='user' -> role='system', drop the [SYSTEM:] prefix, "
        f"suppress the empty branch. Sites:\n  "
        + "\n  ".join(f"{p}:{ln}" for p, ln in findings)
    )