"""Unit tests for budget_math: sourced totals, the v6 joint grid,
the v7 childcare x Albany grid, and the v8 horizon cut.

Run: python3 -m unittest test_budget_math -v
"""

import unittest

import budget_math as bm


class TestSourcedTotals(unittest.TestCase):
    def test_operating_costs(self):
        # 700 + 5,900 + 60 + 1,100 campaign; high adds 100 (buses)
        # and 6,800 (childcare).
        self.assertEqual(bm.annual_costs(kind="operating"), (7_760, 14_660))

    def test_total_costs_include_capital(self):
        self.assertEqual(bm.annual_costs(), (17_760, 24_660))

    def test_revenue_split(self):
        self.assertEqual(bm.proposed_revenue(), 10_000)
        self.assertEqual(bm.proposed_revenue(albany_required=True), 9_000)
        self.assertEqual(bm.proposed_revenue(albany_required=False), 1_000)


class TestJointSensitivity(unittest.TestCase):
    def setUp(self):
        self.rows = bm.joint_sensitivity_rows()

    def test_grid_shape(self):
        self.assertEqual(len(self.rows), 16)  # 4 Albany outcomes x 4 rates
        outcomes = {r["albany_outcome"] for r in self.rows}
        self.assertEqual(len(outcomes), 4)

    def test_albany_totals_include_city_line(self):
        totals = dict(bm.albany_outcome_totals())
        self.assertEqual(totals["Both Albany taxes approved"], 10_000)
        self.assertEqual(totals["Corp tax only"], 6_000)
        self.assertEqual(totals["Income tax only"], 5_000)
        self.assertEqual(totals["Neither Albany tax approved"], 1_000)

    def test_only_one_combination_covers_operating_low(self):
        covering = [r for r in self.rows if r["covers_operating_low"] == "Yes"]
        self.assertEqual(len(covering), 1)
        self.assertEqual(covering[0]["albany_outcome"],
                         "Both Albany taxes approved")
        self.assertEqual(covering[0]["realization_%"], 100)

    def test_spot_cell_corp_only_at_75(self):
        cell = next(r for r in self.rows
                    if r["albany_outcome"] == "Corp tax only"
                    and r["realization_%"] == 75)
        self.assertEqual(cell["realized_revenue_$M"], 4_500)
        self.assertEqual(cell["coverage_of_operating_low_%"], 58.0)
        self.assertEqual(cell["gap_vs_operating_low_$M"], -3_260)

    def test_breakeven_realization_by_outcome(self):
        breakevens = {}
        for r in self.rows:
            breakevens.setdefault(r["albany_outcome"],
                                  r["breakeven_realization_%"])
        self.assertEqual(breakevens["Both Albany taxes approved"], 77.6)
        self.assertEqual(breakevens["Corp tax only"], 129.3)
        self.assertEqual(breakevens["Income tax only"], 155.2)
        self.assertEqual(breakevens["Neither Albany tax approved"], 776.0)

    def test_coverage_falls_as_realization_falls(self):
        for label, _ in bm.albany_outcome_totals():
            covs = [r["coverage_of_operating_low_%"] for r in self.rows
                    if r["albany_outcome"] == label]
            self.assertEqual(covs, sorted(covs, reverse=True))

    def test_joint_downside_cell(self):
        cell = self.rows[-1]
        self.assertEqual(cell["albany_outcome"], "Neither Albany tax approved")
        self.assertEqual(cell["realization_%"], 25)
        self.assertEqual(cell["realized_revenue_$M"], 250)
        self.assertEqual(cell["coverage_of_operating_low_%"], 3.2)

    def test_no_combination_covers_operating_high(self):
        self.assertTrue(all(r["coverage_of_operating_high_%"] < 100
                            for r in self.rows))


class TestChildcareAlbany(unittest.TestCase):
    def setUp(self):
        self.rows = bm.childcare_albany_rows()

    def test_grid_shape(self):
        self.assertEqual(len(self.rows), 16)  # 4 Albany outcomes x 4 cases
        cases = {r["childcare_case"] for r in self.rows}
        self.assertEqual(len(cases), 4)

    def test_childcare_cases_match_v4_range(self):
        self.assertEqual(bm.childcare_case_list(),
                         [("Analyst low", 2_500),
                          ("Campaign figure", 5_900),
                          ("Midpoint of published range", 7_600),
                          ("Analyst high", 12_700)])

    def test_other_operating_held_constant(self):
        # Operating campaign total 7,760 minus childcare 5,900.
        self.assertTrue(all(r["other_operating_$M"] == 1_860
                            for r in self.rows))
        totals = {r["childcare_case"]: r["total_operating_$M"]
                  for r in self.rows}
        self.assertEqual(totals["Analyst low"], 4_360)
        self.assertEqual(totals["Campaign figure"], 7_760)
        self.assertEqual(totals["Analyst high"], 14_560)

    def test_breakeven_childcare_by_outcome(self):
        breakevens = {}
        for r in self.rows:
            breakevens.setdefault(r["albany_outcome"],
                                  r["breakeven_childcare_$M"])
        self.assertEqual(breakevens["Both Albany taxes approved"], 8_140)
        self.assertEqual(breakevens["Corp tax only"], 4_140)
        self.assertEqual(breakevens["Income tax only"], 3_140)
        # Negative: city-controlled revenue cannot cover even the
        # non-childcare operating pledges ($1,860M vs $1,000M).
        self.assertEqual(breakevens["Neither Albany tax approved"], -860)

    def test_only_five_combinations_cover(self):
        covering = {(r["albany_outcome"], r["childcare_case"])
                    for r in self.rows if r["covers_operating"] == "Yes"}
        self.assertEqual(covering, {
            ("Both Albany taxes approved", "Analyst low"),
            ("Both Albany taxes approved", "Campaign figure"),
            ("Both Albany taxes approved", "Midpoint of published range"),
            ("Corp tax only", "Analyst low"),
            ("Income tax only", "Analyst low"),
        })

    def test_spot_cells(self):
        corp_mid = next(r for r in self.rows
                        if r["albany_outcome"] == "Corp tax only"
                        and r["childcare_case"] == "Midpoint of published range")
        self.assertEqual(corp_mid["coverage_%"], 63.4)
        self.assertEqual(corp_mid["gap_$M"], -3_460)
        neither_low = self.rows[-4]  # first Neither-tax row: analyst low
        self.assertEqual(neither_low["childcare_case"], "Analyst low")
        self.assertEqual(neither_low["coverage_%"], 22.9)

    def test_coverage_falls_as_childcare_cost_rises(self):
        for label, _ in bm.albany_outcome_totals():
            covs = [r["coverage_%"] for r in self.rows
                    if r["albany_outcome"] == label]
            self.assertEqual(covs, sorted(covs, reverse=True))


class TestTermHorizon(unittest.TestCase):
    def setUp(self):
        self.rows = {r["horizon_years"]: r for r in bm.term_rows()}

    def test_capital_capped_at_plan_total(self):
        self.assertEqual(self.rows[4]["cumulative_capital_$M"], 40_000)
        self.assertEqual(self.rows[10]["cumulative_capital_$M"], 100_000)
        self.assertEqual(self.rows[20]["cumulative_capital_$M"], 100_000)
        self.assertEqual(self.rows[50]["cumulative_capital_$M"], 100_000)

    def test_cumulative_totals(self):
        # 4 yrs: operating 7,760 x 4 + capital 40,000.
        self.assertEqual(self.rows[4]["cumulative_total_low_$M"], 71_040)
        self.assertEqual(self.rows[4]["cumulative_pledged_revenue_$M"],
                         40_000)
        # 10 yrs: operating 77,600 + the full 100,000 capital plan.
        self.assertEqual(self.rows[10]["cumulative_total_low_$M"], 177_600)
        self.assertEqual(self.rows[10]["cumulative_total_high_$M"], 246_600)
        self.assertEqual(self.rows[10]["cumulative_gap_vs_total_low_$M"],
                         -77_600)

    def test_coverage_flat_while_capital_runs_then_rises(self):
        self.assertEqual(self.rows[1]["coverage_of_total_low_%"], 56.3)
        self.assertEqual(self.rows[10]["coverage_of_total_low_%"], 56.3)
        self.assertEqual(self.rows[20]["coverage_of_total_low_%"], 78.4)
        self.assertEqual(self.rows[50]["coverage_of_total_low_%"], 102.5)

    def test_gap_peaks_at_year_10_then_shrinks(self):
        gap10 = self.rows[10]["cumulative_gap_vs_total_low_$M"]
        gap20 = self.rows[20]["cumulative_gap_vs_total_low_$M"]
        gap50 = self.rows[50]["cumulative_gap_vs_total_low_$M"]
        self.assertLess(gap10, gap20)
        self.assertEqual(gap20, -55_200)
        self.assertEqual(gap50, 12_000)

    def test_breakeven_horizon(self):
        # 100,000 / (10,000 - 7,760) = 44.64 -> 44.6 years.
        self.assertEqual(bm.breakeven_horizon(), 44.6)
        # Crossover falls between the year-44 and year-45 cumulative rows.
        rows = {r["horizon_years"]: r
                for r in bm.term_rows(horizons=(44, 45))}
        self.assertEqual(rows[44]["cumulative_gap_vs_total_low_$M"], -1_440)
        self.assertEqual(rows[45]["cumulative_gap_vs_total_low_$M"], 800)

    def test_breakeven_horizon_none_at_analyst_high(self):
        # Revenue 10,000 < analyst-high operating 14,660: never breaks even.
        self.assertIsNone(bm.breakeven_horizon(high=True))
        self.assertTrue(all(r["breakeven_horizon_high_years"] is None
                            for r in self.rows.values()))

    def test_city_only_revenue_never_covers_operating(self):
        for r in self.rows.values():
            self.assertLess(r["cumulative_city_only_revenue_$M"],
                            r["cumulative_operating_low_$M"])


if __name__ == "__main__":
    unittest.main()
