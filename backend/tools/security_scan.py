#!/usr/bin/env python3
"""
Empire Security Scanner — checks all source code for vulnerabilities,
exposed secrets, malicious patterns, and dependency issues.

Usage:
    python3 tools/security_scan.py [--full] [--json]
"""
import os
import re
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

EMPIRE_ROOT = Path(__file__).parent.parent.parent  # ~/Empire
SCAN_DIRS = ["backend", "founder_dashboard/src", "workroomforge/src", "empire-app/src", "luxeforge_web/src"]

# ═══════════════════════════════════════════════════════
# SECRET PATTERNS — detect exposed keys, tokens, passwords
# ═══════════════════════════════════════════════════════
SECRET_PATTERNS = [
    (r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', "API Key exposed"),
    (r'(?:secret|password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']', "Secret/Password in code"),
    (r'(?:token)\s*[=:]\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']', "Token exposed"),
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
    (r'xai-[a-zA-Z0-9]{20,}', "xAI API key"),
    (r'sk-ant-[a-zA-Z0-9\-]{20,}', "Anthropic API key"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub personal access token"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private key in code"),
    (r'(?:mongodb|postgres|mysql)://[^\s"\']+:[^\s"\']+@', "Database connection string with credentials"),
]

# ═══════════════════════════════════════════════════════
# MALICIOUS PATTERNS — detect dangerous code
# ═══════════════════════════════════════════════════════
MALICIOUS_PATTERNS = [
    (r'eval\s*\(', "eval() usage — potential code injection"),
    (r'exec\s*\(', "exec() usage — potential code execution"),
    (r'__import__\s*\(', "Dynamic import — potential module injection"),
    (r'subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True', "Shell injection risk — shell=True"),
    (r'os\.system\s*\(', "os.system() — prefer subprocess with shell=False"),
    (r'innerHTML\s*=', "innerHTML assignment — XSS risk"),
    (r'dangerouslySetInnerHTML', "React dangerouslySetInnerHTML — XSS risk"),
    (r'document\.write\s*\(', "document.write() — XSS risk"),
    (r'window\.location\s*=\s*[^"\'`]', "Unvalidated redirect"),
    (r'SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*\s*\+\s*', "SQL concatenation — injection risk"),
    (r'f["\'].*SELECT.*\{', "Python f-string SQL — injection risk"),
    (r'\.query\s*\(\s*[`"\'].*\$\{', "Template literal SQL — injection risk"),
    (r'pickle\.loads?\s*\(', "Pickle deserialization — arbitrary code execution"),
    (r'yaml\.load\s*\([^)]*(?!Loader)', "Unsafe YAML load — use safe_load"),
    (r'crypto\.createHash\s*\(\s*["\']md5["\']', "MD5 hash — cryptographically weak"),
    (r'crypto\.createHash\s*\(\s*["\']sha1["\']', "SHA1 hash — cryptographically weak"),
    (r'Math\.random\s*\(\)', "Math.random() for security — use crypto.getRandomValues"),
    (r'atob\s*\(.*\)\s*;?\s*eval', "Base64 decode + eval — obfuscated execution"),
    (r'require\s*\(\s*[^"\'`]', "Dynamic require — potential dependency confusion"),
    (r'fetch\s*\(\s*[^"\'`].*\+', "Unvalidated fetch URL construction"),
]

# ═══════════════════════════════════════════════════════
# VULNERABILITY PATTERNS
# ═══════════════════════════════════════════════════════
VULN_PATTERNS = [
    (r'cors.*origin.*\*|CORS.*\*|Access-Control-Allow-Origin.*\*', "CORS wildcard — allows any origin"),
    (r'verify\s*=\s*False|ssl\s*=\s*False|check_hostname\s*=\s*False', "SSL verification disabled"),
    (r'debug\s*=\s*True|DEBUG\s*=\s*True', "Debug mode enabled in production code"),
    (r'(?:chmod|permissions?).*777', "World-writable permissions"),
    (r'(?:http://)\s*(?!localhost|127\.0\.0\.1|0\.0\.0\.0)', "HTTP (not HTTPS) external URL"),
    (r'\.env\b.*(?:gitignore|commit)', "Env file management issue"),
    (r'TODO.*(?:security|auth|token|password|secret|hack|fix)', "Security-related TODO"),
]

SKIP_EXTENSIONS = {'.pyc', '.pyo', '.so', '.wasm', '.ico', '.png', '.jpg', '.jpeg',
                   '.gif', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.map',
                   '.lock', '.min.js', '.min.css'}
SKIP_DIRS = {'node_modules', '.next', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build', '.cache'}


class SecurityScanner:
    def __init__(self, root: Path):
        self.root = root
        self.findings = []
        self.stats = {"files_scanned": 0, "secrets": 0, "malicious": 0, "vulnerabilities": 0, "dependencies": 0}

    def scan_file(self, filepath: Path):
        """Scan a single file for security issues."""
        try:
            content = filepath.read_text(errors='ignore')
        except Exception:
            return

        self.stats["files_scanned"] += 1
        rel_path = str(filepath.relative_to(self.root))
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('*'):
                continue

            # Check secrets
            for pattern, desc in SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip .env files (expected to have secrets) and example files
                    if '.env' in rel_path and 'example' not in rel_path.lower():
                        continue
                    self.findings.append({
                        "type": "SECRET", "severity": "CRITICAL",
                        "file": rel_path, "line": line_num,
                        "description": desc,
                        "snippet": line.strip()[:120],
                    })
                    self.stats["secrets"] += 1

            # Check malicious patterns
            for pattern, desc in MALICIOUS_PATTERNS:
                if re.search(pattern, line):
                    self.findings.append({
                        "type": "MALICIOUS", "severity": "HIGH",
                        "file": rel_path, "line": line_num,
                        "description": desc,
                        "snippet": line.strip()[:120],
                    })
                    self.stats["malicious"] += 1

            # Check vulnerabilities
            for pattern, desc in VULN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    self.findings.append({
                        "type": "VULNERABILITY", "severity": "MEDIUM",
                        "file": rel_path, "line": line_num,
                        "description": desc,
                        "snippet": line.strip()[:120],
                    })
                    self.stats["vulnerabilities"] += 1

    def scan_directory(self, dir_path: Path):
        """Recursively scan a directory."""
        if not dir_path.exists():
            return
        for item in dir_path.rglob('*'):
            if item.is_file():
                if any(skip in item.parts for skip in SKIP_DIRS):
                    continue
                if item.suffix in SKIP_EXTENSIONS:
                    continue
                self.scan_file(item)

    def check_npm_audit(self):
        """Run npm audit on Node.js projects."""
        for proj in ["founder_dashboard", "workroomforge", "empire-app"]:
            pkg = self.root / proj / "package.json"
            if pkg.exists():
                try:
                    result = subprocess.run(
                        ["npm", "audit", "--json"],
                        cwd=str(self.root / proj),
                        capture_output=True, text=True, timeout=30,
                    )
                    data = json.loads(result.stdout) if result.stdout else {}
                    vulns = data.get("vulnerabilities", {})
                    for name, info in vulns.items():
                        severity = info.get("severity", "unknown")
                        self.findings.append({
                            "type": "DEPENDENCY", "severity": severity.upper(),
                            "file": f"{proj}/package.json",
                            "line": 0,
                            "description": f"npm: {name} — {info.get('via', [{}])[0].get('title', severity) if isinstance(info.get('via', [{}])[0], dict) else severity}",
                            "snippet": f"Fix: npm audit fix in {proj}/",
                        })
                        self.stats["dependencies"] += 1
                except Exception as e:
                    self.findings.append({
                        "type": "DEPENDENCY", "severity": "INFO",
                        "file": f"{proj}/package.json", "line": 0,
                        "description": f"npm audit failed: {e}", "snippet": "",
                    })

    def check_pip_audit(self):
        """Check Python dependencies for known vulnerabilities."""
        req_file = self.root / "backend" / "requirements.txt"
        if req_file.exists():
            try:
                result = subprocess.run(
                    ["pip", "audit", "--format=json"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout) if result.stdout else {}
                    for vuln in data.get("vulnerabilities", []):
                        self.findings.append({
                            "type": "DEPENDENCY", "severity": "HIGH",
                            "file": "backend/requirements.txt", "line": 0,
                            "description": f"pip: {vuln.get('name')} — {vuln.get('description', '')[:100]}",
                            "snippet": f"Installed: {vuln.get('version')}, Fix: {vuln.get('fix_versions', 'N/A')}",
                        })
                        self.stats["dependencies"] += 1
            except FileNotFoundError:
                pass  # pip-audit not installed
            except Exception:
                pass

    def run(self, full=False):
        """Run the full security scan."""
        print(f"\n{'='*60}")
        print(f"  EMPIRE SECURITY SCANNER")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # Scan source code
        for scan_dir in SCAN_DIRS:
            dir_path = self.root / scan_dir
            if dir_path.exists():
                print(f"  Scanning {scan_dir}...", end=" ", flush=True)
                before = self.stats["files_scanned"]
                self.scan_directory(dir_path)
                print(f"{self.stats['files_scanned'] - before} files")

        # Dependency checks
        if full:
            print(f"\n  Checking npm dependencies...", flush=True)
            self.check_npm_audit()
            print(f"  Checking pip dependencies...", flush=True)
            self.check_pip_audit()

        # Report
        self._print_report()
        return self.findings

    def _print_report(self):
        """Print formatted security report."""
        sev_colors = {"CRITICAL": "\033[91m", "HIGH": "\033[93m", "MEDIUM": "\033[33m", "LOW": "\033[36m", "INFO": "\033[90m"}
        reset = "\033[0m"

        print(f"\n{'='*60}")
        print(f"  RESULTS")
        print(f"{'='*60}\n")
        print(f"  Files scanned:    {self.stats['files_scanned']}")
        print(f"  Secrets found:    {sev_colors['CRITICAL']}{self.stats['secrets']}{reset}")
        print(f"  Malicious code:   {sev_colors['HIGH']}{self.stats['malicious']}{reset}")
        print(f"  Vulnerabilities:  {sev_colors['MEDIUM']}{self.stats['vulnerabilities']}{reset}")
        print(f"  Dependency issues:{sev_colors['LOW']}{self.stats['dependencies']}{reset}")
        print()

        if not self.findings:
            print(f"  \033[92m✓ No security issues found!\033[0m\n")
            return

        # Group by type
        for finding_type in ["SECRET", "MALICIOUS", "VULNERABILITY", "DEPENDENCY"]:
            group = [f for f in self.findings if f["type"] == finding_type]
            if not group:
                continue

            print(f"  ── {finding_type} ({len(group)}) ──")
            for f in group[:20]:  # Limit output
                color = sev_colors.get(f["severity"], "")
                print(f"    {color}[{f['severity']}]{reset} {f['file']}:{f['line']}")
                print(f"      {f['description']}")
                if f['snippet']:
                    print(f"      → {f['snippet'][:100]}")
            if len(group) > 20:
                print(f"    ... and {len(group) - 20} more")
            print()

        total = sum(self.stats[k] for k in ["secrets", "malicious", "vulnerabilities", "dependencies"])
        print(f"  Total issues: {total}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    full = "--full" in sys.argv
    as_json = "--json" in sys.argv

    scanner = SecurityScanner(EMPIRE_ROOT)
    findings = scanner.run(full=full)

    if as_json:
        print(json.dumps({
            "scan_time": datetime.now().isoformat(),
            "stats": scanner.stats,
            "findings": findings,
        }, indent=2))
