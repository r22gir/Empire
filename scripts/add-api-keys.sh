#!/bin/bash
# Empire API Key Setup Script
# Run after completing account signups from docs/account-signup-prep.md
# Usage: ./scripts/add-api-keys.sh

ENV_FILE=~/empire-repo/backend/.env

echo "═══════════════════════════════════════════"
echo "  Empire API Key Setup"
echo "  Paste each key when prompted."
echo "  Press Enter to skip any service."
echo "═══════════════════════════════════════════"
echo ""

# Social
echo "── Social Media ──"
read -p "INSTAGRAM_API_TOKEN: " val && [ -n "$val" ] && echo "INSTAGRAM_API_TOKEN=$val" >> "$ENV_FILE"
read -p "FACEBOOK_PAGE_TOKEN: " val && [ -n "$val" ] && echo "FACEBOOK_PAGE_TOKEN=$val" >> "$ENV_FILE"
read -p "GOOGLE_BUSINESS_API_KEY: " val && [ -n "$val" ] && echo "GOOGLE_BUSINESS_API_KEY=$val" >> "$ENV_FILE"
read -p "PINTEREST_API_TOKEN: " val && [ -n "$val" ] && echo "PINTEREST_API_TOKEN=$val" >> "$ENV_FILE"

echo ""
echo "── Shipping ──"
read -p "SHIPSTATION_API_KEY: " val && [ -n "$val" ] && echo "SHIPSTATION_API_KEY=$val" >> "$ENV_FILE"
read -p "SHIPSTATION_API_SECRET: " val && [ -n "$val" ] && echo "SHIPSTATION_API_SECRET=$val" >> "$ENV_FILE"
read -p "SHIPPO_API_TOKEN (backup): " val && [ -n "$val" ] && echo "SHIPPO_API_TOKEN=$val" >> "$ENV_FILE"

echo ""
echo "── Marketplace ──"
read -p "EBAY_APP_ID: " val && [ -n "$val" ] && echo "EBAY_APP_ID=$val" >> "$ENV_FILE"
read -p "EBAY_CERT_ID: " val && [ -n "$val" ] && echo "EBAY_CERT_ID=$val" >> "$ENV_FILE"
read -p "EBAY_DEV_ID: " val && [ -n "$val" ] && echo "EBAY_DEV_ID=$val" >> "$ENV_FILE"
read -p "ETSY_API_KEY: " val && [ -n "$val" ] && echo "ETSY_API_KEY=$val" >> "$ENV_FILE"

echo ""
echo "── Communication ──"
read -p "SENDGRID_API_KEY: " val && [ -n "$val" ] && echo "SENDGRID_API_KEY=$val" >> "$ENV_FILE"
read -p "TWILIO_SID: " val && [ -n "$val" ] && echo "TWILIO_SID=$val" >> "$ENV_FILE"
read -p "TWILIO_AUTH_TOKEN: " val && [ -n "$val" ] && echo "TWILIO_AUTH_TOKEN=$val" >> "$ENV_FILE"
read -p "TWILIO_PHONE (e.g. +12025551234): " val && [ -n "$val" ] && echo "TWILIO_PHONE=$val" >> "$ENV_FILE"

echo ""
chmod 600 "$ENV_FILE"
echo "═══════════════════════════════════════════"
echo "  Done! Keys added to $ENV_FILE"
echo "  File permissions set to 600 (owner only)"
echo ""
echo "  Next: restart the backend"
echo "  cd ~/empire-repo/backend && pkill -f uvicorn"
echo "  source venv/bin/activate"
echo "  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo "═══════════════════════════════════════════"
