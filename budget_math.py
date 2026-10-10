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
    print("Sources: SOURCES.md (results.csv, scenarios.csv, results.png,")
    print("results_operating.png written).")


if __name__ == "__main__":
    main()
