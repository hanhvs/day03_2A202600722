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


def _detect_tier(condition_text: str) -> str:
    text = _normalize_text(condition_text)
    if any(word in text for word in POOR_KEYWORDS):
        return "poor"
    if any(word in text for word in FAIR_KEYWORDS):
        return "fair"
    if any(word in text for word in LIKE_NEW_KEYWORDS):
        return "like_new"
    if any(word in text for word in GOOD_KEYWORDS):
        return "good"
    return "good"


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
    """Map a free-form condition description to a tier, multiplier, and risk flags."""
    tier = _detect_tier(condition_text)
    tier = _adjust_by_battery(tier, condition_text)
    tier = _downgrade_if_no_box(tier, condition_text)
    multiplier = TIER_MULTIPLIERS.get(tier, 0.75)
    risk_flags = _build_risk_flags(condition_text)

    return {
        "tier": tier,
        "multiplier": multiplier,
        "risk_flags": risk_flags,
        "notes": [
            "Đã đánh giá tình trạng dựa trên mô tả khách hàng.",
            f"Ước tính tier {tier} với hệ số {multiplier}.",
        ],
    }
