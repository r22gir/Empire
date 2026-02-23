"""Network monitoring tools for MAX and OpsBot"""
import subprocess
import json
from datetime import datetime

def get_active_connections():
    result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
    return result.stdout

def get_api_logs(lines=20):
    try:
        with open("/home/rg/Empire/logs/backend.log", "r") as f:
            return "\n".join(f.readlines()[-lines:])
    except:
        return "No logs available"

def system_status():
    return {
        "timestamp": datetime.now().isoformat(),
        "backend": subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000/health"], capture_output=True, text=True).stdout,
        "frontend": subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:3000"], capture_output=True, text=True).stdout,
        "ollama": subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:11434/api/tags"], capture_output=True, text=True).stdout,
    }

if __name__ == "__main__":
    print("=== EmpireBox Status ===")
    print(json.dumps(system_status(), indent=2))
    print("\n=== Connections ===")
    print(get_active_connections())
