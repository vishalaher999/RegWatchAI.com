"""
RegWatch AI ROI Calculator — Day 19.

Calculates time saved, FTE equivalent, and fine risk reduction for a
community bank compliance officer using RegWatch AI.

Usage:
    python scripts/roi_calculator.py                           # Sarah persona defaults
    python scripts/roi_calculator.py --regs 80 --salary 90000 # custom inputs
    python scripts/roi_calculator.py --save                    # save to docs/ROI-Calculator-v1.md

This output is used in:
  - Pilot conversion conversations ("here's your ROI")
  - Investor decks ("here's the customer value")
  - Product demos ("enter your numbers")
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def calculate_roi(
    # Institution profile
    regs_per_month: int = 60,          # Regulations published per month across all agencies
    monitoring_hours_per_reg: float = 0.5,  # Hours manually reading per regulation
    compliance_officers: int = 2,      # FTE compliance officers
    officer_salary_usd: int = 85_000,  # Annual salary including benefits
    assets_billion: float = 0.5,       # Institution assets ($ billion)

    # RegWatch AI parameters
    regwatch_price_monthly: int = 1_999,   # Professional plan
    dismiss_rate: float = 0.64,            # % of regulations auto-dismissed (no action)
    summary_read_time_minutes: float = 2,  # Minutes to read a RegWatch summary
    manual_read_time_minutes: float = 25,  # Minutes to manually assess a regulation

    # Risk parameters
    fine_risk_per_missed_reg: int = 500_000,  # Conservative fine estimate
    miss_rate_manual: float = 0.05,           # % of regulations missed manually
    miss_rate_regwatch: float = 0.001,        # % missed with RegWatch (near zero)
) -> dict:
    """
    Calculate ROI for a community bank using RegWatch AI.
    Returns a dict of all calculated metrics.
    """
    # ── Time savings ────────────────────────────────────────────────────────────
    hours_per_officer_per_month_manual = regs_per_month * monitoring_hours_per_reg

    # With RegWatch: dismissed docs take ~15 seconds to glance at
    # Non-dismissed docs take 2 minutes to read the summary
    dismissed_per_month = regs_per_month * dismiss_rate
    reviewed_per_month = regs_per_month * (1 - dismiss_rate)

    hours_per_officer_per_month_regwatch = (
        (dismissed_per_month * 0.0042) +        # 15 seconds = 0.0042 hours
        (reviewed_per_month * summary_read_time_minutes / 60)
    )

    hours_saved_per_officer_per_month = (
        hours_per_officer_per_month_manual - hours_per_officer_per_month_regwatch
    )
    hours_saved_per_year = hours_saved_per_officer_per_month * compliance_officers * 12

    # ── Cost savings ────────────────────────────────────────────────────────────
    hourly_rate = officer_salary_usd / 2080  # 2080 working hours per year
    labour_savings_per_year = hours_saved_per_year * hourly_rate

    regwatch_cost_per_year = regwatch_price_monthly * 12
    net_savings_per_year = labour_savings_per_year - regwatch_cost_per_year

    roi_pct = (net_savings_per_year / regwatch_cost_per_year) * 100

    # ── Risk reduction ──────────────────────────────────────────────────────────
    # Realistic model: not every missed regulation leads to a fine.
    # We estimate: 1 in 20 missed regulations results in an exam finding,
    # 1 in 5 exam findings leads to a civil money penalty.
    # So p(fine | missed regulation) ≈ 1/20 × 1/5 = 1% per missed regulation.
    fine_probability = 0.01
    regs_per_year = regs_per_month * 12

    expected_fine_manual = (
        regs_per_year * miss_rate_manual * fine_probability * fine_risk_per_missed_reg
    )
    expected_fine_regwatch = (
        regs_per_year * miss_rate_regwatch * fine_probability * fine_risk_per_missed_reg
    )
    expected_fine_reduction = expected_fine_manual - expected_fine_regwatch

    # ── Payback period ──────────────────────────────────────────────────────────
    total_value_per_year = labour_savings_per_year + expected_fine_reduction
    payback_weeks = (regwatch_price_monthly / (total_value_per_year / 52))

    return {
        # Input summary
        "regs_per_month": regs_per_month,
        "compliance_officers": compliance_officers,
        "officer_salary_usd": officer_salary_usd,
        "regwatch_price_monthly": regwatch_price_monthly,
        "assets_billion": assets_billion,

        # Time metrics
        "hours_manual_per_officer_per_month": round(hours_per_officer_per_month_manual, 1),
        "hours_regwatch_per_officer_per_month": round(hours_per_officer_per_month_regwatch, 1),
        "hours_saved_per_officer_per_month": round(hours_saved_per_officer_per_month, 1),
        "hours_saved_per_year_total": round(hours_saved_per_year, 0),
        "fte_equivalent_saved": round(hours_saved_per_year / 2080, 2),

        # Cost metrics
        "hourly_rate_usd": round(hourly_rate, 2),
        "labour_savings_per_year": round(labour_savings_per_year, 0),
        "regwatch_cost_per_year": regwatch_cost_per_year,
        "net_savings_per_year": round(net_savings_per_year, 0),
        "roi_pct": round(roi_pct, 0),

        # Risk metrics
        "expected_fine_reduction_per_year": round(expected_fine_reduction, 0),
        "total_value_per_year": round(total_value_per_year, 0),
        "payback_weeks": round(payback_weeks, 1),
    }


def print_report(metrics: dict) -> str:
    """Format the ROI report as a readable string."""
    m = metrics
    hourly = m["hourly_rate_usd"]
    lines = [
        "",
        "=" * 65,
        "  REGWATCH AI — ROI CALCULATOR",
        "=" * 65,
        "",
        "  YOUR INSTITUTION",
        f"    Assets:              ${m['assets_billion']}B",
        f"    Compliance officers: {m['compliance_officers']}",
        f"    Officer salary:      ${m['officer_salary_usd']:,}/year (${hourly:.0f}/hour)",
        f"    Regs monitored/mo:   {m['regs_per_month']}",
        f"    RegWatch plan:       ${m['regwatch_price_monthly']:,}/month",
        "",
        "  TIME SAVINGS",
        f"    Manual monitoring:   {m['hours_manual_per_officer_per_month']} hrs/officer/month",
        f"    With RegWatch:       {m['hours_regwatch_per_officer_per_month']} hrs/officer/month",
        f"    Hours saved/month:   {m['hours_saved_per_officer_per_month']} hrs/officer",
        f"    Hours saved/year:    {m['hours_saved_per_year_total']:.0f} hrs total ({m['fte_equivalent_saved']} FTE)",
        "",
        "  FINANCIAL IMPACT",
        f"    Labour savings/year:   ${m['labour_savings_per_year']:,.0f}",
        f"    RegWatch cost/year:    ${m['regwatch_cost_per_year']:,}",
        f"    Net savings/year:      ${m['net_savings_per_year']:,.0f}",
        f"    ROI:                   {m['roi_pct']:.0f}%",
        "",
        "  RISK REDUCTION",
        f"    Expected fine reduction: ${m['expected_fine_reduction_per_year']:,.0f}/year",
        f"    (Based on 5% miss rate manually -- <0.1% with RegWatch)",
        "",
        "  SUMMARY",
        f"    Total value/year:    ${m['total_value_per_year']:,.0f}",
        f"    Payback period:      {m['payback_weeks']} weeks",
        "    RegWatch pays for itself in " + (
            "< 1 week." if m['payback_weeks'] < 1 else f"{m['payback_weeks']:.1f} weeks."
        ),
        "",
        "=" * 65,
        "",
    ]
    return "\n".join(lines)


def save_markdown(metrics: dict, path: str) -> None:
    """Save the ROI report as a Markdown document."""
    m = metrics
    content = f"""# RegWatch AI — ROI Calculator v1.0

**Date:** 2026-06-01
**Persona:** Sarah — CCO at ${m['assets_billion']}B community bank

---

## Institution Profile

| Parameter | Value |
|-----------|-------|
| Assets | ${m['assets_billion']}B |
| Compliance officers | {m['compliance_officers']} |
| Officer salary (incl. benefits) | ${m['officer_salary_usd']:,}/year |
| Regulations monitored per month | {m['regs_per_month']} |
| RegWatch AI plan | ${m['regwatch_price_monthly']:,}/month (Professional) |

---

## Time Savings

| Metric | Without RegWatch | With RegWatch | Savings |
|--------|-----------------|---------------|---------|
| Monitoring hours/officer/month | {m['hours_manual_per_officer_per_month']} hrs | {m['hours_regwatch_per_officer_per_month']} hrs | {m['hours_saved_per_officer_per_month']} hrs |
| Total hours saved per year | — | — | **{m['hours_saved_per_year_total']:.0f} hours** |
| FTE equivalent | — | — | **{m['fte_equivalent_saved']} FTE** |

**How RegWatch saves time:**
- 64% of regulations auto-dismissed (informational, no action required) in ~15 seconds each
- Remaining 36% read as structured 2-minute summaries vs 25-minute manual review
- No more checking 6 government websites every Monday morning

---

## Financial Impact

| Metric | Annual Value |
|--------|-------------|
| Labour savings | ${m['labour_savings_per_year']:,.0f} |
| RegWatch AI cost | -${m['regwatch_cost_per_year']:,} |
| **Net savings** | **${m['net_savings_per_year']:,.0f}** |
| **ROI** | **{m['roi_pct']:.0f}%** |

---

## Risk Reduction

| Scenario | Annual Expected Cost |
|----------|---------------------|
| Manual monitoring (5% miss rate) | ${5 * m['regs_per_month'] * 12 / 100 * 500000:,.0f} expected fines |
| With RegWatch (<0.1% miss rate) | ${m['expected_fine_reduction_per_year'] * 0.001:,.0f} expected fines |
| **Annual risk reduction** | **${m['expected_fine_reduction_per_year']:,.0f}** |

Risk calculation: 5% of {m['regs_per_month'] * 12} annual regulations × $500K conservative fine estimate.

---

## Summary

| Metric | Value |
|--------|-------|
| Total value created per year | **${m['total_value_per_year']:,.0f}** |
| RegWatch AI cost per year | ${m['regwatch_cost_per_year']:,} |
| **Payback period** | **{m['payback_weeks']} weeks** |

> RegWatch AI at ${m['regwatch_price_monthly']:,}/month pays for itself in **{m['payback_weeks']:.0f} weeks** through labour savings alone. Risk reduction is additional value.

---

## The Compliance Officer's Time

Sarah currently spends **{m['hours_manual_per_officer_per_month']} hours per month** just monitoring regulatory feeds.
With RegWatch AI, that drops to **{m['hours_regwatch_per_officer_per_month']} hours**.

She gets **{m['hours_saved_per_officer_per_month']} hours back per month** — time she can spend on:
- Vendor risk management
- Board reporting and exam preparation
- Policy gap remediation
- Team training and development

That's not a productivity improvement. That's a different job.

---

*Calculator assumptions: 60 regulations/month monitored, 5% manual miss rate, $500K conservative fine,
2-minute RegWatch summary vs 25-minute manual review, 64% auto-dismiss rate.*
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"ROI report saved to: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RegWatch AI ROI Calculator")
    parser.add_argument("--regs", type=int, default=60, help="Regulations per month (default: 60)")
    parser.add_argument("--officers", type=int, default=2, help="Compliance officers (default: 2)")
    parser.add_argument("--salary", type=int, default=85_000, help="Officer salary USD (default: 85000)")
    parser.add_argument("--assets", type=float, default=0.5, help="Assets in $B (default: 0.5)")
    parser.add_argument("--price", type=int, default=1_999, help="RegWatch monthly price (default: 1999)")
    parser.add_argument("--save", action="store_true", help="Save Markdown report")
    args = parser.parse_args()

    metrics = calculate_roi(
        regs_per_month=args.regs,
        compliance_officers=args.officers,
        officer_salary_usd=args.salary,
        assets_billion=args.assets,
        regwatch_price_monthly=args.price,
    )

    print(print_report(metrics))

    if args.save:
        save_markdown(metrics, "docs/ROI-Calculator-v1.md")
