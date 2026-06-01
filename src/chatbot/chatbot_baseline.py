"""Chatbot baseline — same persona, no tools (@hanhvs H6)."""
from typing import Optional

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

PRICE_CHECK_CHATBOT_PROMPT = """Bạn là chuyên gia tư vấn giá đồ cũ tại Việt Nam.
Người dùng mô tả sản phẩm và tình trạng; bạn ước lượng khoảng giá thị trường (VND).

Quy tắc:
- Trả lời ngắn gọn, tiếng Việt.
- Đưa một khoảng giá (triệu VND) và 1–2 câu lý do.
- Bạn KHÔNG có công cụ tra cứu — chỉ dựa trên kiến thức chung (baseline để so với agent).
"""


def run_chatbot(llm: LLMProvider, user_input: str) -> str:
    logger.log_event("CHATBOT_START", {"input": user_input, "model": llm.model_name})
    result = llm.generate(user_input, system_prompt=PRICE_CHECK_CHATBOT_PROMPT)
    answer = result["content"]
    logger.log_event("CHATBOT_END", {"usage": result.get("usage"), "latency_ms": result.get("latency_ms")})
    return answer


# Demo queries (T1 / T3 from task plan)
DEMO_QUERIES = [
    "iPhone 13 128GB, pin 88%, màn ok, vỏ đẹp, đủ hộp sạc — giá bán lại?",
    "MacBook Air M1 256GB, pin 85%, vỏ trầy nhẹ, không hộp — giá rao bán?",
]
