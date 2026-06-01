import json
from typing import List, Dict, Any, Optional

from src.agent.action_parser import parse_action, parse_final_answer, parse_thought
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.tools.product_catalog import (
    format_observation,
    get_reference_price,
    normalize_product,
    update_catalog_from_agent_session,
)

# Partner tools — wired when modules exist (@0infinitive0)
try:
    from src.tools.condition_scoring import score_condition
except ImportError:
    score_condition = None  # type: ignore

try:
    from src.tools.listings_mock import search_comparable_listings
except ImportError:
    search_comparable_listings = None  # type: ignore


class ReActAgent:
    """ReAct agent: Thought → Action → Observation → Final Answer."""

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 6,
        persist_catalog_updates: bool = True,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.persist_catalog_updates = persist_catalog_updates
        self.history: List[Dict[str, Any]] = []

    def get_system_prompt(self) -> str:
        tool_lines = "\n".join(
            f"  - {t['name']}: {t['description']}" for t in self.tools
        )
        return f"""Bạn là PriceCheck Agent — tư vấn giá bán lại đồ cũ tại Việt Nam.

Công cụ (gọi tuần tự khi cần):
{tool_lines}

Quy trình gợi ý:
1. normalize_product — nhận diện sản phẩm
2. get_reference_price — giá tham chiếu mới (VND)
3. score_condition — đánh giá tình trạng từ mô tả user
4. search_comparable_listings — giá tin tương đương
5. Final Answer — khoảng giá (triệu VND), gợi ý đăng, lưu ý rủi ro

Định dạng BẮT BUỘC (không dùng markdown code block):
Thought: <suy luận ngắn>
Action: tool_name(tham_số)
(hệ thống sẽ trả Observation — bạn không tự viết Observation)

Khi đủ dữ liệu:
Thought: <tổng hợp>
Final Answer: <câu trả lời tiếng Việt cho user>

Ví dụ Action:
Action: normalize_product("iPhone 13 128GB")
Action: get_reference_price("iPhone 13 128GB", storage_gb=128)
Action: score_condition("pin 88%, màn ok, đủ hộp")
Action: search_comparable_listings("iPhone 13 128GB", tier="good")
"""

    def run(self, user_input: str) -> str:
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        system_prompt = self.get_system_prompt()
        conversation = f"Question: {user_input}\n"
        steps = 0
        last_content = ""

        while steps < self.max_steps:
            result = self.llm.generate(conversation, system_prompt=system_prompt)
            content = result.get("content") or ""
            last_content = content

            thought = parse_thought(content)
            final = parse_final_answer(content)
            action = parse_action(content)

            step_log = {
                "step": steps,
                "thought": thought,
                "has_action": action is not None,
                "has_final": final is not None,
                "usage": result.get("usage"),
                "latency_ms": result.get("latency_ms"),
            }
            if action:
                step_log["action"] = {"tool": action[0], "args": action[1]}
            logger.log_event("AGENT_STEP", step_log)

            self.history.append({"step": steps, "llm_output": content, **step_log})

            if final:
                catalog_update = self._maybe_update_catalog(user_input, final)
                logger.log_event(
                    "AGENT_END",
                    {"steps": steps + 1, "status": "final_answer", "catalog_update": catalog_update},
                )
                return final

            if action:
                tool_name, args_str = action
                observation = self._execute_tool(tool_name, args_str)
                self.history[-1]["observation"] = observation
                conversation += f"{content.strip()}\nObservation: {observation}\n"
            else:
                conversation += f"{content.strip()}\n"
                if steps >= self.max_steps - 1:
                    break

            steps += 1

        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_or_incomplete"})
        if parse_final_answer(last_content):
            final = parse_final_answer(last_content)  # type: ignore
            self._maybe_update_catalog(user_input, final)
            return final
        return (
            last_content.strip()
            or "Agent chưa hoàn thành trong số bước cho phép. Kiểm tra logs/ và format Action."
        )

    def _maybe_update_catalog(self, user_input: str, final_answer: str) -> Dict[str, Any]:
        if not self.persist_catalog_updates:
            return {"saved": False, "reason": "persist_disabled"}
        try:
            return update_catalog_from_agent_session(
                user_input, self.history, final_answer, persist=True
            )
        except Exception as e:
            logger.log_event("CATALOG_UPDATE_ERROR", {"error": str(e)})
            return {"saved": False, "error": str(e)}

    def _execute_tool(self, tool_name: str, args_str: str) -> str:
        """Execute tools. @hanhvs: catalog tools; partner tools delegated when present."""
        from src.agent.action_parser import parse_tool_args

        pos, kw = parse_tool_args(args_str)
        logger.log_event("TOOL_CALL", {"tool": tool_name, "args": args_str, "parsed_pos": pos, "parsed_kw": kw})

        try:
            if tool_name == "normalize_product":
                query = str(pos[0]) if pos else args_str.strip('"')
                return format_observation(normalize_product(query))

            if tool_name == "get_reference_price":
                name = str(pos[0]) if pos else ""
                storage = kw.get("storage_gb")
                if storage is not None:
                    storage = int(storage)
                return format_observation(get_reference_price(name, storage_gb=storage))

            if tool_name == "score_condition":
                if score_condition is None:
                    return json.dumps(
                        {
                            "error": "score_condition chưa implement — @0infinitive0",
                            "stub": True,
                        },
                        ensure_ascii=False,
                    )
                text = str(pos[0]) if pos else args_str
                return format_observation(score_condition(text))

            if tool_name == "search_comparable_listings":
                if search_comparable_listings is None:
                    return json.dumps(
                        {
                            "error": "search_comparable_listings chưa implement — @0infinitive0",
                            "stub": True,
                        },
                        ensure_ascii=False,
                    )
                canonical = str(pos[0]) if pos else ""
                tier = str(kw.get("tier") or (pos[1] if len(pos) > 1 else "good"))
                return format_observation(search_comparable_listings(canonical, tier))

            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)

        except Exception as e:
            logger.log_event("TOOL_ERROR", {"tool": tool_name, "error": str(e)})
            return json.dumps({"error": str(e), "tool": tool_name}, ensure_ascii=False)
