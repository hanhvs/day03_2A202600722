"""Industry metrics: tokens, latency, cost (v2)."""
from __future__ import annotations

from typing import Any, Dict, List

from src.telemetry.logger import logger

# USD per 1M tokens (input, output) — lab estimates, update as needed
MODEL_PRICING = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-pro": (1.25, 5.00),
    "default": (1.00, 3.00),
}


class PerformanceTracker:
    def __init__(self) -> None:
        self.session_metrics: List[Dict[str, Any]] = []

    def track_request(
        self,
        provider: str,
        model: str,
        usage: Dict[str, int],
        latency_ms: int,
    ) -> Dict[str, Any]:
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage),
            "token_ratio": self._token_ratio(usage),
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)
        return metric

    def session_summary(self) -> Dict[str, Any]:
        if not self.session_metrics:
            return {"calls": 0}
        latencies = [m["latency_ms"] for m in self.session_metrics]
        return {
            "calls": len(self.session_metrics),
            "total_tokens": sum(m["total_tokens"] for m in self.session_metrics),
            "total_cost_usd": round(sum(m["cost_estimate"] for m in self.session_metrics), 4),
            "latency_ms_p50": sorted(latencies)[len(latencies) // 2],
            "latency_ms_max": max(latencies),
        }

    def _token_ratio(self, usage: Dict[str, int]) -> float:
        prompt = usage.get("prompt_tokens", 0) or 1
        completion = usage.get("completion_tokens", 0)
        return round(completion / prompt, 3)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        key = model if model in MODEL_PRICING else "default"
        in_rate, out_rate = MODEL_PRICING[key]
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        return (prompt * in_rate + completion * out_rate) / 1_000_000


tracker = PerformanceTracker()
