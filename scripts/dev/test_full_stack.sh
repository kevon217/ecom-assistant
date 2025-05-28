#!/bin/bash

# Full Stack Test Runner
# This script starts services, runs all tests, and optionally stops services

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 E-Commerce Assistant Full Stack Testing${NC}"
echo "=============================================="

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Parse command line arguments
KEEP_SERVICES=false
SKIP_START=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-services)
            KEEP_SERVICES=true
            shift
            ;;
        --skip-start)
            SKIP_START=true
            shift
            ;;
        --help)
            echo -e "${YELLOW}Usage: $0 [OPTIONS]${NC}"
            echo ""
            echo -e "${YELLOW}Options:${NC}"
            echo -e "  --keep-services    Don't stop services after testing"
            echo -e "  --skip-start       Don't start services (assume already running)"
            echo -e "  --help             Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Function to cleanup on exit
cleanup() {
    local exit_code=$?
    echo ""
    if [[ ${exit_code} -ne 0 ]]; then
        echo -e "${RED}❌ Full stack testing failed with exit code ${exit_code}${NC}"
    fi

    if [[ "${KEEP_SERVICES}" == false ]]; then
        echo -e "${YELLOW}🛑 Stopping services...${NC}"
        "${PROJECT_ROOT}/scripts/dev/stop_local_services.sh"
    else
        echo -e "${YELLOW}💡 Services left running (--keep-services flag used)${NC}"
    fi

    exit ${exit_code}
}

# Set up cleanup trap
trap cleanup EXIT

echo ""
echo -e "${BLUE}📋 Test Plan:${NC}"
echo -e "  1. ${SKIP_START:+${YELLOW}Skip starting${NC}|${GREEN}Start${NC}} local services (ports 8001-8003)"
echo -e "  2. ${GREEN}Run${NC} pytest for all services"
echo -e "  3. ${GREEN}Run${NC} integration tests"
echo -e "  4. ${KEEP_SERVICES:+${YELLOW}Keep${NC}|${GREEN}Stop${NC}} services"
echo ""

# Step 1: Start services (unless skipped)
if [[ "${SKIP_START}" == false ]]; then
    echo -e "${BLUE}🚀 Step 1: Starting Services${NC}"
    "${PROJECT_ROOT}/scripts/dev/start_local_services.sh"
    echo ""
else
    echo -e "${YELLOW}⏭️  Step 1: Skipped starting services${NC}"
    echo ""
fi

# Step 2: Run all tests
echo -e "${BLUE}🧪 Step 2: Running All Tests${NC}"
"${PROJECT_ROOT}/scripts/dev/run_all_tests.sh"

echo ""
echo -e "${GREEN}🎉 FULL STACK TESTING COMPLETED SUCCESSFULLY!${NC}"
echo "=============================================="
echo -e "${BLUE}📊 What was tested:${NC}"
echo -e "  • ✅ All service unit tests"
echo -e "  • ✅ All integration tests"
echo -e "  • ✅ Service health checks"
echo -e "  • ✅ Cross-service communication"
echo ""
echo -e "${YELLOW}💡 Next Steps:${NC}"
echo -e "  • Run Postman collection for end-to-end API testing"
echo -e "  • Deploy to Render if all tests pass"
echo ""
