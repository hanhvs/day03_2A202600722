"""Parse ReAct Action / Final Answer from LLM output (@hanhvs H5)."""
import ast
import re
from typing import Any, Dict, List, Optional, Tuple

ACTION_PATTERN = re.compile(
    r"Action:\s*(\w+)\((.*)\)",
    re.IGNORECASE | re.DOTALL,
)
FINAL_ANSWER_PATTERN = re.compile(
    r"Final Answer:\s*(.+)",
    re.IGNORECASE | re.DOTALL,
)
THOUGHT_PATTERN = re.compile(
    r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)",
    re.IGNORECASE | re.DOTALL,
)


def parse_final_answer(text: str) -> Optional[str]:
    match = FINAL_ANSWER_PATTERN.search(text)
    if not match:
        return None
    return match.group(1).strip()


def parse_action(text: str) -> Optional[Tuple[str, str]]:
    """Return (tool_name, raw_args_string) or None."""
    match = ACTION_PATTERN.search(text)
    if not match:
        return None
    tool_name = match.group(1).strip()
    args_str = match.group(2).strip()
    # Trim trailing junk after closing paren balance
    depth = 0
    end = 0
    for i, ch in enumerate(args_str):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                end = i
                break
    if end:
        args_str = args_str[:end]
    return tool_name, args_str


def parse_thought(text: str) -> Optional[str]:
    match = THOUGHT_PATTERN.search(text)
    return match.group(1).strip() if match else None


def parse_tool_args(args_str: str) -> Tuple[List[Any], Dict[str, Any]]:
    args_str = args_str.strip()
    if not args_str:
        return [], {}
    try:
        node = ast.parse(f"wrapper({args_str})", mode="eval")
        call = node.body  # type: ignore[attr-defined]
        if not isinstance(call, ast.Call):
            return [ast.literal_eval(node.body)], {}  # type: ignore[arg-type]
        pos = [ast.literal_eval(a) for a in call.args]
        kw = {k.arg: ast.literal_eval(k.value) for k in call.keywords if k.arg}
        return pos, kw
    except (SyntaxError, ValueError):
        m = re.match(r'^["\'](.+?)["\']\s*$', args_str, re.DOTALL)
        if m:
            return [m.group(1)], {}
        return [args_str.strip('"').strip()], {}
