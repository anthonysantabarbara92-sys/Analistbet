"""Backend tests for Football Analyzer v2 - Web Search + Normalized Markets"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://poisson-predictor-2.preview.emergentagent.com').rstrip('/')


class TestRootEndpoint:
    """Test root endpoint message indicates web search enabled"""

    def test_root_message_contains_web_search(self):
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        msg = data["message"].lower()
        assert "web search" in msg or "web" in msg, f"Expected web search in message, got: {data['message']}"


class TestWebSearchAnalysis:
    """Test that analyze endpoint uses web search and returns new fields"""

    @pytest.fixture(scope="class")
    def analysis_result(self):
        """Run one analysis for Napoli vs Inter - shared across tests in class"""
        payload = {
            "home": "Napoli",
            "away": "Inter",
            "league": "Serie A",
            "matchday": "Giornata 30"
        }
        response = requests.post(f"{BASE_URL}/api/analyze", json=payload, timeout=180)
        assert response.status_code == 200, f"Analyze failed: {response.text[:300]}"
        return response.json()

    def test_web_search_used_field_present(self, analysis_result):
        assert "web_search_used" in analysis_result, "Missing web_search_used field"

    def test_web_search_used_is_true(self, analysis_result):
        assert analysis_result["web_search_used"] is True, f"web_search_used={analysis_result.get('web_search_used')}"

    def test_web_queries_found_field_present(self, analysis_result):
        assert "web_queries_found" in analysis_result, "Missing web_queries_found field"

    def test_web_queries_found_greater_than_zero(self, analysis_result):
        found = analysis_result.get("web_queries_found", 0)
        assert found > 0, f"web_queries_found={found}, expected > 0"

    def test_1x2_probabilities_sum_to_one(self, analysis_result):
        """Verify normalization - 1X2 should sum to ~1.0"""
        result = analysis_result.get("markets", {}).get("result", {})
        s = result.get("home_win", 0) + result.get("draw", 0) + result.get("away_win", 0)
        assert abs(s - 1.0) < 0.01, f"1X2 sum={s:.4f}, expected ~1.0"

    def test_over_under_pairs_sum_to_one(self, analysis_result):
        """Over+Under for each line should sum to ~1.0"""
        ou = analysis_result.get("markets", {}).get("over_under", {})
        for t in ["1_5", "2_5", "3_5"]:
            o = ou.get(f"over_{t}", 0)
            u = ou.get(f"under_{t}", 0)
            s = o + u
            assert abs(s - 1.0) < 0.01, f"Over/Under {t}: sum={s:.4f}"

    def test_corners_pairs_sum_to_one(self, analysis_result):
        corners = analysis_result.get("markets", {}).get("corners", {})
        for t in ["7_5", "8_5", "9_5", "10_5"]:
            o = corners.get(f"over_{t}", 0)
            u = corners.get(f"under_{t}", 0)
            s = o + u
            assert abs(s - 1.0) < 0.01, f"Corners {t}: sum={s:.4f}"

    def test_exact_scores_present(self, analysis_result):
        scores = analysis_result.get("exact_scores", [])
        assert len(scores) >= 6, f"Expected ≥6 exact scores, got {len(scores)}"

    def test_exact_scores_have_odds_compatible_prob(self, analysis_result):
        """All exact score probs should be > 0 so odds can be computed"""
        for s in analysis_result.get("exact_scores", [])[:8]:
            assert s.get("prob", 0) > 0, f"Score {s.get('score')} has prob=0"

    def test_analysis_saved_to_history(self, analysis_result):
        """After analysis, history should have an item"""
        response = requests.get(f"{BASE_URL}/api/analyses")
        assert response.status_code == 200
        history = response.json()
        assert len(history) > 0
        item = history[0]
        assert "result" in item
        assert "timestamp" in item
        assert "_id" not in item
