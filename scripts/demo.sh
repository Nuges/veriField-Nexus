#!/bin/bash
# =============================================================================
# VeriField Nexus — End-to-End Verification Pipeline Demo
# =============================================================================

# Colors for console formatting
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== VeriField Nexus Pipeline Demo ===${NC}"
echo -e "Sending sample RWA verification payload to local FastAPI Verification Engine..."

# Verify if backend is listening on dev port 8000
if ! lsof -i:8000 -t >/dev/null; then
    echo -e "${RED}Error: Backend server is not running on port 8000.${NC}"
    echo -e "Please start the server first by running: ${BLUE}npm run backend:dev${NC}"
    exit 1
fi

echo -e "${GREEN}API detected on port 8000. Ingesting environmental proof...${NC}"
echo -e "${BLUE}Payload:${NC}"
cat examples/sample-verification.json

echo -e "\n${BLUE}Response from /verify:${NC}"
RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d @examples/sample-verification.json \
  http://localhost:8000/api/v1/verify)

# Output response formatted using Python's JSON tool
echo "$RESPONSE" | python3 -m json.tool

echo -e "\n${GREEN}Demo run completed successfully!${NC}"
