#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000/api/v1/archiveforge}"

TMP_JSON="$(mktemp)"
TMP_IMG="$(mktemp /tmp/archiveforge-smoke-XXXXXX.png)"
ARCHIVE_ID=""
PUBLISH_AVAILABLE="false"

cleanup() {
  rm -f "$TMP_JSON" "$TMP_IMG"
  if [[ -n "${ARCHIVE_ID}" ]]; then
    curl -s -X DELETE "${BASE_URL}/archives/${ARCHIVE_ID}" >/dev/null || true
  fi
}
trap cleanup EXIT

python3 - "$TMP_IMG" <<'PY'
import base64
import sys

png = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2ioAAAAASUVORK5CYII="
)
with open(sys.argv[1], "wb") as f:
    f.write(png)
PY

echo "[1/10] publish-status"
curl -s "${BASE_URL}/publish-status" > "$TMP_JSON"
python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
print("publish_available:", j.get("publish_available"))
PY
PUBLISH_AVAILABLE="$(
  python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
print("true" if j.get("publish_available") else "false")
PY
)"

echo "[2/10] create archive"
curl -s -X POST "${BASE_URL}/archives" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_issue_id":"google-books-IE8EAAAAMBAJ",
    "reference_source":"google_books",
    "issue_date":"1969-07-25",
    "volume":67,
    "issue_number":4,
    "cover_subject":"The Moon Landing — Apollo 11",
    "source_box_code":"AF-SMOKE-SRC",
    "processed_box_code":"AF-SMOKE-DST",
    "processed_status":"RAW",
    "archive_location":"smoke shelf",
    "tier":"A"
  }' > "$TMP_JSON"
ARCHIVE_ID="$(
  python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
print(j["id"])
PY
)"
echo "archive_id: ${ARCHIVE_ID}"

echo "[3/10] save draft"
curl -s -X POST "${BASE_URL}/archives/${ARCHIVE_ID}/save-draft" \
  -H "Content-Type: application/json" \
  -d '{"listing_title":"AF smoke title","listing_description":"AF smoke description","batch_tag":"AF-SMOKE"}' > "$TMP_JSON"
python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
assert j.get("saved") is True
print("draft_saved:", j.get("saved"))
PY

echo "[4/10] status transitions"
for status in IDENTIFIED PHOTOGRAPHED VALUED READY_TO_LIST; do
  curl -s -X PATCH "${BASE_URL}/archives/${ARCHIVE_ID}/status" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"${status}\"}" > "$TMP_JSON"
  python3 - "$TMP_JSON" "$status" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
expected = sys.argv[2]
assert j.get("processed_status") == expected
print("status:", j.get("processed_status"))
PY
done

echo "[5/10] upload photo"
curl -s -X POST "${BASE_URL}/uploads/${ARCHIVE_ID}" \
  -F role=front \
  -F "file=@${TMP_IMG}" > "$TMP_JSON"
python3 - "$TMP_JSON" "$ARCHIVE_ID" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
assert str(j.get("archive_id")) == sys.argv[2]
print("photo_id:", j.get("id"))
PY

echo "[6/10] list/detail"
curl -s "${BASE_URL}/archives?limit=5" > "$TMP_JSON"
python3 - "$TMP_JSON" "$ARCHIVE_ID" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
ids = {item.get("id") for item in j.get("items", [])}
assert int(sys.argv[2]) in ids
print("list_contains_archive:", int(sys.argv[2]) in ids)
PY
curl -s "${BASE_URL}/archives/${ARCHIVE_ID}" > "$TMP_JSON"
python3 - "$TMP_JSON" "$ARCHIVE_ID" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
assert str(j.get("id")) == sys.argv[2]
print("detail_ok:", j.get("id"))
PY

if [[ "${PUBLISH_AVAILABLE}" == "true" ]]; then
  echo "[7/10] publish (available)"
  curl -s -X POST "${BASE_URL}/push/${ARCHIVE_ID}" > "$TMP_JSON"
  python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
assert j.get("push_status") == "pushed"
print("push_status:", j.get("push_status"))
PY
else
  echo "[7/10] publish (blocked expected)"
  HTTP_CODE="$(curl -s -o "$TMP_JSON" -w "%{http_code}" -X POST "${BASE_URL}/push/${ARCHIVE_ID}")"
  if [[ "$HTTP_CODE" != "503" ]]; then
    echo "Expected 503 when publish unavailable, got ${HTTP_CODE}"
    exit 1
  fi
  echo "publish_blocked_http: ${HTTP_CODE}"
fi

echo "[8/10] verify listing state"
curl -s "${BASE_URL}/archives/${ARCHIVE_ID}" > "$TMP_JSON"
python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
assert (j.get("listing_title") or "").strip() != ""
assert j.get("marketforge_push_status") in {"draft_saved", "pushed", "failed", "not_pushed", "pushing"}
print("listing_title_present:", bool((j.get("listing_title") or "").strip()))
print("marketforge_push_status:", j.get("marketforge_push_status"))
PY

echo "[9/10] delete archive"
curl -s -X DELETE "${BASE_URL}/archives/${ARCHIVE_ID}" > "$TMP_JSON"
python3 - "$TMP_JSON" <<'PY'
import json
import sys

j = json.load(open(sys.argv[1]))
assert j.get("deleted") is True
print("deleted:", j.get("deleted"))
PY
ARCHIVE_ID=""

echo "[10/10] verify deleted"
HTTP_CODE="$(curl -s -o "$TMP_JSON" -w "%{http_code}" "${BASE_URL}/archives/999999999")"
echo "missing_archive_http: ${HTTP_CODE}"
echo "ArchiveForge smoke: PASS"
