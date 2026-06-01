"""Mock comparable listings search for PriceCheck Agent v1 (@0infinitive0)."""
from __future__ import annotations

from typing import Dict, Any

from src.tools.product_catalog import get_reference_price, normalize_product

TIER_ADJUSTMENTS = {
    "like_new": {"avg": 0.92, "min": 0.88, "max": 0.98, "count": 10},
    "good": {"avg": 0.78, "min": 0.70, "max": 0.85, "count": 12},
    "fair": {"avg": 0.62, "min": 0.53, "max": 0.70, "count": 9},
    "poor": {"avg": 0.45, "min": 0.35, "max": 0.55, "count": 6},
}

DEFAULT_REFERENCE = 10_000_000


def _normalize_tier(tier: str) -> str:
    tier = tier.lower().strip().replace(" ", "_")
    return tier if tier in TIER_ADJUSTMENTS else "good"


def search_comparable_listings(canonical_name: str, tier: str) -> Dict[str, Any]:
    """Return mock market observation for a canonical product name and condition tier."""
    norm = normalize_product(canonical_name)
    source_name = norm["canonical_name"] if norm.get("matched") else canonical_name
    reference = get_reference_price(source_name)
    base_price = reference["reference_vnd"] if reference.get("found") else DEFAULT_REFERENCE
    tier_key = _normalize_tier(tier)
    adjustments = TIER_ADJUSTMENTS[tier_key]

    avg_vnd = int(base_price * adjustments["avg"])
    min_vnd = int(base_price * adjustments["min"])
    max_vnd = int(base_price * adjustments["max"])

    if min_vnd <= 0:
        min_vnd = max(1_000_000, avg_vnd - 1_000_000)
    if max_vnd <= 0:
        max_vnd = avg_vnd + 1_000_000

    return {
        "canonical_name": source_name,
        "tier": tier_key,
        "avg_vnd": avg_vnd,
        "min_vnd": min_vnd,
        "max_vnd": max_vnd,
        "sample_count": adjustments["count"],
        "source": "mock_listings",
    }
