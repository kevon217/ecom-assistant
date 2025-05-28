#!/bin/bash

# Run All Tests for E-Commerce Assistant
# This script runs pytest for all services and generates a comprehensive report

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Running E-Commerce Assistant Test Suite${NC}"
echo "=============================================="

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo -e "${YELLOW}📂 Project root: ${PROJECT_ROOT}${NC}"

# Create test reports directory
mkdir -p "${PROJECT_ROOT}/test-reports"

# Check if services are running
check_services_running() {
    echo -e "${BLUE}🏥 Checking if services are running...${NC}"

    local services_ok=true

    for port in 8001 8002 8003; do
        if curl -s "http://localhost:${port}/health" > /dev/null; then
            echo -e "${GREEN}✅ Service on port ${port} is running${NC}"
        else
            echo -e "${RED}❌ Service on port ${port} is not running${NC}"
            services_ok=false
        fi
    done

    if [[ "${services_ok}" == false ]]; then
        echo ""
        echo -e "${YELLOW}💡 Start services first: scripts/dev/start_local_services.sh${NC}"
        echo ""
        read -p "🚀 Start services automatically? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo -e "${RED}❌ Exiting. Please start services manually.${NC}"
            exit 1
        else
            echo -e "${BLUE}🚀 Starting services...${NC}"
            "${PROJECT_ROOT}/scripts/dev/start_local_services.sh"
            echo ""
        fi
    fi
}

# Function to run tests for a service
run_service_tests() {
    local service_name=$1
    local service_path="${PROJECT_ROOT}/services/${service_name}"

    echo ""
    echo -e "${PURPLE}🧪 Testing ${service_name} Service${NC}"
    echo "----------------------------------------"

    if [[ ! -d "${service_path}" ]]; then
        echo -e "${RED}❌ Service directory not found: ${service_path}${NC}"
        return 1
    fi

    cd "${service_path}"

    # Check if pytest.ini exists
    if [[ ! -f "pytest.ini" ]]; then
        echo -e "${YELLOW}⚠️  No pytest.ini found for ${service_name}${NC}"
    fi

    # Run pytest with coverage and output formatting
    local report_file="${PROJECT_ROOT}/test-reports/${service_name}_test_report.xml"
    local coverage_file="${PROJECT_ROOT}/test-reports/${service_name}_coverage.xml"

    echo -e "${YELLOW}📝 Running tests with coverage...${NC}"

    if pytest \
        --verbose \
        --tb=short \
        --cov=src \
        --cov-report=xml:"${coverage_file}" \
        --cov-report=term-missing \
        --junit-xml="${report_file}" \
        tests/; then
        echo -e "${GREEN}✅ ${service_name} tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ ${service_name} tests FAILED${NC}"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    echo ""
    echo -e "${PURPLE}🔗 Running Integration Tests${NC}"
    echo "----------------------------------------"

    # Look for integration test directories
    local integration_tests_found=false

    for service in chat order product; do
        local integration_path="${PROJECT_ROOT}/services/${service}/tests/integration"
        if [[ -d "${integration_path}" ]]; then
            echo -e "${YELLOW}📡 Running ${service} integration tests...${NC}"
            cd "${PROJECT_ROOT}/services/${service}"

            if pytest tests/integration/ -v; then
                echo -e "${GREEN}✅ ${service} integration tests PASSED${NC}"
            else
                echo -e "${RED}❌ ${service} integration tests FAILED${NC}"
                return 1
            fi
            integration_tests_found=true
        fi
    done

    if [[ "${integration_tests_found}" == false ]]; then
        echo -e "${YELLOW}⚠️  No integration tests found${NC}"
    fi
}

# Function to generate summary report
generate_summary() {
    local chat_result=$1
    local order_result=$2
    local product_result=$3
    local integration_result=$4

    echo ""
    echo -e "${BLUE}📊 TEST SUMMARY REPORT${NC}"
    echo "=============================================="

    # Service test results
    echo -e "${BLUE}🔧 Unit Tests:${NC}"
    [[ ${chat_result} -eq 0 ]] && echo -e "  • Chat Service:    ${GREEN}PASSED${NC}" || echo -e "  • Chat Service:    ${RED}FAILED${NC}"
    [[ ${order_result} -eq 0 ]] && echo -e "  • Order Service:   ${GREEN}PASSED${NC}" || echo -e "  • Order Service:   ${RED}FAILED${NC}"
    [[ ${product_result} -eq 0 ]] && echo -e "  • Product Service: ${GREEN}PASSED${NC}" || echo -e "  • Product Service: ${RED}FAILED${NC}"

    echo ""
    echo -e "${BLUE}🔗 Integration Tests:${NC}"
    [[ ${integration_result} -eq 0 ]] && echo -e "  • Integration:     ${GREEN}PASSED${NC}" || echo -e "  • Integration:     ${RED}FAILED${NC}"

    echo ""
    echo -e "${BLUE}📁 Test Reports:${NC}"
    echo -e "  • Reports directory: ${PROJECT_ROOT}/test-reports/"
    echo -e "  • Coverage reports:  *_coverage.xml"
    echo -e "  • JUnit reports:     *_test_report.xml"

    # Overall result
    local total_failures=$((${chat_result} + ${order_result} + ${product_result} + ${integration_result}))

    echo ""
    if [[ ${total_failures} -eq 0 ]]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED! Ready for deployment! 🚀${NC}"
        echo -e "${YELLOW}💡 Next: Run Postman collection for end-to-end testing${NC}"
    else
        echo -e "${RED}❌ ${total_failures} test suite(s) failed. Check logs above.${NC}"
        echo -e "${YELLOW}💡 Fix failing tests before deployment${NC}"
    fi

    echo "=============================================="
}

# Main execution
echo ""

# Check services
check_services_running

# Initialize result tracking
chat_result=1
order_result=1
product_result=1
integration_result=1

# Run tests for each service
run_service_tests "chat" && chat_result=0 || chat_result=1
run_service_tests "order" && order_result=0 || order_result=1
run_service_tests "product" && product_result=0 || product_result=1

# Run integration tests
run_integration_tests && integration_result=0 || integration_result=1

# Generate summary
generate_summary ${chat_result} ${order_result} ${product_result} ${integration_result}

# Exit with appropriate code
total_failures=$((${chat_result} + ${order_result} + ${product_result} + ${integration_result}))
exit ${total_failures}
