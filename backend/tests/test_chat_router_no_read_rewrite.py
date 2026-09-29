"""
Tests for the chat router's auto-reroute-to-CodeForge decision.

H52 Phase 2 follow-up — fifth interception layer. Before the fix, the
chat router silently rewrote file_read, file_write, file_edit,
file_append, and git_ops to run_desk_task (CodeForge desk). For reads,
this meant: model emits file_read → router rewrites → run_desk_task
fails → model falls back to web_search → user gets Maryland MVA pages.

The fix scopes the rewrite to writes only (file_write, file_edit,
file_append). Reads reach the model directly. Doctrine: a router must
never silently rewrite a tool call the model made.

These tests assert the routing decision in isolation. They do NOT
exercise the chat handler end-to-end (that requires mocking the entire
ai_router + desk + tool pipeline). The decision function is the gate;
if the gate is correct, the chat handler is correct by construction.

The negative fixtures are the cases the pre-fix code failed on:
pre-fix _should_reroute_to_codeforge("file_read", False) returned True
(file_read was in the rewrite set). Post-fix it must return False.
"""
import pytest

from app.routers.max.router import _should_reroute_to_codeforge, _CODEFORGE_WRITE_TOOLS


def test_helper_set_is_writes_only():
    """The rewrite set must contain only write tools. file_read and
    git_ops must not be in it.

    Negative fixture: pre-fix the set was
    {"file_read", "file_write", "file_edit", "file_append", "git_ops"}.
    Post-fix it must be writes-only. If file_read or git_ops ever reappear,
    the silent-rewrite bug has come back.
    """
    assert "file_read" not in _CODEFORGE_WRITE_TOOLS, (
        "file_read must never be in the rewrite set — reads reach the model directly"
    )
    assert "git_ops" not in _CODEFORGE_WRITE_TOOLS, (
        "git_ops must never be in the rewrite set — reads reach the model directly"
    )
    # Writes are still routed (genuine reason: Atlas path expansion / truncation)
    assert "file_write" in _CODEFORGE_WRITE_TOOLS
    assert "file_edit" in _CODEFORGE_WRITE_TOOLS
    assert "file_append" in _CODEFORGE_WRITE_TOOLS


def test_file_read_never_rerouted_on_chat_lane():
    """file_read with no explicit desk must return False.

    Negative fixture: pre-fix this returned True and the router
    silently rewrote file_read to run_desk_task.
    """
    assert _should_reroute_to_codeforge("file_read", False) is False


def test_git_ops_never_rerouted_on_chat_lane():
    """git_ops with no explicit desk must return False.

    Negative fixture: pre-fix this returned True and the router
    silently rewrote git_ops to run_desk_task.
    """
    assert _should_reroute_to_codeforge("git_ops", False) is False


def test_file_write_rerouted_on_chat_lane():
    """file_write (genuine write case) is still routed when no explicit
    desk is set. Atlas handles path expansion / truncation for code
    edits. The dispatch kept this rewrite because there is a genuine
    reason for it; only reads were scoped out.
    """
    assert _should_reroute_to_codeforge("file_write", False) is True


def test_file_edit_rerouted_on_chat_lane():
    assert _should_reroute_to_codeforge("file_edit", False) is True


def test_file_append_rerouted_on_chat_lane():
    assert _should_reroute_to_codeforge("file_append", False) is True


def test_explicit_desk_overrides_rewrite_for_writes():
    """If the caller already specified a desk, do not rewrite. The user
    asked for a desk; do not second-guess.
    """
    assert _should_reroute_to_codeforge("file_write", True) is False
    assert _should_reroute_to_codeforge("file_edit", True) is False
    assert _should_reroute_to_codeforge("file_append", True) is False


def test_unknown_tool_never_rerouted():
    """A tool the model emitted that is not in the rewrite set must not be
    rewritten. The default must be "execute as-is."
    """
    assert _should_reroute_to_codeforge("send_email", False) is False
    assert _should_reroute_to_codeforge("search_quotes", False) is False
    assert _should_reroute_to_codeforge("", False) is False


@pytest.mark.parametrize("tool_name", ["file_read", "git_ops"])
def test_doctrine_reads_never_rewritten(tool_name):
    """Doctrine parameterized check — every read tool returns False under
    any desk setting.
    """
    assert _should_reroute_to_codeforge(tool_name, False) is False
    assert _should_reroute_to_codeforge(tool_name, True) is False