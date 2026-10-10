import os
import sys
import time
import subprocess
import signal
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    screenshots_dir = Path("/opt/cursor/artifacts/screenshots")
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["EMPIRE_TASK_DB"] = "/tmp/screenshot_empire.db"
    env["EMPIRE_DB"] = "/tmp/screenshot_empire.db"
    env["NEXT_PUBLIC_API_URL"] = "http://localhost:8000/api/v1"
    env["PORT"] = "3005"

    backend_proc = None
    frontend_proc = None

    try:
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd="/workspace/backend",
            env=env,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        frontend_proc = subprocess.Popen(
            ["npx", "next", "start", "-p", "3005"],
            cwd="/workspace/empire-command-center",
            env=env,
            preexec_fn=os.setsid,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        import urllib.request
        max_retries = 30
        for i in range(max_retries):
            try:
                urllib.request.urlopen("http://127.0.0.1:8000/api/v1/jobs/kanban", timeout=1)
                break
            except Exception:
                time.sleep(1)

        for i in range(max_retries):
            try:
                urllib.request.urlopen("http://127.0.0.1:3005", timeout=1)
                break
            except Exception:
                time.sleep(1)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Desktop view scrolled to production/fabric columns
            desktop_page = browser.new_page(viewport={"width": 1280, "height": 800})
            desktop_page.goto("http://localhost:3005/?screen=jobs", wait_until="networkidle")
            desktop_page.wait_for_timeout(2500)
            desktop_page.wait_for_selector("text=In production", timeout=10000)
            
            # Scroll kanban container horizontally to show middle columns
            desktop_page.evaluate("""() => {
                const containers = document.querySelectorAll('div');
                for (const el of containers) {
                    if (el.scrollWidth > el.clientWidth && el.scrollWidth > 1500) {
                        el.scrollLeft = 850;
                        break;
                    }
                }
            }""")
            desktop_page.wait_for_timeout(1000)
            active_cols_path = screenshots_dir / "kanban_columns_active.png"
            desktop_page.screenshot(path=str(active_cols_path), full_page=False)
            print(f"  ✓ Saved active columns screenshot to {active_cols_path}")

            browser.close()

    finally:
        if frontend_proc:
            try:
                os.killpg(os.getpgid(frontend_proc.pid), signal.SIGKILL)
            except Exception:
                pass
        if backend_proc:
            try:
                os.killpg(os.getpgid(backend_proc.pid), signal.SIGKILL)
            except Exception:
                pass

if __name__ == "__main__":
    main()
