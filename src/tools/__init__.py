"""Tool registry for PriceCheck Agent v1."""

from src.tools.condition_scoring import score_condition
from src.tools.listings_mock import search_comparable_listings
from src.tools.openai_web_search import is_web_search_enabled, search_product_online
from src.tools.product_catalog import get_reference_price, normalize_product

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
            "Tìm tin đăng tương đương (mock catalog). Input: canonical_name (str), tier (str). "
            "Trả về avg_vnd, min_vnd, max_vnd, sample_count. Chỉ dùng khi đã matched catalog."
        ),
    },
    {
        "name": "search_product_online",
        "description": (
            "BẮT BUỘC khi normalize_product matched=false hoặc get_reference_price found=false. "
            "Tra giá thị trường VN qua OpenAI Web Search. "
            'Input: product_query (str), tùy chọn condition_text (str). '
            'Vd search_product_online("Samsung Z Flip 5 256GB", "pin 90%, đẹp")'
        ),
    },
]

__all__ = [
    "TOOL_SPECS",
    "normalize_product",
    "get_reference_price",
    "score_condition",
    "search_comparable_listings",
    "search_product_online",
    "is_web_search_enabled",
]
