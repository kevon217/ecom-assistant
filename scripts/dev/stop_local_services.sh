#!/bin/bash

# Stop Local E-Commerce Services
# This script stops all running microservices and cleans up

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping E-Commerce Assistant Local Services${NC}"
echo "=================================================="

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Function to stop a service by PID file
stop_service_by_pid() {
    local service_name=$1
    local pid_file="${PROJECT_ROOT}/logs/services/${service_name}.pid"

    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}")
        if kill -0 ${pid} 2>/dev/null; then
            echo -e "${YELLOW}🛑 Stopping ${service_name} (PID: ${pid})...${NC}"
            kill -TERM ${pid} 2>/dev/null || true
            sleep 2

            # Force kill if still running
            if kill -0 ${pid} 2>/dev/null; then
                echo -e "${YELLOW}   Force killing ${service_name}...${NC}"
                kill -9 ${pid} 2>/dev/null || true
            fi

            echo -e "${GREEN}✅ ${service_name} stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  ${service_name} PID ${pid} not running${NC}"
        fi
        rm -f "${pid_file}"
    else
        echo -e "${YELLOW}⚠️  No PID file for ${service_name}${NC}"
    fi
}

# Function to stop processes by port
stop_service_by_port() {
    local service_name=$1
    local port=$2

    echo -e "${YELLOW}🔍 Checking for processes on port ${port}...${NC}"

    local pids=$(lsof -ti:${port} 2>/dev/null || true)
    if [[ -n "${pids}" ]]; then
        echo -e "${YELLOW}🛑 Killing processes on port ${port}: ${pids}${NC}"
        echo "${pids}" | xargs kill -TERM 2>/dev/null || true
        sleep 2

        # Force kill if still running
        local remaining_pids=$(lsof -ti:${port} 2>/dev/null || true)
        if [[ -n "${remaining_pids}" ]]; then
            echo -e "${YELLOW}   Force killing remaining processes...${NC}"
            echo "${remaining_pids}" | xargs kill -9 2>/dev/null || true
        fi

        echo -e "${GREEN}✅ Port ${port} cleared${NC}"
    else
        echo -e "${GREEN}✅ Port ${port} already free${NC}"
    fi
}

echo ""
echo -e "${BLUE}🎯 Stopping Services by PID...${NC}"

# Stop services by PID files first (more graceful)
stop_service_by_pid "chat"
stop_service_by_pid "order"
stop_service_by_pid "product"

echo ""
echo -e "${BLUE}🔍 Cleaning up any remaining processes...${NC}"

# Clean up any remaining processes on the ports
stop_service_by_port "chat" "8001"
stop_service_by_port "order" "8002"
stop_service_by_port "product" "8003"

# Clean up PID and log files if requested
read -p "🗑️  Clean up log files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🧹 Cleaning up log files...${NC}"
    rm -f "${PROJECT_ROOT}/logs/services/"*.log
    rm -f "${PROJECT_ROOT}/logs/services/"*.pid
    echo -e "${GREEN}✅ Log files cleaned${NC}"
fi

echo ""
echo -e "${GREEN}🎉 ALL SERVICES STOPPED SUCCESSFULLY!${NC}"
echo "=================================================="
echo -e "${BLUE}📊 Port Status:${NC}"

# Verify ports are free
for port in 8001 8002 8003; do
    if lsof -ti:${port} >/dev/null 2>&1; then
        echo -e "  • Port ${port}: ${RED}OCCUPIED${NC}"
    else
        echo -e "  • Port ${port}: ${GREEN}FREE${NC}"
    fi
done

echo ""
echo -e "${YELLOW}💡 To start services again: scripts/dev/start_local_services.sh${NC}"
echo ""
