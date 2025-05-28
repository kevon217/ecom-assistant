# Clear cache first
rm -rf .pytest_cache __pycache__
find . -name "*.pyc" -delete

# Run all tests
pytest -v

# Run unit tests only (fast)
pytest tests/unit -v

# Run integration tests only (slower)
pytest tests/integration -v

# Run specific test file
pytest tests/unit/test_app_endpoints.py -v

# Run with coverage
pytest --cov=chat --cov-report=html tests/
