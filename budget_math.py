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
PLEDGES = [
    # (label, low, high, note)
    ("Fare-free buses", 700, 800,
     "Campaign cited ~$700M/yr lost fare revenue; analysts up to ~$800M."),
    ("Universal childcare (6wk-5yr)", 5_900, 12_700,
     "Campaign estimate ~$5.9B; independent analyses range $2.5B-$12.7B."),
    ("City-owned grocery stores", 60, 60,
     "Campaign pilot: ~$60M/yr."),
    ("Dept. of Community Safety", 1_100, 1_100,
     "Campaign budgeted ~$1.1B/yr."),
    ("Rent freeze (rent-stabilized)", 0, 0,
     "No direct budget cost; cost borne by landlords via forgone rent."),
    ("200k affordable units / 10 yrs", 10_000, 10_000,
     "Campaign: $100B over 10 years => ~$10B/yr run rate (mostly capital)."),
]

REVENUE = [
    # (label, estimate $M/yr, note)
    ("Corp tax 7.5% -> 11.5%", 5_000,
     "Campaign estimate; requires Albany approval."),
    ("2% income tax on $1M+ earners", 4_000,
     "Campaign estimate; requires Albany approval."),
    ("Fines/waste collection", 1_000,
     "Campaign estimate."),
]


def annual_costs():
    low = sum(p[1] for p in PLEDGES)
    high = sum(p[2] for p in PLEDGES)
    return low, high


def proposed_revenue():
    return sum(r[1] for r in REVENUE)


def main():
    cost_low, cost_high = annual_costs()
    revenue = proposed_revenue()

    rows = []
    for label, low, high, note in PLEDGES:
        rows.append({
            "item": label,
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
    print("Sources: SOURCES.md (results.csv and results.png written).")


if __name__ == "__main__":
    main()
