# Product catalog data

File: **`products_catalog.json`**

## Chỉnh sửa thủ công

- Thêm/sửa sản phẩm trong mảng `products`
- `reference_vnd`: giá tham chiếu mới (VND)
- `aliases`: từ khóa để `normalize_product` khớp

## Cập nhật tự động (sau Final Answer)

Khi agent chạy với `persist_catalog_updates=True` (mặc định), mỗi lần có **Final Answer**:

1. Ghi thêm một phần tử vào `market_observations[]` của sản phẩm
2. Cập nhật `last_market_summary` (tier, khoảng giá, số lần quan sát)
3. Ghi `updated_at` ở root file

Ví dụ observation:

```json
{
  "recorded_at": "2026-06-01T12:00:00+00:00",
  "source": "agent_final_answer",
  "tier": "good",
  "estimated_min_vnd": 8000000,
  "estimated_max_vnd": 9000000,
  "suggested_vnd": 8500000,
  "user_query": "iPhone 13 128GB, pin 88%..."
}
```

Tắt ghi file: `ReActAgent(llm, tools, persist_catalog_updates=False)`

Đổi đường dẫn: biến môi trường `PRODUCTS_CATALOG_PATH`
