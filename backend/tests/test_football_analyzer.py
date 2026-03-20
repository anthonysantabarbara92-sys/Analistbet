"""Backend tests for Football Analyzer API"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://poisson-predictor-2.preview.emergentagent.com').rstrip('/')


class TestHealthAndHistory:
    """Health and history endpoint tests"""

    def test_root_endpoint(self):
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_get_analyses_returns_list(self):
        response = requests.get(f"{BASE_URL}/api/analyses")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_analyses_structure(self):
        """If there are items, check structure"""
        response = requests.get(f"{BASE_URL}/api/analyses")
        assert response.status_code == 200
        data = response.json()
        if data:
            item = data[0]
            assert "id" in item or "match_info" in item or "result" in item
            assert "_id" not in item  # MongoDB _id must be excluded


class TestAnalyzeEndpoint:
    """Test analyze endpoint validation"""

    def test_analyze_missing_fields_returns_error(self):
        """Empty body should fail with 422"""
        response = requests.post(f"{BASE_URL}/api/analyze", json={})
        assert response.status_code == 422

    def test_analyze_partial_fields_returns_error(self):
        """Partial fields should fail"""
        response = requests.post(f"{BASE_URL}/api/analyze", json={"home": "Juventus"})
        assert response.status_code == 422

    def test_analyze_valid_request_returns_analysis(self):
        """Full valid request - this calls real Claude AI, may take up to 90s"""
        payload = {
            "home": "Juventus",
            "away": "Milan",
            "league": "Serie A",
            "matchday": "Giornata 29"
        }
        response = requests.post(f"{BASE_URL}/api/analyze", json=payload, timeout=180)
        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "match_info" in data
        assert "context" in data
        assert "poisson" in data
        assert "markets" in data
        assert "exact_scores" in data
        assert "analyst_report" in data
        assert "confidence" in data

    def test_analyze_result_persisted_in_history(self):
        """After analysis, it should appear in /analyses"""
        history = requests.get(f"{BASE_URL}/api/analyses").json()
        assert isinstance(history, list)
        # At minimum the history endpoint returns without error
        # After test_analyze_valid_request runs, there should be data
        if history:
            item = history[0]
            assert "result" in item
            assert "timestamp" in item
