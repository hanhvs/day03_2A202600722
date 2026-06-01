import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.action_parser import parse_action, parse_final_answer, parse_tool_args


def test_parse_action():
    text = 'Thought: need price\nAction: normalize_product("iPhone 13 128GB")'
    a = parse_action(text)
    assert a == ("normalize_product", '"iPhone 13 128GB"')


def test_parse_final():
    text = "Thought: done\nFinal Answer: Khoảng 8–9 triệu VND."
    assert "8" in parse_final_answer(text)


def test_parse_kwargs():
    pos, kw = parse_tool_args('"iPhone 13 128GB", storage_gb=128')
    assert pos[0] == "iPhone 13 128GB"
    assert kw["storage_gb"] == 128
