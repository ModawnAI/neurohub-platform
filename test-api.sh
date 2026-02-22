#!/bin/bash
API="https://neurohub-api.fly.dev/api/v1"
H=(-H "X-User-Id: 11111111-1111-1111-1111-111111111111" -H "X-Username: dev-user" -H "X-Institution-Id: 00000000-0000-0000-0000-000000000001" -H "X-Roles: SYSTEM_ADMIN" -H "Content-Type: application/json")

test_endpoint() {
  local method=$1 path=$2 body=$3
  local code
  local resp
  if [ -z "$body" ]; then
    resp=$(curl -s -w "\n%{http_code}" -X "$method" "$API$path" "${H[@]}" 2>&1)
  else
    resp=$(curl -s -w "\n%{http_code}" -X "$method" "$API$path" "${H[@]}" -d "$body" 2>&1)
  fi
  code=$(echo "$resp" | tail -1)
  local body_out=$(echo "$resp" | head -1 | cut -c1-200)
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    echo "PASS [$code] $method $path => $body_out"
  else
    echo "FAIL [$code] $method $path => $body_out"
  fi
}

echo "========== NeuroHub API Endpoint Test =========="
echo ""

echo "--- Health ---"
test_endpoint GET "/health"
test_endpoint GET "/health/live"
test_endpoint GET "/health/ready"

echo ""
echo "--- Auth ---"
test_endpoint GET "/auth/me"

echo ""
echo "--- Services ---"
test_endpoint GET "/services"
test_endpoint GET "/services/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/pipelines"

echo ""
echo "--- Requests CRUD ---"
test_endpoint GET "/requests"
test_endpoint POST "/requests" '{"service_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","pipeline_id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb","priority":5,"cases":[{"patient_ref":"TEST-PT-002","demographics":{"age":45,"sex":"F"}}],"idempotency_key":"api-test-002"}'

# Get the created request ID
REQ_ID=$(curl -s -X GET "$API/requests" "${H[@]}" | python3 -c "import sys,json; items=json.load(sys.stdin)['items']; print(next((r['id'] for r in items if r['idempotency_key']=='api-test-002'), ''))" 2>/dev/null)
if [ -n "$REQ_ID" ]; then
  echo "  Created request: $REQ_ID"
  test_endpoint GET "/requests/$REQ_ID"

  echo ""
  echo "--- Upload Flow ---"
  # Get case ID
  CASE_ID=$(curl -s "$API/requests/$REQ_ID/cases" "${H[@]}" | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['id'])" 2>/dev/null)
  echo "  Case ID: $CASE_ID"
  test_endpoint GET "/requests/$REQ_ID/cases"
  if [ -n "$CASE_ID" ]; then
    test_endpoint POST "/requests/$REQ_ID/cases/$CASE_ID/files/presign" '{"slot_name":"primary","file_name":"brain_scan.dcm","content_type":"application/dicom","file_size":1024}'
    test_endpoint GET "/requests/$REQ_ID/cases/$CASE_ID/files"
  fi

  echo ""
  echo "--- Request Transitions ---"
  test_endpoint POST "/requests/$REQ_ID/transition" '{"target_status":"STAGING","note":"Test staging"}'
  test_endpoint POST "/requests/$REQ_ID/confirm" '{"confirm_note":"Test confirm"}'
  test_endpoint POST "/requests/$REQ_ID/submit" ''

  echo ""
  echo "--- Cancel Flow (separate request) ---"
  test_endpoint POST "/requests" '{"service_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","pipeline_id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb","priority":3,"cases":[{"patient_ref":"TEST-PT-003"}],"idempotency_key":"api-test-cancel-001"}'
  REQ2_ID=$(curl -s -X GET "$API/requests" "${H[@]}" | python3 -c "import sys,json; items=json.load(sys.stdin)['items']; print(next((r['id'] for r in items if r['idempotency_key']=='api-test-cancel-001'), ''))" 2>/dev/null)
  if [ -n "$REQ2_ID" ]; then
    test_endpoint POST "/requests/$REQ2_ID/cancel" '{"reason":"Testing cancel flow"}'
  fi
fi

echo ""
echo "--- Organizations ---"
test_endpoint GET "/organizations"
test_endpoint GET "/organizations/00000000-0000-0000-0000-000000000001/members"

echo ""
echo "--- Users ---"
test_endpoint GET "/users"
test_endpoint GET "/users/11111111-1111-1111-1111-111111111111"

echo ""
echo "--- Admin ---"
test_endpoint GET "/admin/stats"
test_endpoint GET "/admin/requests"
test_endpoint GET "/admin/audit-logs"

echo ""
echo "--- Notifications ---"
test_endpoint GET "/notifications"
test_endpoint POST "/notifications/read-all"

echo ""
echo "--- Billing ---"
test_endpoint GET "/billing/usage?start_date=2026-01-01&end_date=2026-02-28"

echo ""
echo "--- Reviews ---"
test_endpoint GET "/reviews/queue"

echo ""
echo "--- API Keys ---"
test_endpoint GET "/organizations/00000000-0000-0000-0000-000000000001/api-keys"
test_endpoint POST "/organizations/00000000-0000-0000-0000-000000000001/api-keys" '{"name":"test-key","expires_in_days":30}'

echo ""
echo "========== Test Complete =========="
