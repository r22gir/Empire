"""
H67 regression guard.

The bug (introduced 2026-07-16 in f97d808, latent 39 days): inside the
multi-round tool loop in router.py, `round_results = error_entries +
round_results` runs INSIDE the `if tool_block_errors:` branch — but
`round_results = []` is initialised 17 lines LATER, outside the branch.
On the first iteration of the loop, with malformed tool blocks, the
read raised UnboundLocalError("cannot access local variable
'round_results' where it is not associated with a value").

Fired live at 2026-08-20 19:11 EDT — crashed the chat handler mid-turn.
The model had already emitted its (fabricated) response, so the user
saw partial output. No further tool results reached the model.

This test walks the AST of router.py and asserts: inside the for loop
that drives the tool rounds, `round_results` is initialised BEFORE
it is read. Concretely, the first statement of each loop body must
be `round_results = []` (or an equivalent init). If a future edit moves
the init back below the read, the test fails and the chat handler
cannot crash on the same path again.
"""

import ast
import pathlib


_ROUTER_PY = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "routers" / "max" / "router.py"
)


def _round_loop_bodies(tree: ast.Module) -> list[tuple[str, list[ast.stmt]]]:
    """Return (label, body) for every `for _tool_round in range(3):` loop
    in router.py. There are two — the non-streaming /chat path and the
    /chat/stream path. Both must initialise round_results at the top.
    """
    bodies = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        # Match the tool-round loop by its iterable.
        is_round_loop = (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and len(node.iter.args) == 1
            and isinstance(node.iter.args[0], ast.Constant)
            and node.iter.args[0].value == 3
        )
        if not is_round_loop:
            continue
        # Match by the loop variable name.
        target = node.target
        if isinstance(target, ast.Name) and target.id == "_tool_round":
            bodies.append((f"line {node.lineno}", node.body))
    return bodies


def _first_write_to(name: str, body: list[ast.stmt]) -> int | None:
    """Return the line of the first assignment to `name` in the loop body,
    or None if there is no such assignment."""
    for stmt in body:
        for sub in ast.walk(stmt):
            if (
                isinstance(sub, ast.Assign)
                and len(sub.targets) == 1
                and isinstance(sub.targets[0], ast.Name)
                and sub.targets[0].id == name
            ):
                return sub.lineno
    return None


def _first_read_of(name: str, body: list[ast.stmt]) -> int | None:
    """Return the line of the first Name-load of `name` in the loop body,
    or None if `name` is never read."""
    for stmt in body:
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Name) and sub.id == name and isinstance(sub.ctx, ast.Load):
                return sub.lineno
    return None


def test_round_results_initialized_before_read_in_tool_loop():
    """Every tool-round loop in router.py must initialise `round_results`
    BEFORE it is read. The H67 bug was an UnboundLocalError because the
    init was 17 lines below the read inside the same loop body.
    """
    source = _ROUTER_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)

    bodies = _round_loop_bodies(tree)
    assert len(bodies) == 2, (
        f"Expected exactly 2 tool-round loops (non-streaming /chat + "
        f"/chat/stream). Found {len(bodies)}. If router.py was "
        f"refactored, update this test to match — but the invariant "
        f"below still applies to every loop that drives tool rounds."
    )

    for label, body in bodies:
        first_write = _first_write_to("round_results", body)
        first_read = _first_read_of("round_results", body)
        assert first_write is not None, (
            f"Tool-round loop at {label}: `round_results` is never "
            f"assigned. The H67 fix removed the only init — has it been "
            f"deleted?"
        )
        assert first_read is not None, (
            f"Tool-round loop at {label}: `round_results` is never read. "
            f"If the loop no longer needs it, the variable can be "
            f"removed entirely."
        )
        assert first_write < first_read, (
            f"Tool-round loop at {label}: `round_results` is read at "
            f"line {first_read} but first written at line {first_write}. "
            f"On the first iteration this raises UnboundLocalError. "
            f"The H67 fix moved the init to the top of the loop body; "
            f"this test fires if a future edit moves it back below any "
            f"read."
        )


def test_round_results_first_statement_is_empty_init():
    """Stronger form of the regression guard: assert that the FIRST
    STATEMENT in each tool-round loop body is `round_results = []`.
    A future edit that moves the init to the second statement (still
    before any read) would pass the weaker test above but could still
    introduce a regression if the parse step immediately before it ever
    raises — keep the init as the very first thing the loop does.
    """
    source = _ROUTER_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    bodies = _round_loop_bodies(tree)

    for label, body in bodies:
        first_stmt = body[0]
        # Must be `round_results = []` (an Assign with a single Name target
        # and a List constant of zero elements).
        assert isinstance(first_stmt, ast.Assign), (
            f"Tool-round loop at {label}: first statement is "
            f"{type(first_stmt).__name__}, not Assign. The H67 fix made "
            f"`round_results = []` the very first thing the loop does."
        )
        assert len(first_stmt.targets) == 1
        assert isinstance(first_stmt.targets[0], ast.Name)
        assert first_stmt.targets[0].id == "round_results", (
            f"Tool-round loop at {label}: first statement assigns to "
            f"`{first_stmt.targets[0].id}`, not `round_results`."
        )
        assert isinstance(first_stmt.value, ast.List)
        assert len(first_stmt.value.elts) == 0, (
            f"Tool-round loop at {label}: first statement assigns a "
            f"non-empty list, not `[]`."
        )