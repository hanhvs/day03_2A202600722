import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.action_parser import parse_action, sanitize_llm_output
from src.agent.guardrails import is_off_topic, is_price_related
from src.tools.condition_scoring import score_condition
from src.telemetry.metrics import tracker


def test_sanitize_action_in_fence():
    raw = '```json\nAction: normalize_product("iPhone 13")\n```'
    assert parse_action(sanitize_llm_output(raw)) is not None


def test_off_topic():
    assert is_off_topic("cho tôi mã giảm giá shopee") is True
    assert is_off_topic("iphone 13 pin 88% giá bao nhiêu") is False


def test_condition_v2_dimensions():
    r = score_condition("pin 88%, màn ok, vỏ đẹp, đủ hộp")
    assert r["scoring_version"] == "v2"
    assert "dimension_scores" in r
    assert r["tier"] in ("like_new", "good")


def test_metrics_cost():
    m = tracker.track_request("openai", "gpt-4o", {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200}, 500)
    assert m["cost_estimate"] > 0
    assert m["token_ratio"] > 0
