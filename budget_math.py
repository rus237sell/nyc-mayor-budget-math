"""Do the mayor's affordability pledges add up? NYC FY2027 edition.

Compares the headline campaign pledges' published cost estimates against the
campaign's own revenue proposals and the city's enacted FY2027 budget.

All inputs are labeled estimates from published reporting (campaign claims and
independent analyst ranges), NOT enacted budget lines. The point is to test the
campaign's arithmetic on its own terms, not to assert what the city will spend.
"""

import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Sourced inputs (all $ in millions per year, FY2027 unless noted).
# Sources listed in SOURCES.md.
# ---------------------------------------------------------------------------
ADOPTED_BUDGET_FY27 = 125_800          # enacted FY2027 operating budget, $M
FY27_GAP_BEFORE_CLOSING = 5_400        # two-year gap figure reported at prelim, $M
NYC_HOUSEHOLDS = 3.1e6                 # approx households, for per-household framing

# Pledge costs: (low, high) estimates in $M/yr.
# Low = campaign's own figure; high = top of published analyst range.
# kind: "operating" (recurring budget pressure), "capital" (one-time/infra
# run-rate, not comparable to annual operating revenue), or "none" (no
# direct budget cost).
PLEDGES = [
    # (label, low, high, kind, note)
    ("Fare-free buses", 700, 800, "operating",
     "Campaign cited ~$700M/yr lost fare revenue; analysts up to ~$800M."),
    ("Universal childcare (6wk-5yr)", 5_900, 12_700, "operating",
     "Campaign estimate ~$5.9B; independent analyses range $2.5B-$12.7B."),
    ("City-owned grocery stores", 60, 60, "operating",
     "Campaign pilot: ~$60M/yr."),
    ("Dept. of Community Safety", 1_100, 1_100, "operating",
     "Campaign budgeted ~$1.1B/yr."),
    ("Rent freeze (rent-stabilized)", 0, 0, "none",
     "No direct budget cost; cost borne by landlords via forgone rent."),
    ("200k affordable units / 10 yrs", 10_000, 10_000, "capital",
     "Campaign: $100B over 10 years => ~$10B/yr run rate (mostly capital)."),
]

REVENUE = [
    # (label, estimate $M/yr, albany_required, note)
    ("Corp tax 7.5% -> 11.5%", 5_000, True,
     "Campaign estimate; requires Albany approval."),
    ("2% income tax on $1M+ earners", 4_000, True,
     "Campaign estimate; requires Albany approval."),
    ("Fines/waste collection", 1_000, False,
     "Campaign estimate."),
]


def annual_costs(kind=None):
    """(low, high) $M/yr summed over pledges, optionally filtered by kind."""
    items = [p for p in PLEDGES if kind is None or p[3] == kind]
    low = sum(p[1] for p in items)
    high = sum(p[2] for p in items)
    return low, high


def proposed_revenue(albany_required=None):
    """Total pledged revenue, optionally filtered by Albany-approval need."""
    items = [r for r in REVENUE if albany_required is None or r[2] == albany_required]
    return sum(r[1] for r in items)


def albany_outcome_totals():
    """(label, total pledged revenue $M) for each Albany outcome.

    City-controlled revenue (the fines/waste line) is in every total; the
    Albany lines are added only in the outcomes where Albany approves them.
    """
    city = proposed_revenue(albany_required=False)
    albany = {r[0]: r[1] for r in REVENUE if r[2]}
    corp = next(v for k, v in albany.items() if k.startswith("Corp tax"))
    income = next(v for k, v in albany.items() if "income tax" in k)
    return [
        ("Both Albany taxes approved", city + corp + income),
        ("Corp tax only", city + corp),
        ("Income tax only", city + income),
        ("Neither Albany tax approved", city),
    ]


def joint_sensitivity_rows(realization_cases=(100, 75, 50, 25)):
    """Albany outcome x revenue realization grid, operating-only costs.

    v3 tested Albany approval on its own and v5 tested realization on its
    own; the two risks can land together, so cross them: each Albany
    outcome's pledged total is collected at each realization rate and
    compared with operating-only costs. The break-even realization for an
    outcome is operating cost (campaign figure) over its pledged total --
    above 100% it is unreachable even if the approved taxes collect in
    full.
    """
    op_low, op_high = annual_costs(kind="operating")
    rows = []
    for label, base in albany_outcome_totals():
        breakeven = round(op_low / base * 100, 1)
        for pct in realization_cases:
            realized = base * pct // 100
            rows.append({
                "albany_outcome": label,
                "pledged_revenue_$M": base,
                "realization_%": pct,
                "realized_revenue_$M": realized,
                "coverage_of_operating_low_%": round(realized / op_low * 100, 1),
                "coverage_of_operating_high_%": round(realized / op_high * 100, 1),
                "gap_vs_operating_low_$M": realized - op_low,
                "covers_operating_low": "Yes" if realized >= op_low else "No",
                "breakeven_realization_%": breakeven,
                "note": (f"Break-even realization for this Albany outcome is "
                         f"{breakeven}% of its pledged total"
                         + (" (above 100%, so unreachable)."
                            if breakeven > 100 else ".")),
            })
    return rows


def childcare_case_list():
    """(label, childcare cost $M) across the full published range.

    Same four cases as the v4 sensitivity: analyst low ($2.5B, SOURCES.md),
    the campaign figure, the midpoint of the published range, and the
    analyst high.
    """
    childcare = next(p for p in PLEDGES if p[0].startswith("Universal childcare"))
    return [
        ("Analyst low", 2_500),
        ("Campaign figure", childcare[1]),
        ("Midpoint of published range", (2_500 + childcare[2]) // 2),
        ("Analyst high", childcare[2]),
    ]


def childcare_albany_rows():
    """Childcare cost x Albany outcome grid, operating-only costs.

    v4 varied childcare against the full pledged revenue and v3 varied
    Albany approval at campaign-figure costs; cross them: each childcare
    case's total operating cost (other operating pledges held at campaign
    figures) against each Albany outcome's revenue total. The break-even
    childcare cost for an outcome is its revenue minus the other operating
    pledges -- it can go negative, meaning that outcome cannot cover even
    the non-childcare operating pledges on its own.
    """
    op_low, _ = annual_costs(kind="operating")
    childcare = next(p for p in PLEDGES if p[0].startswith("Universal childcare"))
    other_operating = op_low - childcare[1]
    rows = []
    for label, total_rev in albany_outcome_totals():
        breakeven = total_rev - other_operating
        for case_label, cc_cost in childcare_case_list():
            total_op = other_operating + cc_cost
            rows.append({
                "albany_outcome": label,
                "total_revenue_$M": total_rev,
                "childcare_case": case_label,
                "childcare_cost_$M": cc_cost,
                "other_operating_$M": other_operating,
                "total_operating_$M": total_op,
                "coverage_%": round(total_rev / total_op * 100, 1),
                "gap_$M": total_rev - total_op,
                "covers_operating": "Yes" if total_rev >= total_op else "No",
                "breakeven_childcare_$M": breakeven,
                "note": (f"Break-even childcare cost for this Albany outcome "
                         f"is ${breakeven/1000:.2f}B"
                         + (" (negative: this revenue cannot cover even the "
                            "non-childcare operating pledges)."
                            if breakeven < 0 else ".")),
            })
    return rows


def main():
    cost_low, cost_high = annual_costs()
    revenue = proposed_revenue()

    # ---- new cut: operating-only costs vs Albany-dependency of revenue ----
    op_low, op_high = annual_costs(kind="operating")
    revenue_albany = proposed_revenue(albany_required=True)
    revenue_city = proposed_revenue(albany_required=False)

    scenario_rows = [
        {"scenario": "All pledges, campaign-figure costs",
         "cost_low_$M": cost_low, "cost_high_$M": cost_high,
         "revenue_$M": revenue,
         "coverage_low_%": round(revenue / cost_low * 100, 1),
         "coverage_high_%": round(revenue / cost_high * 100, 1),
         "note": "Baseline comparison."},
        {"scenario": "Operating-only pledges, campaign-figure costs",
         "cost_low_$M": op_low, "cost_high_$M": op_high,
         "revenue_$M": revenue,
         "coverage_low_%": round(revenue / op_low * 100, 1),
         "coverage_high_%": round(revenue / op_high * 100, 1),
         "note": "Excludes $100B/10-yr housing capital plan (not operating)."},
        {"scenario": "Operating-only pledges vs Albany-independent revenue only",
         "cost_low_$M": op_low, "cost_high_$M": op_high,
         "revenue_$M": revenue_city,
         "coverage_low_%": round(revenue_city / op_low * 100, 1),
         "coverage_high_%": round(revenue_city / op_high * 100, 1),
         "note": (f"City-controlled revenue is only the fines/waste line "
                   f"(${revenue_city/1000:.0f}B); the other "
                   f"${revenue_albany/1000:.0f}B needs Albany approval.")},
    ]
    scenario_path = os.path.join(HERE, "scenarios.csv")
    with open(scenario_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(scenario_rows[0].keys()))
        w.writeheader()
        w.writerows(scenario_rows)

    # ---- v3 cut: Albany partial-approval sensitivity (operating-only) ----
    # v2 treated Albany as all-or-nothing. In practice Albany could approve
    # one tax and not the other, so test each combination against the
    # operating-only cost range. City-controlled revenue is in every case.
    albany_items = {r[0]: r[1] for r in REVENUE if r[2]}
    corp_tax = next(v for k, v in albany_items.items() if k.startswith("Corp tax"))
    income_tax = next(v for k, v in albany_items.items() if "income tax" in k)
    albany_outcomes = [
        ("Both Albany taxes approved", corp_tax + income_tax),
        ("Corp tax only", corp_tax),
        ("Income tax only", income_tax),
        ("Neither Albany tax approved", 0),
    ]
    sensitivity_rows = []
    for label, albany_rev in albany_outcomes:
        total_rev = revenue_city + albany_rev
        sensitivity_rows.append({
            "albany_outcome": label,
            "albany_revenue_$M": albany_rev,
            "total_revenue_$M": total_rev,
            "coverage_of_operating_low_%": round(total_rev / op_low * 100, 1),
            "coverage_of_operating_high_%": round(total_rev / op_high * 100, 1),
            "gap_vs_operating_low_$M": total_rev - op_low,
            "gap_vs_operating_high_$M": total_rev - op_high,
            "note": ("Operating-only costs only; housing capital plan excluded."
                     if label != "Both Albany taxes approved" else
                     "Baseline Albany outcome from scenarios.csv."),
        })
    sensitivity_path = os.path.join(HERE, "sensitivity.csv")
    with open(sensitivity_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sensitivity_rows[0].keys()))
        w.writeheader()
        w.writerows(sensitivity_rows)

    # Childcare is the swing item: its low-high range alone is almost the
    # entire width of the operating cost range.
    childcare = next(p for p in PLEDGES if p[0].startswith("Universal childcare"))
    childcare_swing = childcare[2] - childcare[1]
    operating_swing = op_high - op_low

    # ---- v4 cut: childcare cost sensitivity (operating-only) ----
    # v3 showed childcare drives the operating range, so test it across its
    # full published range ($2.5B analyst low in SOURCES.md to $12.7B high),
    # holding the other operating pledges at their campaign figures. The
    # break-even childcare cost is pledged revenue minus those other costs:
    # above it, even full pledged revenue cannot cover operating pledges.
    other_operating = op_low - childcare[1]
    childcare_cases = [
        ("Analyst low", 2_500),
        ("Campaign figure", childcare[1]),
        ("Midpoint of published range", (2_500 + childcare[2]) // 2),
        ("Analyst high", childcare[2]),
    ]
    breakeven_childcare = revenue - other_operating
    childcare_rows = []
    for label, cc_cost in childcare_cases:
        total_op = other_operating + cc_cost
        childcare_rows.append({
            "childcare_case": label,
            "childcare_cost_$M": cc_cost,
            "other_operating_$M": other_operating,
            "total_operating_$M": total_op,
            "coverage_full_pledged_%": round(revenue / total_op * 100, 1),
            "coverage_city_only_%": round(revenue_city / total_op * 100, 1),
            "gap_vs_full_pledged_$M": revenue - total_op,
            "childcare_share_of_operating_%": round(cc_cost / total_op * 100, 1),
            "note": (f"Other operating pledges held at campaign figures "
                     f"(${other_operating/1000:.2f}B); full pledged revenue "
                     f"${revenue/1000:.0f}B, city-controlled ${revenue_city/1000:.0f}B."),
        })
    childcare_path = os.path.join(HERE, "childcare_sensitivity.csv")
    with open(childcare_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(childcare_rows[0].keys()))
        w.writeheader()
        w.writerows(childcare_rows)

    # ---- v5 cut: revenue realization sensitivity ----
    # Costs carry a low-high range in this model but revenue is a single
    # campaign point estimate ($10B). Test what happens if the pledged
    # taxes collect less than estimated: realized revenue at 100/75/50/25%
    # of the campaign figure, against operating-only and total costs. The
    # break-even realization rate is the share of pledged revenue that
    # must actually materialize to cover a given cost level.
    realization_cases = [100, 75, 50, 25]
    breakeven_op_low = round(op_low / revenue * 100, 1)
    breakeven_op_high = round(op_high / revenue * 100, 1)
    breakeven_total_low = round(cost_low / revenue * 100, 1)
    revenue_rows = []
    for pct in realization_cases:
        realized = revenue * pct // 100
        revenue_rows.append({
            "realization_%": pct,
            "realized_revenue_$M": realized,
            "coverage_of_operating_low_%": round(realized / op_low * 100, 1),
            "coverage_of_operating_high_%": round(realized / op_high * 100, 1),
            "coverage_of_total_low_%": round(realized / cost_low * 100, 1),
            "gap_vs_operating_low_$M": realized - op_low,
            "note": (f"Break-even realization: {breakeven_op_low}% of pledged "
                     f"revenue covers operating costs at campaign figures; "
                     f"{breakeven_op_high}% would be needed at analyst high "
                     f"and {breakeven_total_low}% for all pledges at "
                     f"campaign figures (both above 100%, so unreachable)."),
        })
    revenue_path = os.path.join(HERE, "revenue_sensitivity.csv")
    with open(revenue_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(revenue_rows[0].keys()))
        w.writeheader()
        w.writerows(revenue_rows)

    # ---- v6 cut: joint Albany x realization sensitivity ----
    # v3 and v5 each varied one revenue risk at a time. Cross them: a
    # partial Albany approval that also under-collects is the realistic
    # downside, and no single-axis table shows how few combinations cover
    # even campaign-figure operating costs.
    joint_rows = joint_sensitivity_rows(realization_cases)
    joint_path = os.path.join(HERE, "joint_sensitivity.csv")
    with open(joint_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(joint_rows[0].keys()))
        w.writeheader()
        w.writerows(joint_rows)
    joint_covering = [r for r in joint_rows
                      if r["covers_operating_low"] == "Yes"]

    # ---- v7 cut: childcare cost x Albany outcome sensitivity ----
    # v6 crossed the two revenue risks; this crosses the biggest cost
    # risk (childcare's $2.5B-$12.7B range) against the revenue risk
    # (Albany approval). A partial Albany win that looks workable at
    # campaign-figure childcare may fail at the midpoint of the range.
    cc_albany_rows = childcare_albany_rows()
    cc_albany_path = os.path.join(HERE, "childcare_albany.csv")
    with open(cc_albany_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cc_albany_rows[0].keys()))
        w.writeheader()
        w.writerows(cc_albany_rows)
    cc_albany_covering = [r for r in cc_albany_rows
                          if r["covers_operating"] == "Yes"]

    fig5, ax5 = plt.subplots(figsize=(8, 3.8))
    rev_labels = [f"{r['realization_%']}%" for r in revenue_rows]
    rev_vals = [r["realized_revenue_$M"] / 1000 for r in revenue_rows]
    bars = ax5.bar(rev_labels, rev_vals, color="#1f4e79")
    for b, v in zip(bars, rev_vals):
        ax5.text(b.get_x() + b.get_width() / 2, v + 0.3, f"${v:.1f}B",
                 ha="center", va="bottom", fontsize=10)
    ax5.axhline(op_low / 1000, color="#b00020", linestyle="--", linewidth=1.5,
                label=f"Operating costs, campaign figure: ${op_low/1000:.1f}B")
    ax5.axhline(op_high / 1000, color="#7fa8c9", linestyle="--",
                linewidth=1.5,
                label=f"Operating costs, analyst high: ${op_high/1000:.1f}B")
    ax5.set_ylim(0, max(op_high / 1000, max(rev_vals)) * 1.18)
    ax5.set_xlabel("Share of pledged revenue actually collected")
    ax5.set_ylabel("Realized revenue ($B)")
    ax5.set_title("Pledged revenue at 100/75/50/25% realization\n"
                  "vs. operating-only pledge costs")
    ax5.legend(loc="upper right", fontsize=8)
    fig5.tight_layout()
    fig5.savefig(os.path.join(HERE, "results_revenue.png"), dpi=120)
    plt.close(fig5)

    # Heatmap of the joint grid: coverage of campaign-figure operating
    # costs (%) by Albany outcome (rows) x realization rate (columns).
    outcome_labels = [label for label, _ in albany_outcome_totals()]
    grid = [[next(r["coverage_of_operating_low_%"] for r in joint_rows
                  if r["albany_outcome"] == label
                  and r["realization_%"] == pct)
             for pct in realization_cases]
            for label in outcome_labels]
    fig6, ax6 = plt.subplots(figsize=(8, 4.2))
    im = ax6.imshow(grid, cmap="RdYlGn", vmin=0, vmax=130)
    ax6.set_xticks(range(len(realization_cases)))
    ax6.set_xticklabels([f"{p}% realized" for p in realization_cases])
    ax6.set_yticks(range(len(outcome_labels)))
    ax6.set_yticklabels([label.replace(" approved", "")
                         for label in outcome_labels], fontsize=9)
    for i, row in enumerate(grid):
        for j, v in enumerate(row):
            ax6.text(j, i, f"{v:.1f}%", ha="center", va="center",
                     fontsize=10, color="black" if v < 115 else "white")
    ax6.set_title("Coverage of campaign-figure operating costs ($7.8B)\n"
                  "by Albany outcome and revenue realization")
    fig6.colorbar(im, ax=ax6, label="Coverage (%)")
    fig6.tight_layout()
    fig6.savefig(os.path.join(HERE, "results_joint.png"), dpi=120)
    plt.close(fig6)

    # Heatmap of the childcare x Albany grid: coverage (%) of total
    # operating costs by Albany outcome (rows) x childcare case (columns).
    cc_case_labels = [label for label, _ in childcare_case_list()]
    cc_grid = [[next(r["coverage_%"] for r in cc_albany_rows
                     if r["albany_outcome"] == label
                     and r["childcare_case"] == case)
                for case in cc_case_labels]
               for label in outcome_labels]
    fig7, ax7 = plt.subplots(figsize=(8, 4.2))
    im7 = ax7.imshow(cc_grid, cmap="RdYlGn", vmin=0, vmax=230)
    ax7.set_xticks(range(len(cc_case_labels)))
    ax7.set_xticklabels([f"{label}\n(${cost/1000:.1f}B)"
                         for label, cost in childcare_case_list()], fontsize=9)
    ax7.set_yticks(range(len(outcome_labels)))
    ax7.set_yticklabels([label.replace(" approved", "")
                         for label in outcome_labels], fontsize=9)
    for i, row in enumerate(cc_grid):
        for j, v in enumerate(row):
            ax7.text(j, i, f"{v:.1f}%", ha="center", va="center",
                     fontsize=10, color="black" if v < 200 else "white")
    ax7.set_title("Coverage of operating costs by Albany outcome\n"
                  "and childcare cost case (other pledges at campaign figures)")
    fig7.colorbar(im7, ax=ax7, label="Coverage (%)")
    fig7.tight_layout()
    fig7.savefig(os.path.join(HERE, "results_childcare_albany.png"), dpi=120)
    plt.close(fig7)

    fig4, ax4 = plt.subplots(figsize=(8, 3.8))
    cc_labels = [r["childcare_case"] for r in childcare_rows]
    cc_totals = [r["total_operating_$M"] / 1000 for r in childcare_rows]
    bars = ax4.bar(cc_labels, cc_totals, color="#1f4e79")
    for b, v in zip(bars, cc_totals):
        ax4.text(b.get_x() + b.get_width() / 2, v + 0.3, f"${v:.1f}B",
                 ha="center", va="bottom", fontsize=10)
    ax4.axhline(revenue / 1000, color="#b00020", linestyle="--", linewidth=1.5,
                label=f"Full pledged revenue: ${revenue/1000:.0f}B")
    ax4.axhline(revenue_city / 1000, color="#7fa8c9", linestyle="--",
                linewidth=1.5,
                label=f"City-controlled revenue only: ${revenue_city/1000:.0f}B")
    ax4.set_ylim(0, max(cc_totals) * 1.22)
    ax4.set_ylabel("Total operating pledge costs ($B)")
    ax4.set_title("Operating costs by childcare cost case\n"
                  "(other operating pledges at campaign figures)")
    ax4.legend(loc="upper left", fontsize=8)
    fig4.tight_layout()
    fig4.savefig(os.path.join(HERE, "results_childcare.png"), dpi=120)
    plt.close(fig4)

    fig3, ax3 = plt.subplots(figsize=(8, 3.8))
    sens_labels = [r["albany_outcome"].replace(" approved", "")
                   for r in sensitivity_rows]
    sens_rev = [r["total_revenue_$M"] / 1000 for r in sensitivity_rows]
    bars = ax3.barh(sens_labels[::-1], sens_rev[::-1], color="#1f4e79")
    for b, v in zip(bars, sens_rev[::-1]):
        ax3.text(v + 0.15, b.get_y() + b.get_height() / 2, f"${v:.0f}B",
                 va="center", fontsize=10)
    ax3.axvline(op_low / 1000, color="#b00020", linestyle="--", linewidth=1.5,
                label=f"Operating costs, campaign figure: ${op_low/1000:.1f}B")
    ax3.axvline(op_high / 1000, color="#7fa8c9", linestyle="--", linewidth=1.5,
                label=f"Operating costs, analyst high: ${op_high/1000:.1f}B")
    ax3.set_xlim(0, max(op_high / 1000, max(sens_rev)) * 1.18)
    ax3.set_xlabel("Annual revenue ($B)")
    ax3.set_title("Operating-only pledges: revenue by Albany outcome\n"
                  "(city-controlled $1B included in every bar)")
    ax3.legend(loc="lower right", fontsize=8)
    fig3.tight_layout()
    fig3.savefig(os.path.join(HERE, "results_sensitivity.png"), dpi=120)
    plt.close(fig3)

    # ---- new chart: operating-only costs vs city-controlled revenue ----
    fig2, ax2 = plt.subplots(figsize=(8, 3.4))
    cats = ["Operating pledge costs\n(campaign figure)", "Operating pledge costs\n(analyst high)",
            "City-controlled revenue\n(fines/waste)"]
    vals = [op_low / 1000, op_high / 1000, revenue_city / 1000]
    colors = ["#1f4e79", "#7fa8c9", "#b00020"]
    bars = ax2.bar(cats, vals, color=colors)
    for b, v in zip(bars, vals):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.15, f"${v:.1f}B",
                 ha="center", va="bottom", fontsize=10)
    ax2.set_ylim(0, max(vals) * 1.25)
    ax2.set_ylabel("Annual $B")
    ax2.set_title("Operating-only pledges vs revenue the city can control\n"
                  "(estimates, not enacted spending)")
    fig2.tight_layout()
    fig2.savefig(os.path.join(HERE, "results_operating.png"), dpi=120)
    plt.close(fig2)

    rows = []
    for label, low, high, kind, note in PLEDGES:
        rows.append({
            "item": label,
            "kind": kind,
            "cost_low_$M": low,
            "cost_high_$M": high,
            "mid_$M": (low + high) / 2,
            "share_of_FY27_budget_%": round(((low + high) / 2) / ADOPTED_BUDGET_FY27 * 100, 2),
            "note": note,
        })

    os.makedirs(HERE, exist_ok=True)
    csv_path = os.path.join(HERE, "results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- chart: pledge costs (low-high range) vs pledged revenue ----
    labels = [p[0].split(" (")[0] for p in PLEDGES]
    lows = [p[1] / 1000 for p in PLEDGES]          # $B
    highs = [p[2] / 1000 for p in PLEDGES]
    mids = [(p[1] + p[2]) / 2 / 1000 for p in PLEDGES]

    fig, ax = plt.subplots(figsize=(10, 5.2))
    y = range(len(labels))
    ax.barh(list(y), highs, color="#c9c9c9", label="High estimate")
    ax.barh(list(y), lows, color="#1f4e79", label="Campaign figure")
    for i, h in enumerate(highs):
        ax.text(h + 0.3, i, f"${h:.1f}B", va="center", ha="left", fontsize=9)
    ax.axvline(revenue / 1000, color="#b00020", linestyle="--", linewidth=1.5,
               label=f"Pledged new revenue: ${revenue/1000:.0f}B/yr")
    ax.set_xlim(0, max(highs) * 1.18)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("Annual cost ($B)")
    ax.set_title("NYC: pledged program costs (campaign figure vs analyst high)\n"
                 "vs. pledged new revenue — estimates, not enacted spending")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "results.png"), dpi=120)
    plt.close(fig)

    # ---- printed findings ----
    print(f"Adopted FY2027 NYC budget:        ${ADOPTED_BUDGET_FY27/1000:.1f}B")
    print(f"Total pledged program cost range: ${cost_low/1000:.1f}B - ${cost_high/1000:.1f}B/yr")
    print(f"Pledged new revenue:             ${revenue/1000:.0f}B/yr")
    print()
    for scenario, cost in (("campaign-figure costs", cost_low),
                           ("analyst-high costs", cost_high)):
        gap = revenue - cost
        print(f"{scenario}: revenue {'covers' if gap >= 0 else 'short by'} "
              f"${abs(gap)/1000:.1f}B "
              f"({'surplus' if gap >= 0 else 'deficit'} {abs(gap)/revenue*100:.0f}% of pledged revenue)")
    print()
    print(f"Pledges as share of FY27 budget: {cost_low/ADOPTED_BUDGET_FY27*100:.1f}% - "
          f"{cost_high/ADOPTED_BUDGET_FY27*100:.1f}%")
    print(f"Reported gap being closed (FY27): ${FY27_GAP_BEFORE_CLOSING/1000:.1f}B "
          f"({FY27_GAP_BEFORE_CLOSING/ADOPTED_BUDGET_FY27*100:.1f}% of budget)")
    print(f"Mid-estimate pledge cost per NYC household: "
          f"${(cost_low + cost_high)/2*1e6/NYC_HOUSEHOLDS:,.0f}/yr")
    print()
    print("Albany dependency: the two biggest revenue items (corp tax + income surcharge,")
    print(f"${(5000+4000)/1000:.0f}B of the ${revenue/1000:.0f}B) require state approval.")
    print()
    print("--- Operating-only cut (excludes $100B/10-yr housing capital plan) ---")
    print(f"Operating pledge costs:              ${op_low/1000:.1f}B - ${op_high/1000:.1f}B/yr")
    print(f"City-controlled revenue (no Albany): ${revenue_city/1000:.0f}B/yr")
    op_gap = revenue_city - op_low
    print(f"Operating programs vs city-controlled revenue alone: short by "
          f"${abs(op_gap)/1000:.1f}B on campaign figures "
          f"(covers {revenue_city/op_low*100:.0f}% of operating costs)")
    print(f"Albany-dependent share of pledged revenue: "
          f"{revenue_albany/revenue*100:.0f}% "
          f"(${revenue_albany/1000:.0f}B of ${revenue/1000:.0f}B)")
    print(f"Operating cost per NYC household: "
          f"${(op_low + op_high)/2*1e6/NYC_HOUSEHOLDS:,.0f}/yr (mid estimate)")
    print()
    print("--- Albany partial-approval sensitivity (operating-only) ---")
    for r in sensitivity_rows:
        print(f"{r['albany_outcome']}: ${r['total_revenue_$M']/1000:.0f}B revenue "
              f"covers {r['coverage_of_operating_low_%']:.0f}% of campaign-figure "
              f"operating costs, {r['coverage_of_operating_high_%']:.0f}% at analyst high")
    print(f"Childcare swing: ${childcare_swing/1000:.1f}B low-to-high is "
          f"{childcare_swing/operating_swing*100:.0f}% of the "
          f"${operating_swing/1000:.1f}B operating cost range — "
          f"one pledge drives nearly all the uncertainty.")
    print()
    print("--- Childcare cost sensitivity (operating-only) ---")
    for r in childcare_rows:
        print(f"{r['childcare_case']}: childcare ${r['childcare_cost_$M']/1000:.1f}B "
              f"-> operating ${r['total_operating_$M']/1000:.1f}B; full pledged "
              f"revenue covers {r['coverage_full_pledged_%']:.0f}%, "
              f"city-controlled only {r['coverage_city_only_%']:.0f}%")
    print(f"Break-even childcare cost: ${breakeven_childcare/1000:.2f}B — above "
          f"that, even the full ${revenue/1000:.0f}B pledged revenue cannot "
          f"cover the operating pledges.")
    print()
    print("--- Revenue realization sensitivity ---")
    for r in revenue_rows:
        print(f"{r['realization_%']}% realized: ${r['realized_revenue_$M']/1000:.1f}B "
              f"covers {r['coverage_of_operating_low_%']:.0f}% of campaign-figure "
              f"operating costs, {r['coverage_of_operating_high_%']:.0f}% at "
              f"analyst high, {r['coverage_of_total_low_%']:.0f}% of all pledges")
    print(f"Break-even realization: {breakeven_op_low:.1f}% of pledged revenue "
          f"must materialize to cover operating costs at campaign figures; "
          f"at 75% realization the operating surplus flips to a "
          f"${abs(revenue_rows[1]['gap_vs_operating_low_$M'])/1000:.2f}B gap. "
          f"Analyst-high operating costs need {breakeven_op_high:.1f}% and "
          f"all pledges need {breakeven_total_low:.1f}% — both unreachable.")
    print()
    print("--- Joint Albany x realization sensitivity (operating-only) ---")
    for label, base in albany_outcome_totals():
        cells = [r for r in joint_rows if r["albany_outcome"] == label]
        covers = ", ".join(
            f"{r['realization_%']}% -> {r['coverage_of_operating_low_%']:.1f}%"
            for r in cells)
        print(f"{label} (pledged ${base/1000:.0f}B, break-even "
              f"realization {cells[0]['breakeven_realization_%']:.1f}%): {covers}")
    print(f"Only {len(joint_covering)} of {len(joint_rows)} combinations cover "
          f"campaign-figure operating costs: both taxes approved and "
          f"collected in full. Every partial-approval outcome needs more "
          f"than 100% realization to break even, and the joint downside "
          f"(neither tax, 25% realized) collects "
          f"${joint_rows[-1]['realized_revenue_$M']/1000:.2f}B against "
          f"${op_low/1000:.1f}B of operating costs "
          f"({joint_rows[-1]['coverage_of_operating_low_%']:.1f}% coverage).")
    print()
    print("--- Childcare cost x Albany outcome sensitivity (operating-only) ---")
    for label, total_rev in albany_outcome_totals():
        cells = [r for r in cc_albany_rows if r["albany_outcome"] == label]
        covers = ", ".join(
            f"{r['childcare_case']} -> {r['coverage_%']:.1f}%"
            for r in cells)
        print(f"{label} (revenue ${total_rev/1000:.0f}B, break-even "
              f"childcare ${cells[0]['breakeven_childcare_$M']/1000:.2f}B): "
              f"{covers}")
    print(f"Only {len(cc_albany_covering)} of {len(cc_albany_rows)} "
          f"combinations cover operating costs. Partial Albany wins cover "
          f"only at the analyst-low childcare cost, and with neither tax "
          f"the break-even childcare cost is negative "
          f"(${cc_albany_rows[-1]['breakeven_childcare_$M']/1000:.2f}B): "
          f"city-controlled revenue cannot cover even the "
          f"${other_operating/1000:.2f}B of non-childcare operating pledges.")
    print("Sources: SOURCES.md (results.csv, scenarios.csv, sensitivity.csv,")
    print("childcare_sensitivity.csv, revenue_sensitivity.csv,")
    print("joint_sensitivity.csv, childcare_albany.csv, results.png,")
    print("results_operating.png, results_sensitivity.png,")
    print("results_childcare.png, results_revenue.png, results_joint.png,")
    print("results_childcare_albany.png written).")


if __name__ == "__main__":
    main()
