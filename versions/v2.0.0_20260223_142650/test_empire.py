#!/usr/bin/env python3
"""
EmpireBox Unified Test Suite
Run: python test_empire.py
Generates: test_results.json (downloadable)
"""

import requests
import json
import subprocess
import os
from datetime import datetime
from pathlib import Path

BASE_URL = os.getenv("API_URL", "http://localhost:8000")
RESULTS = {"timestamp": datetime.now().isoformat(), "environment": {}, "tests": []}

def log(msg, status="INFO"):
    icons = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}
    print(f"{icons.get(status, 'ℹ️')} {msg}")

def test(name, func):
    try:
        result = func()
        RESULTS["tests"].append({"name": name, "status": "PASS", "details": result})
        log(f"{name}", "PASS")
        return True
    except Exception as e:
        RESULTS["tests"].append({"name": name, "status": "FAIL", "error": str(e)})
        log(f"{name}: {e}", "FAIL")
        return False

# ============ ENVIRONMENT CHECKS ============
def check_env():
    log("=== Environment Checks ===")
    RESULTS["environment"]["python"] = subprocess.getoutput("python3 --version")
    RESULTS["environment"]["node"] = subprocess.getoutput("node --version 2>/dev/null || echo 'Not installed'")
    RESULTS["environment"]["npm"] = subprocess.getoutput("npm --version 2>/dev/null || echo 'Not installed'")
    RESULTS["environment"]["cwd"] = os.getcwd()
    
    env_file = Path.home() / "Empire/backend/.env"
    RESULTS["environment"]["env_exists"] = env_file.exists()
    
    for k, v in RESULTS["environment"].items():
        log(f"{k}: {v}")

# ============ BACKEND API TESTS ============
def test_backend():
    log("\n=== Backend API Tests ===")
    
    test("API Root", lambda: requests.get(f"{BASE_URL}/").json())
    test("Health Check", lambda: requests.get(f"{BASE_URL}/health").json())
    test("OpenAPI Docs", lambda: requests.get(f"{BASE_URL}/openapi.json").status_code == 200)
    
    # MAX AI endpoint
    def test_max():
        resp = requests.post(f"{BASE_URL}/api/v1/max/chat", 
            json={"message": "test", "provider": "claude"},
            timeout=30)
        return resp.json()
    test("MAX AI Chat", test_max)

# ============ FRONTEND BUILD CHECKS ============
def test_frontends():
    log("\n=== Frontend Build Checks ===")
    
    apps = [
        ("founder_dashboard", 3000),
        ("luxeforge_web", 3001),
        ("contractorforge_web", 3002),
        ("marketf_web", 3003),
    ]
    
    for app, port in apps:
        app_path = Path.home() / f"Empire/{app}"
        
        # Check if app exists
        test(f"{app} - exists", lambda p=app_path: p.exists())
        
        # Check package.json
        pkg = app_path / "package.json"
        if pkg.exists():
            test(f"{app} - package.json valid", lambda p=pkg: json.loads(p.read_text()))
        
        # Check if node_modules exists
        nm = app_path / "node_modules"
        test(f"{app} - dependencies installed", lambda n=nm: n.exists())
        
        # Check if .next build exists
        next_dir = app_path / ".next"
        test(f"{app} - built (.next)", lambda n=next_dir: n.exists())

# ============ PAGE INVENTORY ============
def inventory_pages():
    log("\n=== Page Inventory ===")
    
    pages = {
        "founder_dashboard": [
            "src/app/page.tsx",
            "src/app/layout.tsx",
        ],
        "luxeforge_web": [
            "src/app/page.tsx",
            "src/app/layout.tsx",
            "src/app/pricing/page.tsx",
            "src/app/features/page.tsx",
            "src/app/contact/page.tsx",
        ],
        "contractorforge_web": [
            "src/app/page.tsx",
            "src/app/layout.tsx",
            "src/app/pricing/page.tsx",
        ],
        "marketf_web": [
            "src/app/page.tsx",
            "src/app/layout.tsx",
            "src/app/search/page.tsx",
            "src/app/seller/dashboard/page.tsx",
            "src/app/product/[id]/page.tsx",
        ],
    }
    
    RESULTS["pages"] = {}
    for app, page_list in pages.items():
        RESULTS["pages"][app] = []
        for page in page_list:
            full_path = Path.home() / f"Empire/{app}/{page}"
            exists = full_path.exists()
            RESULTS["pages"][app].append({"path": page, "exists": exists})
            status = "PASS" if exists else "FAIL"
            log(f"{app}/{page}", status)

# ============ BACKEND ROUTERS ============
def inventory_routers():
    log("\n=== Backend Router Inventory ===")
    
    routers = [
        "ai.py", "auth.py", "economic.py", "licenses.py", "listings.py",
        "marketplaces.py", "messages.py", "preorders.py", "shipping.py",
        "supportforge_ai.py", "supportforge_customers.py", "supportforge_kb.py",
        "supportforge_tickets.py", "users.py", "webhooks.py", "max/"
    ]
    
    RESULTS["routers"] = []
    router_path = Path.home() / "Empire/backend/app/routers"
    
    for router in routers:
        full_path = router_path / router
        exists = full_path.exists()
        RESULTS["routers"].append({"name": router, "exists": exists})
        status = "PASS" if exists else "FAIL"
        log(f"Router: {router}", status)

# ============ GENERATE REPORT ============
def generate_report():
    log("\n=== Generating Report ===")
    
    passed = sum(1 for t in RESULTS["tests"] if t["status"] == "PASS")
    failed = sum(1 for t in RESULTS["tests"] if t["status"] == "FAIL")
    
    RESULTS["summary"] = {
        "total": len(RESULTS["tests"]),
        "passed": passed,
        "failed": failed,
        "pass_rate": f"{(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A"
    }
    
    # Save JSON report
    report_path = Path.home() / "Empire/test_results.json"
    with open(report_path, "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)
    
    log(f"Report saved: {report_path}")
    log(f"\n📊 Summary: {passed} passed, {failed} failed ({RESULTS['summary']['pass_rate']})")
    
    return report_path

# ============ MAIN ============
if __name__ == "__main__":
    print("=" * 50)
    print("🏰 EmpireBox Unified Test Suite")
    print("=" * 50)
    
    check_env()
    test_backend()
    test_frontends()
    inventory_pages()
    inventory_routers()
    report_path = generate_report()
    
    print("\n" + "=" * 50)
    print(f"📥 Download: {report_path}")
    print("=" * 50)
