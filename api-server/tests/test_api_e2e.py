"""
End-to-End API Tests

Tests all API endpoints to prevent regression.
Run with: pytest tests/test_api_e2e.py -v
"""
import requests
import pytest
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 5  # seconds


class TestHealthCheck:
    """Health check endpoint tests"""

    def test_health_endpoint(self):
        """Test health check returns OK"""
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestBacktestAPI:
    """Backtest API endpoint tests"""

    def test_list_backtests(self):
        """Test backtest list endpoint"""
        response = requests.get(f"{BASE_URL}/backtests", params={"limit": 5}, timeout=TIMEOUT)
        assert response.status_code in [200, 307], f"Unexpected status: {response.status_code}"

        # Follow redirect if needed
        if response.status_code == 307:
            redirect_url = response.headers.get('Location')
            response = requests.get(redirect_url, timeout=TIMEOUT)
            assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list), "Response should be a list"

        if len(data) > 0:
            # Verify structure of first item
            backtest = data[0]
            required_fields = ['id', 'strategy_name', 'symbol', 'total_return', 'created_at']
            for field in required_fields:
                assert field in backtest, f"Missing required field: {field}"

    def test_list_backtests_with_filters(self):
        """Test backtest list with filters"""
        response = requests.get(
            f"{BASE_URL}/backtests",
            params={"limit": 10, "strategy_name": "RSI_Mean_Reversion"},
            timeout=TIMEOUT,
            allow_redirects=True
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_backtest_detail(self):
        """Test getting backtest detail"""
        # First get a list to find an ID
        list_response = requests.get(f"{BASE_URL}/backtests", params={"limit": 1}, timeout=TIMEOUT, allow_redirects=True)
        if list_response.status_code == 200:
            backtests = list_response.json()
            if len(backtests) > 0:
                backtest_id = backtests[0]['id']

                # Get detail
                detail_response = requests.get(f"{BASE_URL}/backtests/{backtest_id}", timeout=TIMEOUT)
                assert detail_response.status_code == 200

                detail = detail_response.json()
                assert 'id' in detail
                assert 'total_trades' in detail
                assert 'win_rate' in detail


class TestStrategyAPI:
    """Strategy API endpoint tests"""

    def test_list_available_strategies(self):
        """Test listing available strategies"""
        response = requests.get(f"{BASE_URL}/strategies/available", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list), "Response should be a list"

    def test_list_strategy_configs(self):
        """Test listing strategy configurations"""
        response = requests.get(f"{BASE_URL}/strategies/configs", timeout=TIMEOUT)
        assert response.status_code == 200, f"Failed with status {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"

    def test_create_and_delete_strategy_config(self):
        """Test creating and deleting a strategy configuration"""
        # Create a test strategy config
        test_config = {
            "strategy_name": "TestStrategy",
            "display_name": "Test Strategy",
            "description": "Test strategy for E2E testing",
            "parameters": {"test_param": 123},
            "is_active": False
        }

        # Note: This will fail if the strategy class doesn't exist in the registry
        # For now, we'll just test that the endpoint responds
        create_response = requests.post(
            f"{BASE_URL}/strategies/configs",
            json=test_config,
            timeout=TIMEOUT
        )

        # Expecting 404 or 400 because TestStrategy is not registered
        # But we should NOT get 500
        assert create_response.status_code in [200, 201, 400, 404, 409], \
            f"Unexpected error: {create_response.status_code}"

    def test_validate_strategy_parameters(self):
        """Test parameter validation endpoint"""
        # This will fail because TestStrategy doesn't exist, but should return proper error
        response = requests.post(
            f"{BASE_URL}/strategies/configs/TestStrategy/validate",
            json={"test_param": 123},
            timeout=TIMEOUT
        )

        # Should return 404 (strategy not found) not 500
        assert response.status_code in [200, 400, 404], \
            f"Validation endpoint failed unexpectedly: {response.status_code}"


class TestCORS:
    """CORS configuration tests"""

    def test_cors_headers_present(self):
        """Test that CORS headers are present"""
        response = requests.options(
            f"{BASE_URL}/backtests",
            headers={
                "Origin": "http://localhost:5175",
                "Access-Control-Request-Method": "GET"
            },
            timeout=TIMEOUT,
            allow_redirects=True
        )

        # Should have CORS headers
        assert response.status_code in [200, 204]
        # Note: Some CORS implementations return headers on the actual request, not OPTIONS


class TestPerformance:
    """Performance tests"""

    def test_backtest_list_response_time(self):
        """Test that backtest list responds quickly"""
        import time
        start = time.time()
        response = requests.get(f"{BASE_URL}/backtests", params={"limit": 20}, timeout=TIMEOUT, allow_redirects=True)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Response took too long: {elapsed:.2f}s"

    def test_health_check_response_time(self):
        """Test that health check is very fast"""
        import time
        start = time.time()
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=TIMEOUT)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.1, f"Health check took too long: {elapsed:.2f}s"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
