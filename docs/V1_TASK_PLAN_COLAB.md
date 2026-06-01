# V1 Task Plan — Colab chung | Giá thị trường theo tình trạng sản phẩm

**Team:** @hanhvs · @0infinitive0  
**Mục tiêu v1:** Agent ReAct trả lời được câu dạng: *"Tôi có [sản phẩm A], tình trạng [mô tả] — giá thị trường khoảng bao nhiêu?"*  
**Môi trường:** Google Colab (1 notebook chung, repo `src/` sync qua Drive hoặc clone GitHub)  
**Deadline nội bộ v1:** 1 buổi làm chung + 1 buổi ghép (xem mốc bên dưới)

---

## 1. Product vision (1 câu)

**PriceCheck Agent v1** — Trợ lý ước lượng **khoảng giá bán lại** dựa trên tên sản phẩm + mô tả tình trạng, bằng cách gọi tuần tự tool (giá tham chiếu → hệ số tình trạng → tin đăng tương đương → tổng hợp), không đoán một lần như chatbot.

---

## 2. Luồng ReAct mong đợi (cả team thống nhất)

```
User: "MacBook Air M1 256GB, pin 85%, vỏ trầy nhẹ, không hộp — giá rao bán?"
  → Thought: cần chuẩn hóa sản phẩm
  → Action: normalize_product("MacBook Air M1 256GB")
  → Observation: { canonical_name, category, storage_gb }

  → Thought: cần giá tham chiếu mới
  → Action: get_reference_price("MacBook Air M1 256GB", storage_gb=256)
  → Observation: { reference_vnd, source: "mock_catalog" }

  → Thought: map tình trạng user mô tả
  → Action: score_condition("pin 85%, vỏ trầy nhẹ, không hộp")
  → Observation: { tier: "good", multiplier: 0.72, notes: [...] }

  → Thought: xem giá tin tương đương
  → Action: search_comparable_listings("MacBook Air M1 256GB", tier="good")
  → Observation: { avg_vnd, min_vnd, max_vnd, sample_count: 12 }

  → Final Answer: Khoảng giá hợp lý X–Y triệu, đề xuất đăng ~Z ...
```

**Chatbot baseline** (cùng prompt, không tool): thường đưa 1 con số không có nguồn → dùng làm so sánh trong báo cáo.

---

## 3. Cấu trúc Colab (ai cũng push vào cùng notebook)

| Cell block | Owner | Ghi chú |
|------------|--------|---------|
| `00_setup` | @hanhvs | `pip install`, mount Drive, `load_dotenv`, secrets Colab |
| `01_imports` | @hanhvs | Import `ReActAgent`, providers |
| `02_tools_registry` | **Ghép** | Import tool từ 2 file module |
| `03_chatbot_demo` | @hanhvs | Hàm chatbot 1 shot + 2 câu test |
| `04_agent_demo` | @0infinitive0 | Khởi tạo agent + 2 câu test killer |
| `05_logs_preview` | @0infinitive0 | Đọc `logs/` / in trace 1 lần chạy |
| `06_compare_table` | **Ghép** | Bảng Chatbot vs Agent (2 case) |

**Quy ước Git/Colab:**  
- Branch: `v1-price-agent`  
- Commit message: `[hanhvs]` / `[0infinitive0]` prefix  
- Không sửa cùng file cùng lúc: @hanhvs → `agent/` + `chatbot` + provider factory; @0infinitive0 → `tools/` + `data/` + test cases

---

## 4. Tool inventory (mock data — đủ rubric 2+ tools)

| Tool | Input | Output (gợi ý) | Owner |
|------|--------|----------------|--------|
| `normalize_product` | `query: str` | `canonical_name`, `category`, attrs | @hanhvs |
| `get_reference_price` | `canonical_name`, optional attrs | `reference_vnd`, `currency` | @hanhvs |
| `score_condition` | `condition_text: str` | `tier`, `multiplier`, `risk_flags[]` | @0infinitive0 |
| `search_comparable_listings` | `canonical_name`, `tier` | `avg/min/max_vnd`, `sample_count` | @0infinitive0 |

**File gợi ý:**

```
src/tools/
  product_catalog.py      # @hanhvs — DB giả 15–20 sản phẩm (điện thoại, laptop, máy ảnh...)
  condition_scoring.py    # @0infinitive0 — rule + keyword (pin, trầy, hộp, bảo hành...)
  listings_mock.py        # @0infinitive0 — dict listing theo (product, tier)
  __init__.py               # export TOOL_SPECS cho agent
```

---

## 5. Chia task đều

### @hanhvs — Pipeline & Agent core (~50%)

| # | Task | Deliverable | Ước lượng |
|---|------|-------------|-----------|
| H1 | Colab `00_setup` + `.env` / Colab Secrets (`OPENAI_API_KEY`, `DEFAULT_PROVIDER`) | Notebook chạy được cell đầu | 30 phút |
| H2 | `src/tools/product_catalog.py` + mock 15 sản phẩm VN | `normalize_product`, `get_reference_price` | 1h |
| H3 | `get_system_prompt()` — mô tả 4 tool + format ReAct (Thought/Action/Observation/Final Answer) | Prompt in repo, không chỉ trong Colab | 45 phút |
| H4 | `ReActAgent.run()` — loop, gọi `llm.generate`, append history | Agent trả về text (chưa cần parse hoàn hảo) | 1.5h |
| H5 | Parse `Action: name(args)` — regex đơn giản + log `AGENT_STEP` | Parse được 2 tool của H2 | 1h |
| H6 | `chatbot_baseline.py` hoặc cell Colab — cùng system persona, **không** tool | 2 câu demo chatbot | 30 phút |
| H7 | Factory `get_llm_from_env()` dùng chung Colab | 1 hàm, OpenAI mặc định | 20 phút |

**Definition of done (@hanhvs):** Colab chạy chatbot + agent gọi được ít nhất `normalize_product` và `get_reference_price`; log có `AGENT_START` / `AGENT_END`.

---

### @0infinitive0 — Tools giá & Demo (~50%)

| # | Task | Deliverable | Ước lượng |
|---|------|-------------|-----------|
| O1 | `condition_scoring.py` — map mô tả → `tier` + `multiplier` | Bảng tier: `like_new` / `good` / `fair` / `poor` | 1h |
| O2 | `listings_mock.py` — `search_comparable_listings` | ≥3 tier × ≥5 sản phẩm có avg/min/max | 1h |
| O3 | `TOOL_SPECS` list trong `tools/__init__.py` — description chi tiết cho LLM | Agent nhận đủ 4 tool metadata | 30 phút |
| O4 | `_execute_tool()` — map tên → hàm (4 tools) | Một chỗ execute, trả string Observation | 45 phút |
| O5 | Hoàn thiện parse + `Final Answer` break loop (phối với @hanhvs trên `agent.py`) | Agent kết thúc đúng sau 3–4 bước | 1h |
| O6 | Colab `04_agent_demo` + `05_logs_preview` | 2 killer queries chạy end-to-end | 45 phút |
| O7 | `tests/test_price_flow.py` hoặc cell assert — 1 happy path | `assert "triệu" in answer` hoặc check tool order | 30 phút |

**Definition of done (@0infinitive0):** Một câu killer chạy đủ 4 tool và có `Final Answer`; observation không rỗng.

---

## 6. Killer test cases (cả team chạy khi ghép)

| ID | Câu hỏi | Kỳ vọng agent |
|----|---------|----------------|
| T1 | *"iPhone 13 128GB, pin 88%, màn ok, vỏ đẹp, đủ hộp sạc — giá bán lại?"* | 4 bước tool → khoảng giá VND |
| T2 | *"Sony A7III, shutter 15k, cảm biến có 1 đốm nhỏ, kèm 1 lens 50mm — thị trường bao nhiêu?"* | normalize → reference → condition (fair) → listings |
| T3 (chatbot only) | Cùng T1 | Một con số, không cite bước → ghi vào bảng so sánh |

---

## 7. Mốc ghép (làm chung trên Colab)

| Thời điểm | Việc | Ai lead |
|-----------|------|---------|
| **M1 — 30%** | Merge `TOOL_SPECS` + chạy `normalize_product` từ Colab | @0infinitive0 push tools, @hanhvs pull |
| **M2 — 60%** | `run()` gọi được 2 tool đầu + 1 tool sau | @hanhvs |
| **M3 — 90%** | Full T1 + xem log JSON 1 trace | Cả hai |
| **M4 — 100%** | Điền 4 dòng bảng so sánh + screenshot Colab | Cả hai → copy vào group report draft |

---

## 8. Tránh conflict khi làm song song

| File / vùng | Chỉ sửa bởi |
|-------------|-------------|
| `src/agent/agent.py` — `run`, `get_system_prompt`, parse | @hanhvs (O5 chỉ PR nhỏ qua branch) |
| `src/agent/agent.py` — `_execute_tool` | @0infinitive0 |
| `src/tools/product_catalog.py` | @hanhvs |
| `src/tools/condition_scoring.py`, `listings_mock.py` | @0infinitive0 |
| `notebooks/Lab3_v1_PriceAgent.ipynb` | Chia cell theo bảng §3 |
| `docs/V1_TASK_PLAN_COLAB.md` | Cả hai (changelog cuối file) |

**Quy tắc merge:** Ai xong task trước → mở PR nhỏ; người kia rebase trước khi sửa `agent.py`.

---

## 9. Definition of Done — v1 (cả nhóm)

- [ ] 4 tool mock, mô tả rõ trong system prompt  
- [ ] ReAct loop ≤ `max_steps` (mặc định 5–6)  
- [ ] Telemetry: ít nhất 1 trace thành công trong `logs/`  
- [ ] Colab: 1 cell chatbot + 1 cell agent, cùng câu T1  
- [ ] Bảng so sánh 2 dòng: Chatbot vs Agent (đúng/sai/khoảng giá)  
- [ ] Ghi contribution vào individual report (module đã code)

---

## 10. Gợi ý mở rộng v2 (không làm trong v1)

- Coupon / phụ kiện ảnh hưởng giá  
- Retry khi `normalize_product` không khớp catalog  
- Guardrail: từ chối hàng cấm / không có trong DB  

---

## Changelog

| Ngày | Người | Ghi chú |
|------|--------|---------|
| 2026-06-01 | — | Tạo plan v1 Colab, chủ đề giá thị trường theo tình trạng |
| 2026-06-01 | @hanhvs | Hoàn thành H1–H7: catalog, agent, chatbot, factory, Colab notebook |
