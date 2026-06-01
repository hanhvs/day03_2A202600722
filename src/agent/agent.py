import json
from typing import Any, Dict, Generator, List, Optional

from src.agent.action_parser import (
    parse_action,
    parse_final_answer,
    parse_thought,
    sanitize_llm_output,
)
from src.agent.guardrails import (
    ALLOWED_TOOLS,
    is_off_topic,
    off_topic_message,
    validate_tool_name,
)
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
from src.tools.openai_web_search import search_product_online
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
        max_steps: int = 8,
        persist_catalog_updates: bool = True,
        tool_retry_limit: int = 1,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.persist_catalog_updates = persist_catalog_updates
        self.tool_retry_limit = tool_retry_limit
        self.history: List[Dict[str, Any]] = []
        self.agent_version = "v2"

    def get_system_prompt(self) -> str:
        tool_lines = "\n".join(
            f"  - {t['name']}: {t['description']}" for t in self.tools
        )
        return f"""Bạn là PriceCheck Agent v2 — tư vấn giá bán lại đồ cũ tại Việt Nam.

Công cụ (gọi tuần tự khi cần):
{tool_lines}

Quy tắc v2:
- KHÔNG bọc Action trong markdown ``` — chỉ một dòng Action: tool_name("...")
- Kiểm tra tên tool và tham số trước khi gọi; dùng đúng chuỗi trong dấu ngoặc kép.
- Câu hỏi không liên quan giá đồ cũ → trả lời Final Answer từ chối lịch sự.

Quy trình gợi ý:
1. normalize_product — nhận diện sản phẩm trong catalog nội bộ
2. Nếu matched=false hoặc catalog_miss → search_product_online (OpenAI web search, bắt buộc)
3. Nếu matched=true → get_reference_price → score_condition → search_comparable_listings
4. Final Answer — khoảng giá (triệu VND), nêu nguồn (catalog hoặc web search)

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
Action: search_product_online("Samsung Z Flip 5 256GB", "pin 90%, đẹp")
"""

    def run(self, user_input: str) -> str:
        final: Optional[str] = None
        for event in self.run_stream(user_input):
            if event.get("type") == "final_answer":
                final = event.get("text")
            elif event.get("type") == "error":
                return event.get("message", "Lỗi agent.")
            elif event.get("type") == "done" and final is None:
                final = event.get("fallback_text")
        return final or "Agent chưa hoàn thành."

    def run_stream(self, user_input: str) -> Generator[Dict[str, Any], None, None]:
        """Yield step events for SSE / live UI."""
        self.history = []
        logger.log_event(
            "AGENT_START",
            {"input": user_input, "model": self.llm.model_name, "version": self.agent_version},
        )

        yield {
            "type": "agent_start",
            "model": self.llm.model_name,
            "version": self.agent_version,
            "tools": [t["name"] for t in self.tools],
        }

        if is_off_topic(user_input):
            msg = off_topic_message()
            logger.log_event("GUARDRAIL_OFF_TOPIC", {"input": user_input})
            yield {"type": "final_answer", "step": 0, "text": msg}
            yield {"type": "done", "status": "off_topic"}
            return

        system_prompt = self.get_system_prompt()
        conversation = f"Question: {user_input}\n"
        steps = 0
        last_content = ""

        try:
            while steps < self.max_steps:
                yield {"type": "llm_start", "step": steps}

                result = self.llm.generate(conversation, system_prompt=system_prompt)
                content = result.get("content") or ""
                last_content = content

                usage = result.get("usage") or {}
                if usage:
                    tracker.track_request(
                        provider=result.get("provider", "unknown"),
                        model=self.llm.model_name,
                        usage=usage,
                        latency_ms=result.get("latency_ms", 0),
                    )

                parsed_content = sanitize_llm_output(content)
                thought = parse_thought(parsed_content)
                final = parse_final_answer(parsed_content)
                action = parse_action(parsed_content)

                yield {
                    "type": "llm_done",
                    "step": steps,
                    "latency_ms": result.get("latency_ms"),
                    "usage": result.get("usage"),
                    "raw": content,
                }

                if thought:
                    yield {"type": "thought", "step": steps, "text": thought}

                step_log: Dict[str, Any] = {
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
                    yield {"type": "final_answer", "step": steps, "text": final}
                    catalog_update = self._maybe_update_catalog(user_input, final)
                    yield {"type": "catalog_update", "data": catalog_update}
                    summary = tracker.session_summary()
                    logger.log_event(
                        "AGENT_END",
                        {
                            "steps": steps + 1,
                            "status": "final_answer",
                            "catalog_update": catalog_update,
                            "metrics": summary,
                        },
                    )
                    yield {"type": "metrics_summary", "data": summary}
                    yield {"type": "done", "status": "final_answer"}
                    return

                if action:
                    tool_name, args_str = action
                    if not validate_tool_name(tool_name):
                        observation = json.dumps(
                            {"error": f"Tool không hợp lệ: {tool_name}", "allowed": list(ALLOWED_TOOLS)},
                            ensure_ascii=False,
                        )
                        self.history[-1]["observation"] = observation
                        conversation += f"{content.strip()}\nObservation: {observation}\n"
                        steps += 1
                        continue

                    yield {
                        "type": "tool_start",
                        "step": steps,
                        "tool": tool_name,
                        "args": args_str,
                    }
                    observation = self._execute_tool_with_retry(tool_name, args_str)
                    self.history[-1]["observation"] = observation
                    yield {
                        "type": "tool_result",
                        "step": steps,
                        "tool": tool_name,
                        "observation": observation,
                    }
                    conversation += f"{content.strip()}\nObservation: {observation}\n"
                else:
                    conversation += f"{content.strip()}\n"
                    if steps >= self.max_steps - 1:
                        break

                steps += 1

            logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_or_incomplete"})
            fallback = parse_final_answer(last_content)
            if fallback:
                self._maybe_update_catalog(user_input, fallback)
                yield {"type": "final_answer", "step": steps, "text": fallback}
                yield {"type": "done", "status": "final_answer"}
                return

            fallback_text = (
                last_content.strip()
                or "Agent chưa hoàn thành trong số bước cho phép."
            )
            yield {"type": "done", "status": "incomplete", "fallback_text": fallback_text}

        except Exception as e:
            logger.log_event("AGENT_ERROR", {"error": str(e)})
            yield {"type": "error", "message": str(e)}
            yield {"type": "done", "status": "error"}

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

    def _execute_tool_with_retry(self, tool_name: str, args_str: str) -> str:
        observation = self._execute_tool(tool_name, args_str)
        for attempt in range(self.tool_retry_limit):
            try:
                data = json.loads(observation)
            except json.JSONDecodeError:
                break
            if not data.get("error") and not data.get("stub"):
                break
            logger.log_event(
                "TOOL_RETRY",
                {"tool": tool_name, "attempt": attempt + 1, "reason": data.get("error")},
            )
            observation = self._execute_tool(tool_name, args_str)
        return observation

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

            if tool_name == "search_product_online":
                product_q = str(pos[0]) if pos else args_str.strip('"')
                condition = str(kw.get("condition_text") or (pos[1] if len(pos) > 1 else ""))
                return format_observation(
                    search_product_online(product_q, condition_text=condition)
                )

            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)

        except Exception as e:
            logger.log_event("TOOL_ERROR", {"tool": tool_name, "error": str(e)})
            return json.dumps({"error": str(e), "tool": tool_name}, ensure_ascii=False)
