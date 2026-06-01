import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.product_catalog import get_reference_price, normalize_product


def test_normalize_iphone():
    r = normalize_product("iphone 13 128gb")
    assert r["matched"] is True
    assert "iPhone 13" in r["canonical_name"]


def test_reference_price():
    r = get_reference_price("iPhone 13 128GB")
    assert r["found"] is True
    assert r["reference_vnd"] > 0


def test_unknown_product():
    r = normalize_product("xyz unknown gadget 9000")
    assert r["matched"] is False
