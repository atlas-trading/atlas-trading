# API Testing Guide

## Running E2E Tests

### Prerequisites
```bash
# Install dependencies
pip install pytest requests

# Make sure API server is running
uvicorn app.main:app --reload --port 8000
```

### Run All Tests
```bash
cd api-server
pytest tests/test_api_e2e.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_api_e2e.py::TestBacktestAPI -v
pytest tests/test_api_e2e.py::TestStrategyAPI -v
pytest tests/test_api_e2e.py::TestPerformance -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Test Categories

### 1. Health Check Tests
- Verifies API server is running
- Response time < 0.1s

### 2. Backtest API Tests
- List backtests with pagination
- Filter by strategy/symbol
- Get backtest detail
- Verify data structure

### 3. Strategy API Tests
- List available strategies
- List configured strategies
- Create/update/delete strategy configs
- Parameter validation

### 4. CORS Tests
- Verify CORS headers present
- Test allowed origins

### 5. Performance Tests
- Response time < 1s for list endpoints
- Health check < 0.1s

## CI/CD Integration

### GitHub Actions Example
```yaml
name: API E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: atlas_trading_test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd api-server
          pip install -r requirements.txt
          pip install pytest requests

      - name: Run migrations
        run: |
          cd api-server
          alembic upgrade head

      - name: Start API server
        run: |
          cd api-server
          uvicorn app.main:app --port 8000 &
          sleep 5

      - name: Run E2E tests
        run: |
          cd api-server
          pytest tests/test_api_e2e.py -v
```

## Adding New Tests

### Template
```python
class TestMyFeature:
    """My feature tests"""

    def test_my_endpoint(self):
        """Test description"""
        response = requests.get(f"{BASE_URL}/my-endpoint", timeout=TIMEOUT)
        assert response.status_code == 200

        data = response.json()
        assert 'expected_field' in data
```

### Best Practices
1. Always set timeout on requests
2. Test both success and error cases
3. Verify response structure, not just status code
4. Use descriptive test names
5. Clean up test data after tests
6. Don't rely on order of test execution

## Debugging Failed Tests

### Check API server logs
```bash
tail -f /tmp/api-server.log
```

### Run single test with verbose output
```bash
pytest tests/test_api_e2e.py::TestBacktestAPI::test_list_backtests -vvs
```

### Use pytest debugger
```bash
pytest tests/test_api_e2e.py --pdb
```

## Continuous Monitoring

Add these tests to your monitoring:
- Run every 5 minutes in production
- Alert on failures
- Track response times

Example monitoring script:
```bash
#!/bin/bash
while true; do
  pytest tests/test_api_e2e.py::TestPerformance -q
  if [ $? -ne 0 ]; then
    echo "Performance test failed!" | mail -s "API Performance Alert" admin@example.com
  fi
  sleep 300
done
```
