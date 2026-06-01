"""Mock condition scoring for PriceCheck Agent v1 (@0infinitive0)."""
from __future__ import annotations

import re
from typing import Dict, Any, List

TIER_MULTIPLIERS = {
    "like_new": 0.92,
    "good": 0.78,
    "fair": 0.62,
    "poor": 0.45,
}

LIKE_NEW_KEYWORDS = [
    "like mới",
    "như mới",
    "còn mới",
    "mới 100%",
    "mới",
    "full box",
    "fullbox",
    "đủ hộp",
    "box",
]

GOOD_KEYWORDS = [
    "vỏ đẹp",
    "màn ok",
    "hoạt động tốt",
    "nguyên bản",
    "pin",
    "đủ hộp",
    "trầy nhẹ",
    "vỏ còn tốt",
]

FAIR_KEYWORDS = [
    "trầy",
    "cấn",
    "lỗi nhỏ",
    "ốp",
    "mất hộp",
    "không hộp",
    "cảm biến",
    "shutter",
    "đốm",
    "vết",
    "xoáy",
]

POOR_KEYWORDS = [
    "hư",
    "lỗi",
    "vỡ",
    "màn hỏng",
    "pin yếu",
    "sửa",
    "chậm",
    "không bật",
    "dead",
    "bể",
]

BATTERY_RE = re.compile(r"pin\s*(\d{2,3})\s*%")


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_dimension_pin(text: str) -> float:
    match = BATTERY_RE.search(text)
    if match:
        try:
            return min(100.0, max(0.0, float(match.group(1))))
        except ValueError:
            pass
    if "pin" in text:
        return 75.0
    return 82.0


def _score_dimension_screen(text: str) -> float:
    if any(w in text for w in ["màn hỏng", "màn lỗi", "dead pixel", "đốm", "sọc màn"]):
        return 45.0
    if any(w in text for w in ["màn ok", "màn đẹp", "màn tốt"]):
        return 90.0
    if "màn" in text:
        return 75.0
    return 85.0


def _score_dimension_body(text: str) -> float:
    if any(w in text for w in POOR_KEYWORDS):
        return 40.0
    if any(w in text for w in ["trầy", "cấn", "vết", "xoáy"]):
        return 62.0
    if any(w in text for w in ["vỏ đẹp", "vỏ còn tốt", "đẹp"]):
        return 92.0
    return 80.0


def _score_dimension_box(text: str) -> float:
    if "không hộp" in text or "mất hộp" in text or "no box" in text:
        return 55.0
    if any(w in text for w in ["đủ hộp", "full box", "fullbox", "box"]):
        return 95.0
    return 78.0


def _tier_from_average(avg: float) -> str:
    if avg >= 88:
        return "like_new"
    if avg >= 75:
        return "good"
    if avg >= 58:
        return "fair"
    return "poor"


def _detect_tier_v2(condition_text: str) -> tuple[str, Dict[str, float]]:
    text = _normalize_text(condition_text)
    dimensions = {
        "pin": _score_dimension_pin(text),
        "screen": _score_dimension_screen(text),
        "body": _score_dimension_body(text),
        "box": _score_dimension_box(text),
    }
    avg = sum(dimensions.values()) / len(dimensions)
    return _tier_from_average(avg), dimensions


def _detect_tier(condition_text: str) -> str:
    tier, _ = _detect_tier_v2(condition_text)
    return tier


def _adjust_by_battery(tier: str, condition_text: str) -> str:
    match = BATTERY_RE.search(condition_text.lower())
    if not match:
        return tier
    try:
        percent = int(match.group(1))
    except ValueError:
        return tier

    if percent >= 95:
        return "like_new" if tier != "poor" else "poor"
    if 85 <= percent < 95:
        return "good" if tier in {"good", "like_new"} else tier
    if 75 <= percent < 85:
        return "fair" if tier != "poor" else "poor"
    return "poor"


def _downgrade_if_no_box(tier: str, condition_text: str) -> str:
    text = _normalize_text(condition_text)
    if "không hộp" in text or "mất hộp" in text or "no box" in text:
        if tier == "like_new":
            return "good"
        if tier == "good":
            return "fair"
    return tier


def _build_risk_flags(condition_text: str) -> List[str]:
    text = _normalize_text(condition_text)
    flags: List[str] = []
    if "không hộp" in text or "mất hộp" in text:
        flags.append("không hộp")
    if "trầy" in text or "cấn" in text or "vỏ" in text:
        flags.append("hư hỏng bề mặt")
    if "pin" in text:
        flags.append("pin hao mòn")
    if "cảm biến" in text or "đốm" in text or "shutter" in text:
        flags.append("rủi ro phần cứng / cảm biến")
    if "lỗi" in text or "hư" in text or "vỡ" in text or "màn hỏng" in text:
        flags.append("có lỗi kỹ thuật")
    return list(dict.fromkeys(flags))


def score_condition(condition_text: str) -> Dict[str, Any]:
    """Map condition text → tier via v2 weighted dimensions (pin, screen, body, box)."""
    tier, dimensions = _detect_tier_v2(condition_text)
    tier = _downgrade_if_no_box(tier, condition_text)
    multiplier = TIER_MULTIPLIERS.get(tier, 0.75)
    risk_flags = _build_risk_flags(condition_text)
    avg_score = round(sum(dimensions.values()) / len(dimensions), 1)

    return {
        "tier": tier,
        "multiplier": multiplier,
        "risk_flags": risk_flags,
        "scoring_version": "v2",
        "dimension_scores": dimensions,
        "average_score": avg_score,
        "notes": [
            "v2: chấm theo 4 chiều (pin, màn, vỏ, hộp) rồi gộp tier.",
            f"Tier {tier}, điểm TB {avg_score}/100, hệ số {multiplier}.",
        ],
    }
