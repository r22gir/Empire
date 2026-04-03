#!/bin/bash
BUSINESS=${1:-workroom}
echo "═══════════════════════════════════════"
echo "  SOCIAL ACCOUNT SETUP — $BUSINESS"
echo "═══════════════════════════════════════"

DATA=$(curl -s "http://localhost:8000/api/v1/socialforge/setup-wizard/$BUSINESS" 2>/dev/null)
if [ -z "$DATA" ] || echo "$DATA" | grep -q '"detail"'; then
    echo "Backend not responding — check that it's running"
    exit 1
fi

echo "$DATA" | python3 -c "
import sys, json
d = json.load(sys.stdin)
biz = d.get('business', {})
print(f'Business: {biz.get(\"name\",\"?\")} ({biz.get(\"email\",\"?\")})')
print(f'Connected: {d.get(\"completed\",0)}/{d.get(\"total\",0)}')
print()
for step in d.get('steps', []):
    status = step.get('status','?')
    emoji = '✅' if status == 'active' else '⏳' if 'pending' in status else '❌'
    print(f'{emoji} {step[\"platform\"].upper()} — {status}')
    if status != 'active':
        for k, v in step.get('prefill_data', {}).items():
            if v: print(f'    {k}: {v}')
        if step.get('signup_url'):
            print(f'    URL: {step[\"signup_url\"]}')
    print()
" 2>/dev/null

# Open browser tabs for pending platforms
if command -v xdg-open &> /dev/null; then
    echo "$DATA" | python3 -c "
import sys, json, subprocess, time
d = json.load(sys.stdin)
for step in d.get('steps', []):
    if step.get('status') != 'active' and step.get('signup_url'):
        subprocess.Popen(['xdg-open', step['signup_url']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
" 2>/dev/null
    echo "Browser tabs opened for pending platforms."
fi
echo ""
echo "When done: ~/empire-repo/scripts/social-verify-all.sh $BUSINESS"
