"""
Cost dashboard (Day 44, KM #239 -- cost ($/query) tracking).

Computes $/query and total LLM spend from AuditLog(SUMMARISE) rows written
by src/f2_summarise/summariser.py. Each SUMMARISE row's payload_json carries
"model", "input_tokens", and "output_tokens" (Day 44 addition to
_call_claude / summarise_document).

Pricing is hardcoded per-model ($ per million tokens, published Anthropic
list pricing as of this build). If pricing changes, update PRICING_PER_MTOK
below -- there is deliberately no live pricing API call.

v1 only covers F2 (the only feature that calls the Anthropic API per
document). F3's reranker and F4's LangGraph agent do not currently log
token usage -- see "Key limitation noted" in docs/ARCHITECTURE.md.

Run: python -m scripts.cost_dashboard
"""

import json
import sys
from collections import defaultdict

from sqlmodel import select

from src.database import get_session
from src.models import AuditAction, AuditLog

# $ per million tokens: (input, output)
PRICING_PER_MTOK = {
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}


def _cost_for_tokens(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = PRICING_PER_MTOK.get(model, (0.0, 0.0))
    return (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price


def compute_cost_report() -> dict:
    with get_session() as session:
        logs = session.exec(
            select(AuditLog).where(AuditLog.action == AuditAction.SUMMARISE)
        ).all()

    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    queries_with_tokens = 0
    by_model = defaultdict(lambda: {"queries": 0, "input_tokens": 0, "output_tokens": 0, "cost": 0.0})

    for log in logs:
        payload = json.loads(log.payload_json) if log.payload_json else {}
        model = payload.get("model")
        input_tokens = payload.get("input_tokens", 0) or 0
        output_tokens = payload.get("output_tokens", 0) or 0

        if not model or (input_tokens == 0 and output_tokens == 0):
            # Pre-Day-44 SUMMARISE rows have no token counts -- skip rather
            # than counting them as $0 queries (would understate $/query).
            continue

        cost = _cost_for_tokens(model, input_tokens, output_tokens)

        total_cost += cost
        total_input_tokens += input_tokens
        total_output_tokens += output_tokens
        queries_with_tokens += 1

        by_model[model]["queries"] += 1
        by_model[model]["input_tokens"] += input_tokens
        by_model[model]["output_tokens"] += output_tokens
        by_model[model]["cost"] += cost

    cost_per_query = (total_cost / queries_with_tokens) if queries_with_tokens else 0.0

    return {
        "total_summarise_logs": len(logs),
        "queries_with_token_data": queries_with_tokens,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "total_cost_usd": round(total_cost, 4),
        "cost_per_query_usd": round(cost_per_query, 4),
        "by_model": {
            model: {
                "queries": stats["queries"],
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
                "cost_usd": round(stats["cost"], 4),
            }
            for model, stats in by_model.items()
        },
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")

    report = compute_cost_report()

    print("Cost Dashboard ($/query)")
    print("=" * 40)
    print(f"SUMMARISE log entries:      {report['total_summarise_logs']}")
    print(f"  with token data:          {report['queries_with_token_data']}")
    print(f"Total input tokens:         {report['total_input_tokens']:,}")
    print(f"Total output tokens:        {report['total_output_tokens']:,}")
    print(f"Total cost (USD):           ${report['total_cost_usd']:.4f}")
    print(f"Cost per query (USD):       ${report['cost_per_query_usd']:.4f}")
    print()
    print("By model:")
    if report["by_model"]:
        for model, stats in report["by_model"].items():
            print(f"  {model}")
            print(f"    queries:        {stats['queries']}")
            print(f"    input tokens:   {stats['input_tokens']:,}")
            print(f"    output tokens:  {stats['output_tokens']:,}")
            print(f"    cost (USD):     ${stats['cost_usd']:.4f}")
    else:
        print("  (none -- no SUMMARISE rows have token data yet)")
        print("  Token tracking was added Day 44; only documents summarised")
        print("  on/after Day 44 will have input_tokens/output_tokens.")


if __name__ == "__main__":
    main()
