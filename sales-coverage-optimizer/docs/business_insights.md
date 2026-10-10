# Business Insights

Real output from `run_pipeline.py` on the seed-42 synthetic dataset, base
assumptions (`docs/assumptions.md`). Every number here is in
`data/results/`. Where a result depends on a guess, the guess is named and
its range is shown.

## What changed since the first version, and why

A review found that the first version's headline numbers mostly came from
how the data and a few settings had been chosen, not from analysis.

| First version said | Problem | Now |
|---|---|---|
| "38 reps, not 119; 70.9% cheaper" | 38 was arithmetic on an unsourced "55 points per rep". The baseline used every rep by design, and idle reps were counted as free | Workload built up from visits and hours; compared against the real as-is, a greedy rule, and the optimiser. **56 → 45 reps, 18% lower cost to serve** |
| "Ratio warned a year before margin" | Detected a planted pattern; 37% starting margin; docs contradicted themselves | Tested on 200 histories it wasn't tuned on; realistic P&L. **Warning catches 99% of breaches ~2 years early, with 24% false alarms** |
| "Product Specialist is cheapest" | Travel was free, and travel is why the real company went geographic | Travel and expertise risk priced in rupees. **Product Specialist is the most expensive; Geographic and Hybrid tie** |
| "Pod breaks even in 2.4 months" | Annual pay counted as one-time; revenue counted as profit; 40 accounts assumed vs 33 in data | Margin-based 24-month model with three options. **Channel partners; a pod needs a 29% win rate to win** |
| "Echoes the case's headcount problem" | The case shows the opposite (reps 1.4× vs revenue 2.1×) | Labelled as a stress scenario invented to test Module A |

---

## A. Diagnostic Engine — is sales cost outrunning growth?

**Output.** Net margin falls every year, from 11.6% (2019) to 1.2% (2024),
while revenue grows 2.1×. Sales headcount grows 3.5× (16 → 56), so sales
cost rises from 9.6% to 21.4% of revenue.

- **Early warning: 2020.** Cumulative headcount growth is already 24%
  ahead of revenue growth.
- **Margin breach: 2022.** Net margin falls below half its base-year level
  (5.8%).
- **2 years' notice.** Sustainability score 20/100.
- Revenue growth never drops below 14% in any year, so a team watching
  revenue would have seen nothing.
- Had headcount grown in step with revenue, the team would be **34** reps,
  not 56.

**Is the warning any good?** Run on 200 generated histories (headcount
growing anywhere from 0.7× to 2× as fast as revenue, with noise), judged
against whether margin actually breached:

| Warn when headcount runs ahead by | Breaches caught | False alarms | Median years' notice |
|---|---|---|---|
| 10% | 100% | 63% | 2 |
| **20% (used)** | **99%** | **24%** | **2** |
| 30% | 91% | 4% | 1 |
| 40% | 77% | 0% | 0 |

Watching revenue growth instead (warn when it falls below 8%) caught only
34% of breaches, with 43% false alarms.

**Insight.** The ratio is a real leading indicator, but there is a trade-off
to choose, not a free lunch. At 20% it catches almost everything two years
out and is wrong about one time in four. At 30% it is rarely wrong but
gives one year's notice instead of two.

**Decision it enables.** Track cumulative headcount growth against revenue
growth every quarter. Treat 20% as "investigate" and 30% as "act".

*VP-of-Sales view: revenue never stopped growing, so revenue was never
going to tell us. The ratio would have told us in 2020, two years before
the margin did. It will also cry wolf about one time in four at that
setting, so it starts a conversation; it doesn't trigger a restructuring
on its own.*

---

## B. Coverage Model Simulator — which structure?

**Output** (₹M a year: payroll + travel + expertise risk + margin on
uncovered accounts):

| Structure | Reps | Payroll | Travel | Total | Complex accounts with a product expert |
|---|---|---|---|---|---|
| Geographic | 45 | 47.6 | 7.0 | **56.5** | 70% |
| Segmented Hybrid | 45 | 47.6 | 7.6 | **56.5** | 72% |
| Product Specialist | 53 | 56.6 | 18.1 | 76.8 | 100% |

**Across 100 different generated account bases:** Geographic and Hybrid
tie (within 1%) in 73% of them. Geographic is cheapest outright in 21% and
Hybrid in 6%. Product Specialist never wins and costs about 29% more on
average (₹71.6M vs ₹55.6M).

**Which inputs would change it.** Moving travel cost (0.5–2× base) and the
margin lost on complex accounts served by a non-expert (0–100%):
- Hybrid edges ahead when travel is at or below base cost and expertise
  loss is 10% or more (and at 1.5× travel once loss reaches 75%).
- Wherever either structure leads, the gap between them never exceeds 3%.
- Product Specialist does not win anywhere in the grid.

**Insight.** Once travel is priced, specialising by product across regions
is the most expensive design by far. Travel time also eats selling hours,
so it needs 8 more reps. The 2009 lesson still holds, but the fix is
cheaper than a specialist force. Most regions already have reps with
product backgrounds, so **matching accounts to those reps inside each
region** recovers most of the expertise without the travel.

**Decision it enables.** Stay geographic, but assign complex accounts to
the in-region rep whose background matches the product. Re-test the
specialist overlay if Haryana's complex-account revenue slips.

*VP-of-Sales view: the answer to Haryana isn't flying specialists around
the country. It's making sure that inside Haryana, the conveyor accounts
go to the conveyor people.*

---

## C. Territory Optimizer — how many reps, and who owns what?

The optimiser runs on Module B's recommendation (Geographic), with:
- a 50–90% workload band for every kept rep
- a charge for moving an account away from its current owner
- the option to relocate a rep into a region that is short of capacity.

| Method | Reps | Total cost ₹M | Accounts changing owner | Rep load range |
|---|---|---|---|---|
| As-is (today) | 56 | 68.0 | 0 | 5%–223% |
| Greedy (fill cheapest first) | 47 | 57.6 | 558 | 5%–90% |
| **Optimiser** | **45** | **55.5** | **247** | **51%–90%** |
| Optimiser ignoring current owners | 45 | 55.3 | 551 | 53%–90% |

**Findings.**
- **The problem is distribution, not just size.** Haryana (121 of the 175
  complex accounts) is short by 2 reps. Today one rep there carries 223% of
  their selling hours. Tamil Nadu has 5 more reps than it needs, and
  Maharashtra and Gujarat 3 each.
- **The optimiser's real value is continuity, not cost.** It beats the
  greedy rule by ₹2.1M a year (3.6%). It moves 247 accounts instead of
  558, and leaves no rep with a token book. Ignoring current owners would
  save another ₹0.3M at the price of 304 more account handovers.
- **Headcount depends most on one assumption, selling hours per rep:**

| Selling hours per rep per year | 750 | 850 | **990** | 1,100 | 1,200 |
|---|---|---|---|---|---|
| Reps needed | 56 (Haryana still short) | 51 | **45** | 40 | 38 |

**Trade-off to flag.** At the base expertise-loss assumption (10%), the
redesign lowers the share of complex accounts served by a product expert
from 80% to 67%. Re-solved assuming 25% loss, it keeps 73% for ₹0.3M more
a year.

*VP-of-Sales view: we don't need 56 reps, and we don't need the same
number in every region. Haryana needs two more and Tamil Nadu five fewer.
Before committing to 45, I'd measure how many selling hours our reps
really have, because that one number moves the answer by ±6 people.*

---

## D. New-Product GTM Scorer — how to sell the Dumb Waiter

**Fit score: 0.52.** At or above 0.50, the product is a poor fit for the
existing sales motion. The inputs, all from the data:

| Input | Value | Basis |
|---|---|---|
| Buyer distance | 0.66 | No overlap in buyer type (builders, hotels and hospitals vs. industrial plants); different regional mix (0.32); tickets about a third the size (0.67) |
| Complexity distance | 0.37 | Average complexity ~1.5 vs ~3.0 |
| Deal-cycle distance | 0.50 | 46 vs 94 days |

The score is borderline. Any one input falling to about 0.61 (buyer), 0.31
(complexity) or 0.42 (deal cycle) would tip it to "fits". It says the
existing motion is a questionable home; it does not say where else to go.

**Economics** (24 months, gross margin after each option's own costs; base
case):

| Option | Accounts won | Contribution ₹M | Pays back vs. existing force |
|---|---|---|---|
| Existing sales force | 66 | 0.7 | — |
| Dedicated pod (3 redeployed reps) | 127 | 0.5 | Not within 24 months |
| **Channel partners** (lift dealers, 1 redeployed rep) | 86 | **1.7** | Month 12 |

- **Pessimistic case:** channel partners still lead, though every option
  loses money.
- **Optimistic case:** the pod leads.
- **Break-even:** the pod needs a **29%** win rate (25% assumed) to beat
  partners.

**Insight.** The pod wins the most accounts but loses on money. Dumb
Waiter tickets average ₹166K, so three full salaries are hard to cover.
Partners already sell to builders, and their cost scales with sales. "Pod
or existing force" was the wrong question.

**Decision it enables.** Take the Dumb Waiter out of the generalists' bag
and sell it through about 8 lift dealers and installers, managed by one
redeployed rep. Revisit the pod only if measured win rates come in above
about 29%.

*VP-of-Sales view: this is a small-ticket product sold to people our reps
never call on. Dealers already have those relationships. We put one person
on making them successful and keep our reps on the accounts that pay for
them.*

---

## Economics — does the redesign pay?

| | Today | Redesigned |
|---|---|---|
| Sales reps | 56 | 45 |
| Cost to serve (payroll + travel) | ₹67.4M | ₹55.1M |
| Cost to serve per account | ₹104K | ₹85K |
| Cost to serve, % of revenue | 21.4% | 17.5% |
| Revenue per rep | ₹5.6M | ₹7.0M |
| Net margin (final year, after tax) | 1.2% | 4.1% |

- **Saving:** ₹12.2M a year.
- **One-time cost of the change:** ₹4.5M base (₹2.8M–₹8.6M). That covers
  severance for 10 reps, 2 relocations, retraining, and margin lost on 247
  handovers.
- **Payback:** month 6 in the base case (release now or attrition), month
  8–10 in the pessimistic case.

Net margin recovers to 4.1%, not to its 2019 level of 11.6%, because the
redesign fixes sales cost only. CAC, LTV and ROAS are not computed: the
dataset has no marketing spend or retention data, and inventing them would
be decoration.

Rollout sequence, owners and post-rollout KPIs: `docs/rollout_plan.md`.

## Open items

1. Selling hours per rep and the expertise-loss rate drive the two biggest
   answers. Both should be measured (visit logs; Haryana complex-account
   revenue) before acting.
2. The Dumb Waiter economics rest on assumed win rates and partner
   volumes. Only the pilot account count (33) is data.
3. Module A's false-alarm rate (24% at the chosen threshold) means it
   should open a review, not decide one.
