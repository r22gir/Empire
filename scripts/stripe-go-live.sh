#!/bin/bash
echo "═══════════════════════════════════════"
echo "  STRIPE — SWITCH TO LIVE MODE"
echo "  WARNING: Live charges are REAL"
echo "═══════════════════════════════════════"
echo ""
echo "Get live keys from: https://dashboard.stripe.com/apikeys"
echo ""
read -p "Stripe Live Secret Key (sk_live_...): " LIVE_SECRET
read -p "Stripe Live Publishable Key (pk_live_...): " LIVE_PUB
if [[ $LIVE_SECRET != sk_live_* ]]; then echo "ERROR: Must start with sk_live_"; exit 1; fi
if [[ $LIVE_PUB != pk_live_* ]]; then echo "ERROR: Must start with pk_live_"; exit 1; fi
read -p "Are you sure? (type YES): " CONFIRM
if [ "$CONFIRM" != "YES" ]; then echo "Cancelled."; exit 0; fi
BACKUP=~/empire-repo/backend/.env.backup_stripe_$(date +%Y%m%d_%H%M)
cp ~/empire-repo/backend/.env $BACKUP
echo "Backup: $BACKUP"
sed -i "s|STRIPE_SECRET_KEY=.*|STRIPE_SECRET_KEY=$LIVE_SECRET|" ~/empire-repo/backend/.env
sed -i "s|STRIPE_PUBLISHABLE_KEY=.*|STRIPE_PUBLISHABLE_KEY=$LIVE_PUB|" ~/empire-repo/backend/.env
echo "Keys updated. Restarting backend..."
sudo systemctl restart empire-backend 2>/dev/null || (cd ~/empire-repo/backend && pkill -f uvicorn; sleep 2; source venv/bin/activate && nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &)
sleep 5
STATUS=$(curl -s -o /dev/null -w '%{http_code}' localhost:8000/health 2>/dev/null)
[ "$STATUS" = "200" ] && echo "Stripe is now LIVE. Backend healthy." || echo "Backend may need manual restart (HTTP $STATUS)"
