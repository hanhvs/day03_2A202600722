"""
Mock product catalog for PriceCheck Agent v1 (@hanhvs).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# reference_vnd = giá mới / MSRP tham chiếu (VND)
CATALOG: List[Dict[str, Any]] = [
    {"canonical_name": "iPhone 13 128GB", "category": "phone", "aliases": ["iphone 13", "iphone13 128"], "storage_gb": 128, "reference_vnd": 12_500_000},
    {"canonical_name": "iPhone 14 256GB", "category": "phone", "aliases": ["iphone 14", "iphone14 256"], "storage_gb": 256, "reference_vnd": 18_900_000},
    {"canonical_name": "Samsung Galaxy S23 256GB", "category": "phone", "aliases": ["s23", "galaxy s23"], "storage_gb": 256, "reference_vnd": 14_990_000},
    {"canonical_name": "Xiaomi 13T 256GB", "category": "phone", "aliases": ["xiaomi 13t", "13t"], "storage_gb": 256, "reference_vnd": 10_490_000},
    {"canonical_name": "MacBook Air M1 256GB", "category": "laptop", "aliases": ["macbook air m1", "mba m1"], "storage_gb": 256, "reference_vnd": 22_990_000},
    {"canonical_name": "MacBook Pro 14 M2 512GB", "category": "laptop", "aliases": ["macbook pro m2", "mbp 14 m2"], "storage_gb": 512, "reference_vnd": 42_990_000},
    {"canonical_name": "Dell XPS 13 i7 16GB", "category": "laptop", "aliases": ["dell xps 13", "xps 13"], "storage_gb": 512, "reference_vnd": 28_500_000},
    {"canonical_name": "Sony A7III body", "category": "camera", "aliases": ["sony a7iii", "a7iii", "a7 mark iii"], "storage_gb": None, "reference_vnd": 32_000_000},
    {"canonical_name": "Canon EOS R6 Mark II body", "category": "camera", "aliases": ["canon r6 ii", "eos r6 mark ii"], "storage_gb": None, "reference_vnd": 48_500_000},
    {"canonical_name": "iPad Air 5 64GB WiFi", "category": "tablet", "aliases": ["ipad air 5", "ipad air m1"], "storage_gb": 64, "reference_vnd": 13_990_000},
    {"canonical_name": "AirPods Pro 2", "category": "audio", "aliases": ["airpods pro 2", "app2"], "storage_gb": None, "reference_vnd": 5_490_000},
    {"canonical_name": "Apple Watch Series 8 45mm", "category": "wearable", "aliases": ["apple watch s8", "watch series 8"], "storage_gb": None, "reference_vnd": 8_990_000},
    {"canonical_name": "PlayStation 5 Slim", "category": "gaming", "aliases": ["ps5", "playstation 5"], "storage_gb": None, "reference_vnd": 12_490_000},
    {"canonical_name": "Nintendo Switch OLED", "category": "gaming", "aliases": ["switch oled", "nintendo switch"], "storage_gb": None, "reference_vnd": 8_290_000},
    {"canonical_name": "Logitech MX Master 3S", "category": "accessory", "aliases": ["mx master 3s", "logitech mx master"], "storage_gb": None, "reference_vnd": 2_490_000},
    {"canonical_name": "DJI Mini 3 Pro", "category": "drone", "aliases": ["dji mini 3 pro", "mini 3 pro"], "storage_gb": None, "reference_vnd": 16_990_000},
    {"canonical_name": "Kindle Paperwhite 11", "category": "ereader", "aliases": ["kindle paperwhite", "paperwhite 11"], "storage_gb": 8, "reference_vnd": 3_790_000},
    {"canonical_name": "ASUS ROG Zephyrus G14", "category": "laptop", "aliases": ["rog g14", "zephyrus g14"], "storage_gb": 512, "reference_vnd": 35_990_000},
]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_match(query: str, product: Dict[str, Any]) -> float:
    q = _normalize_text(query)
    names = [_normalize_text(product["canonical_name"])] + [_normalize_text(a) for a in product["aliases"]]
    best = 0.0
    for name in names:
        if q == name:
            return 1.0
        if name in q or q in name:
            best = max(best, 0.85)
        overlap = len(set(q.split()) & set(name.split())) / max(len(set(name.split())), 1)
        best = max(best, overlap * 0.7)
    storage_match = re.search(r"(\d+)\s*gb", q)
    if storage_match and product.get("storage_gb"):
        if int(storage_match.group(1)) == product["storage_gb"]:
            best += 0.1
    return min(best, 1.0)


def normalize_product(query: str) -> Dict[str, Any]:
    """Map free-text product mention to catalog entry."""
    if not query or not query.strip():
        return {"matched": False, "error": "empty_query"}

    ranked = sorted(CATALOG, key=lambda p: _score_match(query, p), reverse=True)
    best = ranked[0]
    score = _score_match(query, best)

    if score < 0.35:
        return {
            "matched": False,
            "canonical_name": None,
            "category": None,
            "storage_gb": None,
            "confidence": round(score, 2),
            "message": "Không khớp catalog. Thử ghi rõ model và dung lượng (vd: iPhone 13 128GB).",
        }

    return {
        "matched": True,
        "canonical_name": best["canonical_name"],
        "category": best["category"],
        "storage_gb": best.get("storage_gb"),
        "confidence": round(score, 2),
    }


def get_reference_price(
    canonical_name: str,
    storage_gb: Optional[int] = None,
) -> Dict[str, Any]:
    """Return MSRP / reference price from mock catalog."""
    name = _normalize_text(canonical_name)
    for product in CATALOG:
        if _normalize_text(product["canonical_name"]) == name:
            ref = product["reference_vnd"]
            if storage_gb and product.get("storage_gb") and storage_gb != product["storage_gb"]:
                # Rough adjustment if user asks different storage tier
                ratio = storage_gb / product["storage_gb"]
                ref = int(ref * min(max(ratio, 0.85), 1.25))
            return {
                "found": True,
                "canonical_name": product["canonical_name"],
                "reference_vnd": ref,
                "currency": "VND",
                "source": "mock_catalog",
            }

    # fallback: fuzzy
    norm = normalize_product(canonical_name)
    if norm.get("matched"):
        return get_reference_price(norm["canonical_name"], storage_gb=storage_gb)

    return {
        "found": False,
        "canonical_name": canonical_name,
        "reference_vnd": None,
        "currency": "VND",
        "source": "mock_catalog",
        "message": "Sản phẩm không có trong catalog.",
    }


def format_observation(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
