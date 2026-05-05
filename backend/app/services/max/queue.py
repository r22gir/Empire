"""MAX Prompt Queue."""
import json, os, time
from pathlib import Path

BASE = Path(os.path.expanduser("~/empire-repo-v10/backend/data/max"))
PENDING = BASE / "pending_prompts.jsonl"
PROPOSALS = BASE / "proposals"
APPROVALS = BASE / "approvals"

PENDING.parent.mkdir(parents=True, exist_ok=True)
PENDING.touch(exist_ok=True)

def add_prompt(text: str, priority: str = "medium"):
    entry = {"id": f"p_{int(time.time())}", "text": text, "priority": priority, "status": "pending", "ts": time.time()}
    with open(PENDING, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry["id"]

def get_pending(n=5):
    items = [json.loads(l) for l in open(PENDING) if l.strip()]
    prio = {"high": 0, "medium": 1, "low": 2}
    return sorted(items, key=lambda x: prio.get(x.get("priority", "medium"), 1))[:n]

def mark_done(pid):
    tmp = PENDING.with_suffix(".tmp")
    with open(PENDING) as fin, open(tmp, "w") as fout:
        for l in fin:
            if l.strip():
                try:
                    entry = json.loads(l)
                    if entry.get("id") == pid:
                        continue  # skip this one (done)
                    fout.write(l)
                except json.JSONDecodeError:
                    continue  # skip malformed lines
    tmp.rename(PENDING)

def save_proposal(pid, data):
    (PROPOSALS / f"{pid}.json").write_text(json.dumps(data, indent=2))

def check_approval(pid):
    p = APPROVALS / f"{pid}.txt"
    if p.exists():
        r = p.read_text().strip().lower()
        p.unlink()
        return r
    return None