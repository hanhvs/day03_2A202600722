"""
OpenAI Responses API + web_search when product is not in local catalog.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from src.telemetry.logger import logger

_CATALOG_MISS_HINT = (
    "Sản phẩm không có trong catalog nội bộ. "
    "Gọi search_product_online(product_query, condition_text) để tra giá thị trường qua OpenAI Web Search."
)


def is_web_search_enabled() -> bool:
    return os.getenv("ENABLE_OPENAI_WEB_SEARCH", "true").lower() in ("1", "true", "yes")


def catalog_miss_hint() -> str:
    return _CATALOG_MISS_HINT


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _responses_web_search(client: Any, model: str, prompt: str) -> str:
    """Call OpenAI Responses API with web_search tool."""
    if not hasattr(client, "responses"):
        raise RuntimeError(
            "OpenAI SDK quá cũ — cần openai>=1.50 hỗ trợ client.responses. Chạy: pip install -U openai"
        )

    tool_variants = [{"type": "web_search"}, {"type": "web_search_preview"}]
    last_error: Optional[Exception] = None

    for tool in tool_variants:
        try:
            response = client.responses.create(
                model=model,
                input=prompt,
                tools=[tool],
            )
            text = getattr(response, "output_text", None)
            if text:
                return text
            return str(response)
        except Exception as e:
            last_error = e
            logger.log_event("WEB_SEARCH_RETRY", {"tool": tool, "error": str(e)})

    raise last_error or RuntimeError("web_search failed")


def search_product_online(
    product_query: str,
    condition_text: str = "",
) -> Dict[str, Any]:
    """
  Tra cứu giá bán lại tại Việt Nam qua OpenAI Web Search (Responses API).
  Dùng khi normalize_product trả matched=false hoặc get_reference_price found=false.
    """
    product_query = (product_query or "").strip()
    condition_text = (condition_text or "").strip()

    if not product_query:
        return {"found": False, "error": "empty_product_query"}

    if not is_web_search_enabled():
        return {
            "found": False,
            "error": "web_search_disabled",
            "message": "Bật ENABLE_OPENAI_WEB_SEARCH=true trong .env",
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"found": False, "error": "OPENAI_API_KEY missing"}

    from openai import OpenAI

    model = os.getenv("OPENAI_WEB_SEARCH_MODEL") or os.getenv("DEFAULT_MODEL", "gpt-4o")
    client = OpenAI(api_key=api_key)

    prompt = f"""Bạn là chuyên gia giá đồ cũ tại Việt Nam. Dùng web search để tìm giá rao bán / thị trường gần đây.

Sản phẩm: {product_query}
Tình trạng (nếu có): {condition_text or "không rõ"}

Trả lời CHỈ bằng một JSON object (không markdown), các trường:
- product_name (string)
- estimated_min_vnd (integer, VND)
- estimated_max_vnd (integer, VND)
- suggested_vnd (integer, VND)
- sources_summary (string, tiếng Việt, ngắn)
- confidence ("low" | "medium" | "high")
- notes (string, tùy chọn)

Nếu không đủ dữ liệu, vẫn trả JSON với confidence "low" và ước lượng thận trọng."""

    logger.log_event(
        "WEB_SEARCH_START",
        {"product_query": product_query, "model": model, "has_condition": bool(condition_text)},
    )

    try:
        raw = _responses_web_search(client, model, prompt)
        parsed = _extract_json_object(raw)

        if not parsed:
            return {
                "found": True,
                "source": "openai_web_search",
                "raw_answer": raw,
                "product_query": product_query,
                "message": "Không parse được JSON; dùng raw_answer.",
            }

        result = {
            "found": True,
            "source": "openai_web_search",
            "product_query": product_query,
            "condition_text": condition_text or None,
            "product_name": parsed.get("product_name", product_query),
            "estimated_min_vnd": parsed.get("estimated_min_vnd"),
            "estimated_max_vnd": parsed.get("estimated_max_vnd"),
            "suggested_vnd": parsed.get("suggested_vnd"),
            "sources_summary": parsed.get("sources_summary"),
            "confidence": parsed.get("confidence", "medium"),
            "notes": parsed.get("notes"),
        }
        logger.log_event("WEB_SEARCH_END", {"found": True, "confidence": result.get("confidence")})
        return result

    except Exception as e:
        logger.log_event("WEB_SEARCH_ERROR", {"error": str(e)})
        return {
            "found": False,
            "source": "openai_web_search",
            "error": str(e),
            "product_query": product_query,
            "message": _CATALOG_MISS_HINT,
        }
