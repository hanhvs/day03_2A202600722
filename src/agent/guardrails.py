"""Input guardrails for PriceCheck Agent v2."""
from __future__ import annotations

import re
from typing import List, Set

ALLOWED_TOOLS: Set[str] = {
    "normalize_product",
    "get_reference_price",
    "score_condition",
    "search_comparable_listings",
    "search_product_online",
}

PRICE_HINTS = [
    "giá",
    "bán",
    "mua",
    "triệu",
    "vnd",
    "đồ cũ",
    "cũ",
    "pin",
    "iphone",
    "macbook",
    "laptop",
    "sony",
    "canon",
    "airpods",
    "tình trạng",
    "rao",
    "thanh lý",
    "market",
]

OFF_TOPIC_PATTERNS = [
    r"mã\s*giảm\s*giá",
    r"coupon",
    r"voucher",
    r"ship\s*code",
    r"khuyến\s*mãi\s*shopee",
    r"đặt\s*hàng",
    r"giao\s*hàng\s*miễn\s*phí",
]


def is_price_related(user_input: str) -> bool:
    text = user_input.lower()
    return any(hint in text for hint in PRICE_HINTS)


def is_off_topic(user_input: str) -> bool:
    """Reject obvious non-pricing requests (v2 guardrail)."""
    text = user_input.lower().strip()
    if not text:
        return True
    if any(re.search(p, text) for p in OFF_TOPIC_PATTERNS):
        return True
    return not is_price_related(text)


def off_topic_message() -> str:
    return (
        "Mình là PriceCheck Agent — chỉ hỗ trợ **ước lượng giá bán lại** đồ cũ tại Việt Nam. "
        "Bạn mô tả giúp tên sản phẩm + tình trạng (pin, vỏ, phụ kiện) để mình tra giá nhé."
    )


def validate_tool_name(tool_name: str) -> bool:
    return tool_name in ALLOWED_TOOLS
