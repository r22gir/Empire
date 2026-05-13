import re
"""MAX Execution Bridge — Converts approved proposals into real code.
Safety layer: validates paths, backs up files, logs all actions.
LLM-powered: generates actual source using MiniMax.
"""
import asyncio, json, re, shutil
from pathlib import Path
from typing import Optional

V10_ROOT = Path.home() / "empire-repo-v10"
PROPOSALS_DIR = V10_ROOT / "backend" / "data" / "max" / "proposals"
AUDIT_LOG = V10_ROOT / "backend" / "data" / "logs" / "execution_audit.jsonl"

# Language map for syntax validation
LANG_BRACES = {
    ".py": {"open": "(", "close": ")", "check": "python"},
    ".ts": {"open": "{", "close": "}", "check": "typescript"},
    ".tsx": {"open": "{", "close": "}", "check": "typescript"},
    ".js": {"open": "{", "close": "}", "check": "javascript"},
    ".jsx": {"open": "{", "close": "}", "check": "javascript"},
}


def load_proposal(pid: str) -> Optional[dict]:
    """Load proposal JSON by ID."""
    p = PROPOSALS_DIR / f"{pid}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def backup_file(path: Path) -> Path:
    """Create timestamped backup before writing."""
    bak = path.with_suffix(path.suffix + f".bak.{int(Path(__file__).stat().st_mtime)}")
    shutil.copy2(path, bak)
    return bak


def restore_backup(path: Path) -> bool:
    """Restore from most recent .bak file."""
    bak = path.with_suffix(path.suffix + f".bak.{int(Path(__file__).stat().st_mtime)}")
    if bak.exists():
        shutil.copy2(bak, path)
        bak.unlink()
        return True
    return False


def validate_proposal_paths(files: list) -> list:
    """Ensure all paths are within v10 sandbox. Returns list of (resolved_path, error)."""
    results = []
    for f in files:
        try:
            resolved = Path(f).expanduser().resolve()
            v10 = V10_ROOT.resolve()
            if not str(resolved).startswith(str(v10)):
                results.append((None, f"Path escapes v10 sandbox: {f}"))
            else:
                results.append((resolved, None))
        except Exception as e:
            results.append((None, str(e)))
    return results


def _generate_code_prompt(feature: str, file_path: str, ext: str) -> str:
    """Build targeted LLM prompt for file generation."""
    lang_map = {
        ".py": "Python 3 (FastAPI, asyncio)",
        ".ts": "TypeScript (Next.js 14, strict mode)",
        ".tsx": "TypeScript React (Next.js 14, Tailwind CSS)",
        ".js": "JavaScript (Next.js)",
        ".jsx": "JavaScript React (Next.js)",
        ".sh": "Bash shell script",
    }
    framework = lang_map.get(ext, "plain text")

    return f"""You are an expert EmpireBox coder. Write the complete, production-ready source file.

Filename: {Path(file_path).name}
Feature context: {feature}
Target framework: {framework}

Rules:
1. Output ONLY the raw source code — no markdown fences, no backticks, no explanations
2. The file must be syntactically correct and complete (not truncated)
3. If the file needs imports, include them
4. Follow EmpireBox conventions: v10 paths, TypeScript strict typing, Python type hints
5. Do NOT include any TODO comments or placeholder markers

Write the full file content now:"""


def _extract_code(text: str) -> str:
    """Strip markdown fences from LLM response and return clean code."""
    # Remove common markdown code block wrappers
    cleaned = re.sub(r"^```[\w]*\n?", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\n?```$", "", cleaned)
    # If still has unexpected wrapping, try direct extraction
    if cleaned.startswith("```") or cleaned.startswith("`"):
        cleaned = re.sub(r"^`+", "", cleaned)
        cleaned = re.sub(r"`+$", "", cleaned)
    return cleaned.strip()


def _syntax_check(content: str, file_path: str) -> bool:
    """Strong syntax check using ast.parse (Python) + XML/HTML rejection. Returns True if OK."""
    import ast
    import io

    ext = Path(file_path).suffix

    # Reject hallucinated XML/HTML content before any other checks
    if ext in (".py", ".ts", ".tsx", ".js", ".jsx", ".vue"):
        # Pattern: XML closing tags (hallucination artifacts like </project_name>)
        if re.search(r"</(?:project_name|component|div|span|p)[^>]*>", content, re.IGNORECASE):
            return False
        # Pattern: HTML-like tags at document start
        if re.search(r"^\s*<(?:!DOCTYPE|html|head|body|div|span|p|a|script|style)", content, re.IGNORECASE | re.MULTILINE):
            return False
        # Pattern: unescaped HTML in what should be code
        if re.search(r"^\s*</", content, re.MULTILINE) and content.count("\n") < 5:
            return False

    # For Python, use py_compile (ast.parse as fallback)
    if ext == ".py":
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            # Last resort: try py_compile via BytesIO (catches different error types)
            try:
                py_compile(source=content.encode(), doraise=True)
                return True
            except Exception:
                return False

    # For TypeScript/JSX, use brace counting as secondary check
    brace_config = LANG_BRACES.get(ext)
    if not brace_config:
        return True  # Unknown extension, skip

    open_char = brace_config["open"]
    close_char = brace_config["close"]
    depth = 0
    in_string = False
    prev_char = ""

    for char in content:
        if char in ('"', "'", '`') and prev_char != "\\":
            in_string = not in_string
        if not in_string:
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
        prev_char = char
        if depth < 0:
            return False

    return depth == 0


async def _generate_file_content(feature: str, file_path: str, ai_router) -> tuple[str, bool]:
    """Ask MiniMax to generate content for one file. Returns (content, success)."""
    ext = Path(file_path).suffix
    prompt = _generate_code_prompt(feature, file_path, ext)

    try:
        from app.services.max.ai_router import AIMessage

        resp = await ai_router._minimax_chat(
            messages=[
                AIMessage(role="system", content="You are EmpireBox's expert code generator. Output raw code only."),
                AIMessage(role="user", content=prompt),
            ],
            image_path=None,
            tools=None,
        )
        raw = resp.content if hasattr(resp, "content") else str(resp)
        code = _extract_code(raw)

        if not code or len(code) < 20:
            return "// MAX LLM failed: empty response", False

        return code, True

    except Exception as e:
        return f"// MAX LLM failed: {type(e).__name__}: {e}", False


async def execute_proposal(pid: str, dry_run: bool = True, ai_router=None) -> dict:
    """Execute an approved proposal by generating and writing real code.

    Args:
        pid: Proposal ID to execute
        dry_run: If True, validate and log without writing. Set False for live writes.
        ai_router: AIRouter instance for LLM calls. If None, uses placeholder mode.

    Returns:
        dict with status, written_files list, errors list
    """
    proposal = load_proposal(pid)
    if not proposal:
        return {"error": f"Proposal {pid} not found", "status": "failed"}

    feature = proposal.get("feature", "unknown")
    files = proposal.get("files_to_modify", [])
    results = {
        "status": "dry_run" if dry_run else "executed",
        "feature": feature,
        "pid": pid,
        "written_files": [],
        "errors": [],
        "generated": [],
    }

    if ai_router is None:
        # Fallback to placeholder mode if no LLM available
        return await _execute_placeholder(pid, feature, files, results, dry_run)

    from app.services.openclaw.code_tools import v10_write_file

    # Validate all paths upfront
    path_results = validate_proposal_paths(files)

    # Production path guard
    if any("empire-repo/" in f and "empire-repo-v10/" not in f for f in files):
        results["errors"].append("PROD_PATH_BLOCKED: Cannot write to production ~/empire-repo/")
        results["status"] = "blocked"
        _log_audit(results, dry_run)
        return results

    # Backup phase
    if not dry_run:
        for (resolved, err) in path_results:
            if err or not resolved:
                continue
            if resolved.exists():
                backup_file(resolved)
                results["written_files"].append(str(resolved) + ".bak")

    if results["errors"]:
        results["status"] = "validation_failed"
        _log_audit(results, dry_run)
        return results

    # Generate + Write phase
    if not dry_run:
        for (resolved, err), file_path in zip(path_results, files):
            if err or not resolved:
                continue

            # Generate code via LLM
            content, ok = await _generate_file_content(feature, file_path, ai_router)
            results["generated"].append(file_path)

            if not ok:
                results["errors"].append(f"{file_path}: LLM generation failed")

            # Syntax validation
            if ok and not _syntax_check(content, file_path):
                results["errors"].append(f"{file_path}: syntax check failed (unbalanced braces)")
                ok = False

            if ok:
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                # Strip thinking blocks before writing
                if isinstance(content, str):
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                write_result = v10_write_file(
                    str(resolved), content, mode="overwrite", dry_run=False, confirm=True
                )
                if "error" in write_result:
                    results["errors"].append(f"{resolved}: {write_result['error']}")
                else:
                    results["written_files"].append(str(resolved))
            else:
                # Restore backup on failure
                if resolved.exists() and str(resolved) + ".bak" in results["written_files"]:
                    restore_backup(resolved)
                    results["written_files"].remove(str(resolved) + ".bak")

    results["status"] = "success" if not results["errors"] else "partial"
    _log_audit(results, dry_run)
    return results


async def _execute_placeholder(pid: str, feature: str, files: list, results: dict, dry_run: bool) -> dict:
    """Fallback: write placeholder stubs when no LLM is available."""
    from app.services.openclaw.code_tools import v10_write_file

    path_results = validate_proposal_paths(files)

    if not dry_run:
        for (resolved, err) in path_results:
            if err or not resolved:
                continue
            if resolved.exists():
                backup_file(resolved)
                results["written_files"].append(str(resolved) + ".bak")

    if not dry_run:
        for (resolved, err), file_path in zip(path_results, files):
            if err or not resolved:
                continue

            content = _generate_placeholder(feature, resolved)
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            # Strip thinking blocks before writing
            if isinstance(content, str):
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            write_result = v10_write_file(
                str(resolved), content, mode="overwrite", dry_run=False, confirm=True
            )
            if "error" in write_result:
                results["errors"].append(f"{resolved}: {write_result['error']}")
            else:
                results["written_files"].append(str(resolved))

    results["status"] = "success" if not results["errors"] else "partial"
    _log_audit(results, dry_run)
    return results


def _generate_placeholder(feature: str, path: Path) -> str:
    """Generate placeholder implementation stub."""
    ext = path.suffix
    lang_map = {".py": "python", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript", ".jsx": "javascript"}
    lang = lang_map.get(ext, "text")

    if lang == "python":
        return f'''# Generated by MAX — EmpireBox Autonomous Engine
# Feature: {feature}
# Path: {path}
# Status: PLACEHOLDER

def placeholder_{feature.replace(" ", "_").lower()}():
    """{feature} — implemented by MAX orchestrator."""
    raise NotImplementedError("MAX placeholder")
'''
    else:
        return f'''// Generated by MAX — EmpireBox Autonomous Engine
// Feature: {feature}
// Path: {path}
// Status: PLACEHOLDER

function placeholder_{feature.replace(" ", "_").lower()}() {{
    // {feature}
    throw new Error("MAX placeholder");
}}
'''


def _log_audit(results: dict, dry_run: bool):
    """Append execution result to audit log."""
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "pid": results["pid"],
            "feature": results["feature"],
            "status": results["status"],
            "written_files": results.get("written_files", []),
            "generated": results.get("generated", []),
            "errors": results.get("errors", []),
            "dry_run": dry_run,
        }
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass