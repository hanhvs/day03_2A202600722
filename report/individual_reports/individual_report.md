# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Vương Sỹ Hạnh
- **Student ID**: 2A202600722
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

*Đóng góp code và tài liệu cho PriceCheck Agent (nhóm PriceCheck Team).*

- **Modules Implemented**:
  - `src/agent/agent.py` — ReAct loop v1/v1.1/v2, `run_stream()` (SSE), tool retry, metrics
  - `src/agent/action_parser.py` — parse Thought/Action/Final Answer; v2 `sanitize_llm_output()`
  - `src/agent/guardrails.py` — off-topic filter, allowlist tool (Agent v2)
  - `src/tools/product_catalog.py` — catalog JSON, normalize, reference price, cập nhật sau Final Answer
  - `src/tools/openai_web_search.py` — OpenAI Web Search khi catalog miss
  - `src/chatbot/chatbot_baseline.py` — baseline so sánh
  - `src/core/llm_factory.py` — `get_llm_from_env()`
  - `src/api/main.py`, `static/chat/index.html` — API SSE + UI chat
  - `src/telemetry/metrics.py` — cost/token (`LLM_METRIC`)
  - `data/products_catalog.json` — 18 sản phẩm mock

- **Code Highlights**:

```python
# Agent v2 — guardrail trước ReAct loop
if is_off_topic(user_input):
    yield {"type": "final_answer", "text": off_topic_message()}
    return

# Catalog miss → gợi ý web search trong Observation
{"matched": false, "catalog_miss": true, "recommended_tool": "search_product_online"}

# Metrics sau mỗi bước LLM
tracker.track_request(provider, model, usage, latency_ms)
```

- **Documentation**: Agent chạy vòng `Thought` → `Action` → hệ thống gọi tool → `Observation` JSON ghép lại conversation → đến `Final Answer`. Chatbot dùng cùng persona nhưng **một** lần `generate`, không có Observation. Agent v2 (cải tiến sau RCA v1): parser, guardrails, retry, metrics — mô tả thêm ở báo cáo nhóm và mục II bên dưới.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Agent không thực thi tool khi LLM trả `Action: normalize_product("iPhone 13 128GB")` bên trong block markdown ` ```json ... ``` `. UI/SSE không có event `tool_start`; log `has_action: false`.

- **Log Source** (`logs/YYYY-MM-DD.log`):

```json
{"timestamp": "2026-06-01T10:00:00", "event": "AGENT_STEP", "data": {"step": 0, "has_action": false, "thought": "Cần chuẩn hóa sản phẩm"}}
```

- **Diagnosis**: `parse_action()` dùng regex trên raw output; chuỗi fence che dòng `Action:`. Lỗi thuộc nhóm **JSON/Action parse** trong [EVALUATION.md](../../EVALUATION.md).

- **Solution**:
  1. v2: `sanitize_llm_output()` trong `action_parser.py` gỡ fence trước parse.
  2. System prompt: cấm markdown code block quanh Action.
  3. (Liên quan catalog miss) v1.1: thêm `search_product_online` khi `catalog_miss` — case debug thứ hai đã xử lý bằng prompt + field `recommended_tool` trong Observation.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: `Thought` buộc model nêu kế hoạch (vd. “cần giá tham chiếu rồi đánh giá tình trạng”). Chatbot trả lời một khối — nhanh nhưng khi GV hỏi “số đó từ đâu?” khó trả lời bằng trace.

2. **Reliability**: Agent **kém hơn** chatbot trên câu đơn giản (chỉ hỏi giá một model phổ biến) vì tốn 3–4 vòng LLM. Agent **tốt hơn** khi có mô tả tình trạng + nhiều bước, hoặc sản phẩm không có trong catalog (nhờ web search).

3. **Observation**: Khi Observation trả `catalog_miss: true`, model gần như luôn gọi `search_product_online` sau khi chỉnh prompt — chứng tỏ **feedback từ tool** quan trọng hơn việc chỉ mở rộng system prompt.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Tách worker cho `search_product_online`; queue async cho API SSE thay vì block trong `run_stream`.
- **Safety**: Supervisor LLM duyệt `Final Answer`; rate limit API; mở rộng guardrail intent.
- **Performance**: Cache catalog in-memory; dashboard từ `log_analyzer` + `LLM_METRIC` (đã có nền tảng v2). **Không** crawl marketplace trong lab — khi production nên dùng API đối tác thay vì scrape (theo hướng nhóm).

---

*Nộp: `report/individual_reports/individual_report.md` (theo [SCORING.md](../../SCORING.md) và `TEMPLATE_INDIVIDUAL_REPORT.md`).*
