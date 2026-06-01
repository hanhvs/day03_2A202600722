"""Parse JSON logs for evaluation dashboard (v2)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def parse_log_file(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def summarize(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    llm_metrics = [e for e in events if e.get("event") == "LLM_METRIC"]
    agent_starts = [e for e in events if e.get("event") == "AGENT_START"]
    tool_errors = [e for e in events if e.get("event") == "TOOL_ERROR"]
    agent_ends = [e for e in events if e.get("event") == "AGENT_END"]

    latencies = [m["data"].get("latency_ms", 0) for m in llm_metrics]
    tokens = [m["data"].get("total_tokens", 0) for m in llm_metrics]
    costs = [m["data"].get("cost_estimate", 0) for m in llm_metrics]

    return {
        "runs": len(agent_starts),
        "llm_calls": len(llm_metrics),
        "tool_errors": len(tool_errors),
        "completed": sum(1 for e in agent_ends if e.get("data", {}).get("status") == "final_answer"),
        "latency_ms": {
            "p50": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "max": max(latencies) if latencies else 0,
        },
        "tokens_total": sum(tokens),
        "cost_estimate_usd": round(sum(costs), 4),
    }


def main() -> None:
    log_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("logs")
    files = sorted(log_dir.glob("*.log"))
    if not files:
        print("No log files in", log_dir)
        return
    for f in files:
        summary = summarize(parse_log_file(f))
        print(f"\n=== {f.name} ===")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
