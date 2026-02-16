#!/bin/bash

# MarketForge API Test Script
# This script tests the MarketForge API endpoints

API_URL="http://localhost:8000"

echo "🧪 MarketForge API Test Suite"
echo "=============================="
echo ""

# Test 1: Health Check
echo "1️⃣  Testing health endpoint..."
curl -s "${API_URL}/health" | python3 -m json.tool
echo ""

# Test 2: Root endpoint
echo "2️⃣  Testing root endpoint..."
curl -s "${API_URL}/" | python3 -m json.tool
echo ""

# Test 3: Register a test user
echo "3️⃣  Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "${API_URL}/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpassword123"}')
echo $REGISTER_RESPONSE | python3 -m json.tool
echo ""

# Test 4: Login
echo "4️⃣  Logging in..."
TOKEN_RESPONSE=$(curl -s -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123")
echo $TOKEN_RESPONSE | python3 -m json.tool

# Extract token
TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
echo ""

if [ -z "$TOKEN" ]; then
    echo "⚠️  Could not get token (user might already exist)"
    echo "   Try logging in manually or delete the database file"
    exit 0
fi

# Test 5: Get current user
echo "5️⃣  Getting current user info..."
curl -s "${API_URL}/auth/me" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
echo ""

# Test 6: Get listings (should be empty)
echo "6️⃣  Getting listings..."
curl -s "${API_URL}/listings/" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -m json.tool
echo ""

echo "✅ API tests complete!"
echo ""
echo "Next steps:"
echo "- Visit ${API_URL}/docs for interactive API documentation"
echo "- Create a listing using the Flutter app or API docs"
echo "- Configure marketplace API credentials in .env file"
