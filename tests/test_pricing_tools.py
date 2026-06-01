import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.condition_scoring import score_condition
from src.tools.listings_mock import search_comparable_listings


def test_score_condition_good():
    response = score_condition("pin 88%, màn ok, vỏ đẹp, đủ hộp")
    assert response["tier"] == "good"
    assert 0.7 < response["multiplier"] < 0.85
    assert "pin hao mòn" in response["risk_flags"]


def test_score_condition_fair():
    response = score_condition("Sony A7III, shutter 15k, cảm biến có 1 đốm nhỏ, kèm 1 lens 50mm")
    assert response["tier"] == "fair"
    assert response["multiplier"] == 0.62
    assert any("cảm biến" in flag for flag in response["risk_flags"])


def test_search_comparable_listings():
    response = search_comparable_listings("iPhone 13 128GB", "good")
    assert response["tier"] == "good"
    assert response["avg_vnd"] >= response["min_vnd"]
    assert response["max_vnd"] >= response["avg_vnd"]
    assert response["sample_count"] > 0
