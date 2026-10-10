# Rollout plan

How the redesign would actually be deployed. All figures come from
`run_pipeline.py` (seed-42 dataset, base assumptions); region detail is in
`data/results/e_region_changes.csv`. The case's own lesson shapes the order:
the 2009 restructuring failed in Haryana because changes were made without
regard to who could serve which accounts. So the plan fixes the most
complex region first, pilots the cuts in the least complex one, and makes
each step depend on the previous step's numbers.

## What changes

| Region | Reps today | Reps needed | Change | Accounts changing owner | Complex accounts |
|---|---|---|---|---|---|
| Haryana Belt | 11 | 13 | **+2 (relocated in)** | 86 | 121 |
| Delhi NCR | 7 | 7 | 0 | 31 | 6 |
| Karnataka South | 6 | 4 | −2 | 23 | 0 |
| Gujarat Industrial Corridor | 8 | 5 | −3 | 22 | 4 |
| Maharashtra West | 12 | 9 | −3 | 52 | 38 |
| Tamil Nadu Coastal | 12 | 7 | −5 | 34 | 6 |
| **Total** | **56** | **45** | **−11** | **248** | **175** |

Of the 13 reps no longer needed in their current territory: 2 relocate to
Haryana, 1 becomes the channel-partner manager for the Dumb Waiter
(Module D), and 10 leave.

**Haryana is understaffed today, not overstaffed.** One rep there carries
over twice their selling hours. The headline "56 → 45" hides a region that
needs *more* people.

It is also the only region where capacity is the binding constraint: an
extra selling hour there is worth about ₹980 today, against ₹0 in most
other regions. That is why the plan fixes Haryana first. One caveat: a
full extra rep recovers about ₹4.3 lakh of margin a year, less than a
rep's cost. The relocations follow from the policy of covering every
account. If that policy is relaxed, the cheaper fallback is to serve
Haryana's smallest accounts by phone and relocate one rep, not two.

## Release now, or let attrition do it?

| Path | One-off cost (base) | Payback | Net benefit by month 24 | Time to target headcount |
|---|---|---|---|---|
| Release 10 reps now | ₹4.6M | Month 6 | ₹18.9M | 1 month |
| Hiring freeze, normal attrition (20%/yr) | ₹1.9M (no severance) | Month 6 | ₹17.6M | ~11 months |

Under pessimistic transition assumptions (6 months' severance, 10% margin
loss on handed-over accounts), release-now pays back in month 10 and
attrition in month 8.

Operating leverage gives a second reason to act on how the cost base is
built, not just its size: in 2024 a 10% revenue dip would wipe out
operating profit, because the whole sales cost behaves as fixed. Moving
20–40% of rep pay to commission brings leverage from 14 down to 9–12.

**Recommended: hiring freeze plus attrition, with transfers.** It gives up
about ₹1.3M over two years in exchange for no severance, no forced exits
and a slower pace of account handovers, which is where the real risk sits.
The caveat: people leave from every region, not just surplus ones. A
Haryana exit must be backfilled by a transfer from Tamil Nadu, Gujarat or
Maharashtra, so the plan needs a standing transfer rule, not just a freeze.

## Phases

**Month 0 — decide and announce**
- Approve the 45-rep target and the region numbers above. Freeze hiring.
- Publish the new account map to the affected reps, with the 248 moves
  listed by name (`data/results/c_assignment.csv`).
- Owner: VP Sales. Finance signs off the transition budget (₹1.9M base,
  ₹3.4M high).

**Months 1–2 — fix Haryana first**
- Relocate 2 reps into Haryana (₹150K each) from Tamil Nadu (largest
  surplus). Prefer reps with Conveyor or Bulk Material Handling
  backgrounds, the lines most of Haryana's 121 complex accounts buy.
- Rebalance Haryana's 86 account moves with joint handover visits for
  every complex account, so no complex account changes hands without a
  meeting.
- Exit check: no Haryana rep above 90% of selling hours; no complex
  account lost.

**Months 2–4 — pilot the reduction in Karnataka South**
- Lowest-risk region: no complex accounts, 23 moves, −2 reps.
- Exit check: revenue on the 23 moved accounts holding at ≥95% of the
  prior-year run rate; remaining reps at 50–90% load.
- If the check fails, pause the remaining regions and raise the
  handover-loss assumption before continuing.

**Months 4–9 — remaining regions, lowest complexity first**
- Gujarat (−3, 22 moves) → Tamil Nadu (−5, 34 moves) → Maharashtra West
  (−3, 52 moves, 38 complex accounts, so last). Delhi NCR keeps 7 reps and
  rebalances 31 accounts.

**Months 1–6, in parallel — Dumb Waiter through channel partners**
- Redeploy one freed rep as partner manager. Sign about 8 lift dealers or
  installers in Delhi NCR, Maharashtra West and Karnataka South, where the
  pilot buyers are. The reachable market (~61 units a year) supports about
  10 dealers at 6 installs each, so 8 is selective distribution.
- Trade terms: 10% commission, 45-day credit.
- Quote toward the market price. Ours is ₹1.66 lakh against a competitor
  median of ~₹2.5 lakh. Track win rate by price band from the first quarter.
- Hold the architect-specification programme until price is tested; at
  today's price it doesn't pay for itself.
- Review at month 12: fewer than 24 partner-sourced accounts (the
  pessimistic case) means the channel is under-performing. If the price
  test lands near +20% and demand holds, revisit the dedicated-pod option:
  at that price it draws level with partners (Module D).

## KPIs to watch after rollout

Each KPI has a trigger level that sends the team back to re-run the
pipeline with real data rather than wait for the annual cycle.

| KPI | Target | Trigger to re-run |
|---|---|---|
| Cost to serve, % of revenue | ≤ 17.5% | > 20% for two quarters |
| Accounts per rep (Module A decomposition) | ≥ 14 | Falls below 12, the 2024 level |
| Cumulative headcount growth ÷ revenue growth (Module A's warning) | ≤ 1.0× from the new base | > 1.2× |
| Rep load | Every rep at 50–90% of selling hours | Any rep > 100% or < 40% for a quarter |
| Revenue retained on accounts that changed owner | ≥ 95% at 12 months | < 90% (handover loss is worse than the 5% assumed) |
| Engineering-led accounts served by a product expert | ≥ 69% overall | Haryana engineering-led account revenue down > 5% (the expertise-loss assumption is too low; re-test the hybrid) |
| Dumb Waiter partner-sourced accounts | ≥ 48 a year at run rate | < 24 in the first 12 months |

## What would change this plan

- **Selling hours per rep.** The single most sensitive input. At 850 hours
  the target is 52 reps; at 1,100 it is 40. Measure it from three months
  of visit logs before committing to the release numbers.
- **Expertise loss.** At the base 10%, the redesign lowers expert coverage
  of engineering-led accounts from 79% to 69%. Re-solved at 25%, the
  optimiser keeps 71% for ₹0.8M more a year. If Haryana's numbers dip, use
  that version.
- **Real data.** Every assumption is listed in `docs/assumptions.md`. The
  first planning cycle with real CRM visit logs and account history should
  replace them, then re-run `python run_pipeline.py`.
