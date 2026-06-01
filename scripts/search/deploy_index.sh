#!/usr/bin/env bash
# deploy_index.sh — Create or update the clinical-kb index in Azure AI Search.
#
# Required env vars:
#   SEARCH_SERVICE_NAME   e.g. clinicalscribe-lab-search
#   SEARCH_ADMIN_KEY      Admin API key (from Key Vault in CI)
#
# Optional:
#   SEARCH_API_VERSION    defaults to 2024-07-01
#
# Usage:
#   ./scripts/search/deploy_index.sh
#
# Idempotent: uses PUT (create-or-update).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INDEX_JSON="${SCRIPT_DIR}/create_index.json"

: "${SEARCH_SERVICE_NAME:?SEARCH_SERVICE_NAME is required}"
: "${SEARCH_ADMIN_KEY:?SEARCH_ADMIN_KEY is required}"

API_VERSION="${SEARCH_API_VERSION:-2024-07-01}"
ENDPOINT="https://${SEARCH_SERVICE_NAME}.search.windows.net"
INDEX_NAME="clinical-kb"

echo "Deploying index '${INDEX_NAME}' to ${ENDPOINT} ..."

curl -sS -X PUT \
  "${ENDPOINT}/indexes/${INDEX_NAME}?api-version=${API_VERSION}&allowIndexDowntime=false" \
  -H "Content-Type: application/json" \
  -H "api-key: ${SEARCH_ADMIN_KEY}" \
  -d "@${INDEX_JSON}" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d.get('name','?'))"

echo "Index deployment complete."
