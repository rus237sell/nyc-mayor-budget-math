# NYC mayor budget math

**Goal:** Test whether the mayor's headline affordability pledges add up — campaign cost estimates vs. campaign revenue proposals, scaled against the enacted FY2027 city budget.

**Macro steps:**
1. Collected published cost estimates for the six signature pledges (campaign's own figures as the low case, independent analyst ranges as the high case).
2. Collected the campaign's three revenue proposals with the same sourcing.
3. Compared total pledged cost range against pledged revenue (coverage ratio), and pledges as a share of the $125.8B adopted FY2027 budget.
4. Plotted costs vs. revenue and wrote the pledge table to `results.csv`; split each pledge into operating vs. capital, ran an operating-only scenario against Albany-dependent vs. city-controlled revenue (`scenarios.csv`, second chart).
5. Tested Albany partial approval (both taxes / corp only / income only / neither) against operating-only costs (`sensitivity.csv`, third chart).

**Versions:** v1 — initial analysis. v2 — operating-only scenario + Albany-dependency revenue cut (new `scenarios.csv`, `results_operating.png`). v3 — Albany partial-approval sensitivity + childcare swing check (new `sensitivity.csv`, `results_sensitivity.png`).

**Short results:** On the campaign's own figures, the six pledges total ~$17.8B/yr against $10B/yr of pledged revenue — a $7.8B shortfall that widens to $14.7B at the top of published analyst ranges. Strip out the $100B/10-yr housing capital plan (capital, not operating), and the operating pledges (~$7.8B) are covered 129% by pledged revenue on campaign figures — but 90% of that revenue ($9B of $10B) needs Albany approval, and the only city-controlled line (fines/waste, $1B) covers just 13% of operating costs. Partial Albany approval does not close it either: corp tax only ($6B total) covers 77% of campaign-figure operating costs, income tax only ($5B) covers 64%, and childcare alone drives the uncertainty — its $6.8B low-to-high swing is 99% of the operating cost range. The enacted FY2027 budget closed its $5.4B gap with savings + state aid + pension restructuring, not the pledged tax hikes.
