"""Tool registry for PriceCheck Agent v1."""

from src.tools.condition_scoring import score_condition
from src.tools.listings_mock import search_comparable_listings
from src.tools.product_catalog import normalize_product, get_reference_price

# Tool metadata for LLM (all 4; partner implements score_condition + search_comparable_listings)
TOOL_SPECS = [
    {
        "name": "normalize_product",
        "description": (
            "Chuẩn hóa tên sản phẩm từ câu user. Input: query (str), vd normalize_product(\"iPhone 13 128GB\"). "
            "Trả về canonical_name, category, storage_gb, confidence."
        ),
    },
    {
        "name": "get_reference_price",
        "description": (
            "Lấy giá tham chiếu mới (VND) từ catalog. Input: canonical_name (str), tùy chọn storage_gb (int). "
            "Vd get_reference_price(\"iPhone 13 128GB\") hoặc get_reference_price(\"iPhone 13 128GB\", storage_gb=128)."
        ),
    },
    {
        "name": "score_condition",
        "description": (
            "[@0infinitive0] Đánh giá tình trạng từ mô tả text. Input: condition_text (str). "
            "Trả về tier (like_new/good/fair/poor), multiplier, risk_flags."
        ),
    },
    {
        "name": "search_comparable_listings",
        "description": (
            "[@0infinitive0] Tìm tin đăng tương đương (mock). Input: canonical_name (str), tier (str). "
            "Trả về avg_vnd, min_vnd, max_vnd, sample_count."
        ),
    },
]

__all__ = [
    "TOOL_SPECS",
    "normalize_product",
    "get_reference_price",
    "score_condition",
    "search_comparable_listings",
]
