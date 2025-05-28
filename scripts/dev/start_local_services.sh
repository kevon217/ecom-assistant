#!/bin/bash

# Start Local E-Commerce Services for Testing
# This script starts all three microservices on ports 8001, 8002, 8003

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting E-Commerce Assistant Local Services${NC}"
echo "=================================================="

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo -e "${YELLOW}📂 Project root: ${PROJECT_ROOT}${NC}"

# Kill any existing processes on the ports first
echo -e "${YELLOW}🧹 Cleaning up existing processes on ports 8001-8003...${NC}"
lsof -ti:8001 | xargs kill -9 2>/dev/null || true
lsof -ti:8002 | xargs kill -9 2>/dev/null || true
lsof -ti:8003 | xargs kill -9 2>/dev/null || true
sleep 2

# Create logs directory
mkdir -p "${PROJECT_ROOT}/logs/services"

# Function to start a service
start_service() {
    local service_name=$1
    local port=$2
    local service_path=$3
    local app_module=$4

    echo -e "${YELLOW}📡 Starting ${service_name} service on port ${port}...${NC}"

    cd "${PROJECT_ROOT}/${service_path}"

    # Check if we're in a virtual environment or if uvicorn is available
    if ! command -v uvicorn &> /dev/null; then
        echo -e "${RED}❌ uvicorn not found. Please install it or activate your virtual environment${NC}"
        exit 1
    fi

    # Start the service in background
    uvicorn ${app_module}:app \
        --host 0.0.0.0 \
        --port ${port} \
        --reload \
        --log-level info \
        > "${PROJECT_ROOT}/logs/services/${service_name}.log" 2>&1 &

    local pid=$!
    echo "${pid}" > "${PROJECT_ROOT}/logs/services/${service_name}.pid"

    echo -e "${GREEN}✅ ${service_name} started (PID: ${pid})${NC}"

    # Wait a moment for the service to start
    sleep 2

    # Check if the service is still running
    if ! kill -0 ${pid} 2>/dev/null; then
        echo -e "${RED}❌ ${service_name} failed to start. Check logs:${NC}"
        echo -e "${RED}   tail -f ${PROJECT_ROOT}/logs/services/${service_name}.log${NC}"
        exit 1
    fi
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local port=$2

    echo -e "${YELLOW}🏥 Checking ${service_name} health...${NC}"

    for i in {1..10}; do
        if curl -s "http://localhost:${port}/health" > /dev/null; then
            echo -e "${GREEN}✅ ${service_name} is healthy${NC}"
            return 0
        fi
        echo -e "${YELLOW}   Waiting for ${service_name} (attempt ${i}/10)...${NC}"
        sleep 2
    done

    echo -e "${RED}❌ ${service_name} health check failed${NC}"
    return 1
}

echo ""
echo -e "${BLUE}🎯 Starting Services...${NC}"

# Start Chat Service (8001)
start_service "chat" "8001" "services/chat" "src.chat.app"

# Start Order Service (8002)
start_service "order" "8002" "services/order" "src.order.app"

# Start Product Service (8003)
start_service "product" "8003" "services/product" "src.product.app"

echo ""
echo -e "${BLUE}🏥 Health Checks...${NC}"

# Wait a bit for all services to fully start
sleep 5

# Check health of all services
check_service_health "chat" "8001"
check_service_health "order" "8002"
check_service_health "product" "8003"

echo ""
echo -e "${GREEN}🎉 ALL SERVICES STARTED SUCCESSFULLY!${NC}"
echo "=================================================="
echo -e "${BLUE}📊 Service Status:${NC}"
echo -e "  • Chat Service:    http://localhost:8001/health"
echo -e "  • Order Service:   http://localhost:8002/health"
echo -e "  • Product Service: http://localhost:8003/health"
echo ""
echo -e "${BLUE}📝 Log Files:${NC}"
echo -e "  • Chat:    ${PROJECT_ROOT}/logs/services/chat.log"
echo -e "  • Order:   ${PROJECT_ROOT}/logs/services/order.log"
echo -e "  • Product: ${PROJECT_ROOT}/logs/services/product.log"
echo ""
echo -e "${YELLOW}💡 To stop services: scripts/dev/stop_local_services.sh${NC}"
echo -e "${YELLOW}💡 To run tests: scripts/dev/run_all_tests.sh${NC}"
echo ""
