import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools import product_catalog as pc


def test_load_catalog_from_json():
    products = pc.get_products()
    assert len(products) >= 18
    assert products[0]["canonical_name"]


def test_parse_vnd_range():
    p = pc.parse_vnd_from_final_answer("Khoảng 8-9 triệu VND, đề xuất ~8.5 triệu.")
    assert p["estimated_min_vnd"] == 8_000_000
    assert p["estimated_max_vnd"] == 9_000_000
    assert p["suggested_vnd"] == 8_500_000


def test_append_market_observation_tmp_file():
    with tempfile.TemporaryDirectory() as tmp:
        src = pc.get_catalog_path()
        dest = Path(tmp) / "products_catalog.json"
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

        pc._catalog_cache = None
        pc._catalog_path = dest

        r = pc.append_market_observation(
            "iPhone 13 128GB",
            tier="good",
            estimated_min_vnd=8_000_000,
            estimated_max_vnd=9_000_000,
            suggested_vnd=8_500_000,
            source="test",
        )
        assert r["saved"] is True

        data = json.loads(dest.read_text(encoding="utf-8"))
        iphone = next(p for p in data["products"] if p["id"] == "iphone-13-128gb")
        assert len(iphone["market_observations"]) >= 1
        assert iphone["last_market_summary"]["suggested_vnd"] == 8_500_000

        pc._catalog_cache = None
        pc._catalog_path = None
