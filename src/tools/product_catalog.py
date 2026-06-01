"""
Product catalog loaded from data/products_catalog.json.
Supports persisting market observations after agent Final Answer.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CATALOG_PATH = _PROJECT_ROOT / "data" / "products_catalog.json"

_catalog_cache: Optional[Dict[str, Any]] = None
_catalog_path: Optional[Path] = None


def get_catalog_path() -> Path:
    global _catalog_path
    if _catalog_path is None:
        env_path = os.getenv("PRODUCTS_CATALOG_PATH")
        _catalog_path = Path(env_path) if env_path else _DEFAULT_CATALOG_PATH
    return _catalog_path


def load_catalog(*, reload: bool = False) -> Dict[str, Any]:
    """Load full catalog document from JSON."""
    global _catalog_cache
    if _catalog_cache is not None and not reload:
        return _catalog_cache

    path = get_catalog_path()
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")

    with open(path, encoding="utf-8") as f:
        _catalog_cache = json.load(f)
    return _catalog_cache


def save_catalog(data: Optional[Dict[str, Any]] = None) -> Path:
    """Write catalog JSON (pretty, UTF-8)."""
    global _catalog_cache
    doc = data if data is not None else load_catalog()
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()

    path = get_catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")

    _catalog_cache = doc
    return path


def get_products() -> List[Dict[str, Any]]:
    return list(load_catalog().get("products", []))


def reload_catalog() -> List[Dict[str, Any]]:
    load_catalog(reload=True)
    return get_products()


def _find_product(canonical_name: str) -> Optional[Dict[str, Any]]:
    name = _normalize_text(canonical_name)
    for product in get_products():
        if _normalize_text(product["canonical_name"]) == name:
            return product
    return None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_match(query: str, product: Dict[str, Any]) -> float:
    q = _normalize_text(query)
    names = [_normalize_text(product["canonical_name"])] + [
        _normalize_text(a) for a in product.get("aliases", [])
    ]
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

    catalog = get_products()
    ranked = sorted(catalog, key=lambda p: _score_match(query, p), reverse=True)
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
        "product_id": best.get("id"),
        "category": best["category"],
        "storage_gb": best.get("storage_gb"),
        "confidence": round(score, 2),
    }


def get_reference_price(
    canonical_name: str,
    storage_gb: Optional[int] = None,
) -> Dict[str, Any]:
    """Return MSRP / reference price from catalog JSON."""
    product = _find_product(canonical_name)
    if product:
        ref = product["reference_vnd"]
        if storage_gb and product.get("storage_gb") and storage_gb != product["storage_gb"]:
            ratio = storage_gb / product["storage_gb"]
            ref = int(ref * min(max(ratio, 0.85), 1.25))
        return {
            "found": True,
            "canonical_name": product["canonical_name"],
            "product_id": product.get("id"),
            "reference_vnd": ref,
            "currency": "VND",
            "source": "products_catalog.json",
        }

    norm = normalize_product(canonical_name)
    if norm.get("matched"):
        return get_reference_price(norm["canonical_name"], storage_gb=storage_gb)

    return {
        "found": False,
        "canonical_name": canonical_name,
        "reference_vnd": None,
        "currency": "VND",
        "source": "products_catalog.json",
        "message": "Sản phẩm không có trong catalog.",
    }


def parse_vnd_from_final_answer(text: str) -> Dict[str, Optional[int]]:
    """Extract min/max/suggested VND from Vietnamese answer (triệu / VND)."""
    t = text.lower().replace(",", ".")
    result: Dict[str, Optional[int]] = {
        "estimated_min_vnd": None,
        "estimated_max_vnd": None,
        "suggested_vnd": None,
    }

    range_m = re.search(
        r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*tri[eệ]u",
        t,
    )
    if range_m:
        result["estimated_min_vnd"] = int(float(range_m.group(1)) * 1_000_000)
        result["estimated_max_vnd"] = int(float(range_m.group(2)) * 1_000_000)

    for label, pattern in [
        ("suggested_vnd", r"(?:đề xuất|nên đăng|khoảng)\s*~?\s*(\d+(?:\.\d+)?)\s*tri[eệ]u"),
        ("suggested_vnd", r"(\d+(?:\.\d+)?)\s*tri[eệ]u"),
    ]:
        m = re.search(pattern, t)
        if m and result.get("suggested_vnd") is None:
            result["suggested_vnd"] = int(float(m.group(1)) * 1_000_000)

    vnd_m = re.search(r"(\d[\d.]*)\s*vnd", t)
    if vnd_m:
        raw = int(float(vnd_m.group(1).replace(".", "")))
        if result["suggested_vnd"] is None:
            result["suggested_vnd"] = raw

    return result


def append_market_observation(
    canonical_name: str,
    *,
    tier: Optional[str] = None,
    estimated_min_vnd: Optional[int] = None,
    estimated_max_vnd: Optional[int] = None,
    suggested_vnd: Optional[int] = None,
    listings_avg_vnd: Optional[int] = None,
    user_query: Optional[str] = None,
    final_answer: Optional[str] = None,
    source: str = "agent_final_answer",
) -> Dict[str, Any]:
    """Append one market observation and save JSON."""
    doc = load_catalog()
    product = None
    for p in doc["products"]:
        if _normalize_text(p["canonical_name"]) == _normalize_text(canonical_name):
            product = p
            break

    if product is None:
        return {"saved": False, "error": f"Product not in catalog: {canonical_name}"}

    obs: Dict[str, Any] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "tier": tier,
        "estimated_min_vnd": estimated_min_vnd,
        "estimated_max_vnd": estimated_max_vnd,
        "suggested_vnd": suggested_vnd,
        "listings_avg_vnd": listings_avg_vnd,
    }
    if user_query:
        obs["user_query"] = user_query
    if final_answer:
        obs["final_answer_excerpt"] = final_answer[:500]

    product.setdefault("market_observations", []).append(obs)

    # Rolling summary for quick reads / future listings mock
    product["last_market_summary"] = {
        "updated_at": obs["recorded_at"],
        "tier": tier,
        "estimated_min_vnd": estimated_min_vnd,
        "estimated_max_vnd": estimated_max_vnd,
        "suggested_vnd": suggested_vnd,
        "listings_avg_vnd": listings_avg_vnd,
        "observation_count": len(product["market_observations"]),
    }

    path = save_catalog(doc)
    return {
        "saved": True,
        "catalog_path": str(path),
        "product_id": product.get("id"),
        "canonical_name": product["canonical_name"],
        "observation": obs,
    }


def _parse_observation_json(observation: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(observation)
    except json.JSONDecodeError:
        return None


def update_catalog_from_agent_session(
    user_input: str,
    history: List[Dict[str, Any]],
    final_answer: str,
    *,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    After Final Answer: merge tool observations + parsed prices → market_observations in JSON.
    """
    canonical_name: Optional[str] = None
    tier: Optional[str] = None
    listings_avg_vnd: Optional[int] = None

    for step in history:
        action = step.get("action") or {}
        tool = action.get("tool")
        obs_raw = step.get("observation")
        if not tool or not obs_raw:
            continue
        data = _parse_observation_json(obs_raw)
        if not data:
            continue

        if tool == "normalize_product" and data.get("matched"):
            canonical_name = data.get("canonical_name")
        elif tool == "score_condition":
            tier = data.get("tier")
        elif tool == "search_comparable_listings":
            listings_avg_vnd = data.get("avg_vnd")

    if not canonical_name:
        norm = normalize_product(user_input)
        if norm.get("matched"):
            canonical_name = norm["canonical_name"]

    if not canonical_name:
        return {"saved": False, "reason": "no_canonical_name"}

    prices = parse_vnd_from_final_answer(final_answer)
    payload = {
        "canonical_name": canonical_name,
        "tier": tier,
        "listings_avg_vnd": listings_avg_vnd,
        "user_query": user_input,
        "final_answer": final_answer,
        **prices,
    }

    if not persist:
        return {"saved": False, "dry_run": True, "canonical_name": canonical_name, **prices, "tier": tier}

    return append_market_observation(
        canonical_name,
        tier=tier,
        listings_avg_vnd=listings_avg_vnd,
        user_query=user_input,
        final_answer=final_answer,
        source="agent_final_answer",
        **prices,
    )


def format_observation(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
