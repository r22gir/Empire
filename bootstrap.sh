#!/bin/bash
# Empire Platform — Bootstrap Installer
# Idempotent — safe to run multiple times
set -e
echo "═══════════════════════════════════════"
echo "  EMPIRE BOOTSTRAP — $(date)"
echo "═══════════════════════════════════════"

REPO=~/empire-repo

# 1. Create directories
echo "1. Creating directories..."
mkdir -p $REPO/{manifests,knowledge,playbooks,templates/{campaigns,drawings},logs}
mkdir -p $REPO/.session-artifacts/{max,openclaw,leadforge,drawings,self-heal,socialforge,polish}

# 2. Check manifests exist
echo "2. Checking manifests..."
for f in skill_manifest.json feature_flags.json; do
  [ -f $REPO/manifests/$f ] && echo "  ✓ $f" || echo "  ✗ $f MISSING"
done

# 3. Check key services
echo "3. Checking services..."
curl -s -o /dev/null -w "  Backend :8000 → HTTP %{http_code}\n" --max-time 3 localhost:8000/health 2>/dev/null
curl -s -o /dev/null -w "  CC :3005 → HTTP %{http_code}\n" --max-time 3 localhost:3005 2>/dev/null

# 4. Check Python modules
echo "4. Checking Python modules..."
cd $REPO/backend && source venv/bin/activate 2>/dev/null
python3 -c "
import sys; sys.path.insert(0,'.')
modules = [
    'app.services.max.capability_loader',
    'app.services.max.conversation_mode',
    'app.services.max.founder_auth',
    'app.services.max.transport_matrix',
    'app.services.max.self_heal',
    'app.services.vision.product_catalog',
    'app.services.vision.renderer_registry',
    'app.services.vision.primitives',
    'app.services.leadforge.prospect_engine',
    'app.services.leadforge.campaign_service',
]
for m in modules:
    try:
        __import__(m)
        print(f'  ✓ {m.split(\".\")[-1]}')
    except Exception as e:
        print(f'  ✗ {m.split(\".\")[-1]}: {e}')
" 2>/dev/null

# 5. Check DB tables
echo "5. Checking database tables..."
python3 -c "
import sqlite3, os
c = sqlite3.connect(os.path.expanduser('~/empire-repo/backend/data/empire.db'))
tables = ['customers','tasks','prospects','campaigns','campaign_steps','self_heal_log','conversation_modes','business_profiles','social_accounts','jobs']
for t in tables:
    try:
        count = c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f'  ✓ {t}: {count} rows')
    except: print(f'  ✗ {t}: MISSING')
" 2>/dev/null

# 6. Product catalog
echo "6. Product catalog..."
python3 -c "
import sys; sys.path.insert(0,'.')
from app.services.vision.product_catalog import get_total_styles, get_all_types
print(f'  {len(get_all_types())} categories, {get_total_styles()} styles')
" 2>/dev/null

echo ""
echo "═══════════════════════════════════════"
echo "  BOOTSTRAP COMPLETE"
echo "═══════════════════════════════════════"
