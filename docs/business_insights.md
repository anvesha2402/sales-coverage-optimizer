# Business Insights

Real output from `run_pipeline.py` on the seed-42 synthetic dataset, base
assumptions (`docs/assumptions.md`). Every number here is in
`data/results/`. Where a result depends on a guess, the guess is named and
its range is shown.

## What changed, and why

**Version 2** rebuilt the first version, whose headline numbers mostly came
from how the data and settings were chosen:

| First version said | Problem | Version 2+ |
|---|---|---|
| "38 reps, not 119; 70.9% cheaper" | 38 was arithmetic on an unsourced "55 points per rep". The baseline used every rep by design, and idle reps were counted as free | Workload built up from visits and hours; compared against the real as-is, a greedy rule and the optimiser. **56 → 45 reps, 18% lower cost to serve** |
| "Ratio warned a year before margin" | Detected a planted pattern; 37% starting margin; docs contradicted themselves | Tested on 200 histories; realistic P&L. **99% of breaches caught ~2 years early, 24% false alarms** |
| "Product Specialist is cheapest" | Travel was free | Travel and expertise risk priced. **Product Specialist is the most expensive** |
| "Pod breaks even in 2.4 months" | Annual pay counted as one-time; revenue counted as profit | Margin-based 24-month model. **Channel partners** |
| "Echoes the case's headcount problem" | The case shows the opposite | Labelled as an invented stress scenario |

**Version 3** adds the MBA frameworks that change a number or a decision,
and leaves out the ones that would only decorate:

| Framework | Where | What it changed |
|---|---|---|
| Revenue decomposition (reps × accounts per rep × revenue per account) | A | Showed the fall in revenue per rep is entirely coverage thinning; the customers didn't weaken |
| Operating leverage | A | Showed why margin fell faster than costs rose, and gave the hiring-freeze path a risk rationale |
| Theory of Constraints / shadow prices | C | Put a number on Haryana as the bottleneck, and showed that adding reps there pays only under a cover-everyone policy |
| B2B buying centre | B, C, D | Grounded "needs an expert" in the engineering role, and grounded buyer distance in who decides |
| Service output demands, trade terms, push vs pull | D | An independent test of the channel choice; costed dealer credit days; added an architect programme as a fourth option |
| TAM / SAM / SOM, distribution intensity | D | Capped every option's volume at the reachable market. A pod can no longer win at any win rate, and the market supports ~10 dealers |
| EVC pricing | D | Showed price headroom. At a higher price the pod and partners are neck and neck |

Considered and left out, because they would add no number or decision:
marketing concept vs selling orientation, exchange theory, Ansoff, jobs to
be done, 7Ps, Ishikawa / 5 Whys, queueing theory, CLV/NRR (no retention
data). MECE and the Minto pyramid are used to structure this write-up, not
as analysis.

---

## A. Diagnostic Engine — is sales cost outrunning growth?

**Output.** Net margin falls every year, from 11.6% (2019) to 1.2% (2024),
while revenue grows 2.1×. Sales headcount grows 3.5× (16 → 56), so sales
cost goes from 9.6% to 21.4% of revenue.

- **Early warning: 2020.** Cumulative headcount growth is 24% ahead of
  revenue growth.
- **Margin breach: 2022.** Net margin falls below half its base-year level.
- **2 years' notice.** Revenue growth never drops below 14% in any year.
- Had headcount grown in step with revenue, the team would be **34** reps.

**Is the warning any good?** On 200 generated histories it was not tuned on:

| Warn when headcount runs ahead by | Breaches caught | False alarms | Median years' notice |
|---|---|---|---|
| 10% | 100% | 63% | 2 |
| **20% (used)** | **99%** | **24%** | **2** |
| 30% | 91% | 4% | 1 |
| 40% | 77% | 0% | 0 |

Watching revenue growth instead (warn below 8%) caught 34% of breaches,
with 43% false alarms.

**Why did revenue per rep fall? (decomposition)**
- Revenue per rep fell **40%** (₹9.4M → ₹5.6M).
- Accounts per rep fell **46%** (21.6 → 11.6).
- Revenue per account *rose* **11%** (₹435K → ₹485K).

So the whole fall comes from each rep covering fewer accounts. The book
grew from 345 to 650 accounts, but reps were added faster. The customers
didn't get worse; coverage got thinner.

Win rate and repeat-order rate, the other two terms of the classic
four-term version, need deal-level data that this dataset does not have.
They are left out rather than invented.

**Why did margin fall so fast? (operating leverage)**
- In this P&L the whole sales cost scales with headcount, not revenue, so
  it acts as a fixed cost.
- Operating leverage (% change in profit per 1% change in revenue) climbs
  from **1.6 (2019) to 14.2 (2024)**.
- By 2024, a 10% revenue dip would wipe out more than all of operating
  profit (−142%).
- Paying 20% / 40% of rep pay as commission instead of salary would bring
  leverage down to **11.6 / 8.9**.

**Decision it enables.**
- Track cumulative headcount growth against revenue growth every quarter:
  20% means investigate, 30% means act.
- Track accounts per rep alongside it. That is the term that actually moved.
- Treat variable pay as a risk lever, not just a cost lever.

---

## B. Coverage Model Simulator — which structure?

**Output** (₹M a year: payroll + travel + expertise risk + margin on
uncovered accounts). "Needs an expert" now means engineering sits in the
account's buying centre: 250 of 650 accounts.

| Structure | Reps | Payroll | Travel | Total | Engineering-led accounts with a product expert |
|---|---|---|---|---|---|
| **Geographic** | 47 | 49.7 | 7.0 | **58.9** | 71% |
| Segmented Hybrid | 47 | 49.7 | 8.5 | 59.2 | 74% |
| Product Specialist | 53 | 56.6 | 18.1 | 76.8 | 100% |

**Across 100 generated account bases:**
- Geographic and Hybrid tie (within 1%) in 65% of them.
- Geographic is cheapest outright in 31% and Hybrid in 4%.
- Product Specialist never wins and costs about 25% more on average.

**Which inputs would change it.** Sweeping travel cost (0.5–2×) and margin
lost on engineering-led accounts served by a non-expert (0–100%):
- Hybrid leads only when travel is half its base cost.
- Product Specialist costs at least 15% more than Geographic everywhere in
  the grid.

**Insight.** Once travel is priced, specialising by product across regions
is the most expensive design. Most regions already have reps with product
backgrounds, so matching engineering-led accounts to those reps inside each
region recovers most of the expertise without the travel.

**Decision it enables.** Stay geographic. Assign every account whose buying
centre includes engineering to the in-region rep with the matching product
background.

---

## C. Territory Optimizer — how many reps, and who owns what?

The optimiser runs on Module B's recommendation (Geographic), with:
- a 50–90% workload band for every kept rep
- a charge for moving an account away from its current owner
- the option to relocate a rep into a region short of capacity.

| Method | Reps | Total cost ₹M | Accounts changing owner | Rep load range |
|---|---|---|---|---|
| As-is (today) | 56 | 68.3 | 0 | 5%–223% |
| Greedy (fill cheapest first) | 49 | 60.0 | 548 | 4%–90% |
| **Optimiser** | **45** | **55.7** | **248** | **50%–90%** |
| Optimiser ignoring current owners | 45 | 55.4 | 543 | 50%–90% |

**Findings.**
- **The problem is distribution, not just size.** Haryana (121 of the 175
  most complex accounts) is short by 2 reps. Tamil Nadu has 5 more than it
  needs, Maharashtra and Gujarat 3 each, and Karnataka 2.
- **The optimiser beats the greedy rule by ₹4.3M a year (7%)**, uses 4
  fewer reps, and moves 300 fewer accounts. Ignoring current owners would
  save another ₹0.3M at the price of 295 more handovers.
- **Selling hours per rep is the dominant assumption:**

| Selling hours per rep per year | 750 | 850 | **990** | 1,100 | 1,200 |
|---|---|---|---|---|---|
| Reps needed | 56 (Haryana still short) | 52 | **45** | 40 | 38 |

**Where is the constraint? (Theory of Constraints, from the optimiser's
shadow prices)**

| | Haryana | Maharashtra West | Other regions |
|---|---|---|---|
| Value of one more selling hour, today | **₹978** | ₹188 | ₹0 |
| Hours short of workload, today | **1,160** | 0 | 0 |
| Value of one more selling hour, after redesign | ₹202 | ₹188 | ₹0 |

- **Haryana is the one binding constraint today.** The redesign elevates
  it (two reps relocated in), and its value per hour falls by about 80%.
  Maharashtra's small value comes from expertise matching, not a shortage.
- **Caveat:** a full extra rep in Haryana recovers about ₹4.3 lakh of
  margin a year, less than a rep's ₹10.7 lakh cost. Relocating is
  justified by the policy of covering every account, not by one year's
  margin. The cheaper alternative is serving Haryana's smallest accounts
  by phone; `docs/rollout_plan.md` names it as the fallback.

**Trade-off.** The redesign lowers the share of engineering-led accounts
served by a product expert from 79% to 69%. Re-solved assuming 25%
expertise loss, it keeps 71% for ₹0.8M more a year.

---

## D. New-Product GTM Scorer — how to sell the Dumb Waiter

**Fit score: 0.62, a poor fit for the existing motion.** It no longer sits
on the line.

| Input | Value | Basis |
|---|---|---|
| Buyer distance | 0.92 | **Buying centre.** Dumb Waiter orders involve architects (76% of orders), builders' project managers (67%), hotel owners and F&B heads. Industrial orders involve plant heads and procurement (100%), engineering (41%) and finance (37%). Procurement is the only role in common |
| Complexity distance | 0.37 | Average complexity ~1.5 vs ~3.0 |
| Deal-cycle distance | 0.50 | 46 vs 94 days |

To flip to "fits", buyer distance would have to fall to 0.61, or
complexity to almost zero.

**Service outputs: what buyers need from a channel** (weights × scores
1–5; judgement calls, stated):
- **Weighted scores:** dealers **4.10**, dedicated pod 3.20, existing
  force 2.65.
- **Why dealers lead:** local presence, installation speed, after-sales
  service and single-unit orders.
- **Where the pod leads:** technical specification support only.
- **Robustness:** changing any single score by one point never changes
  the leader (0 of 30 tests).

**Market size: TAM / SAM / SOM.** Units a year in the covered regions,
built bottom-up from sourced construction, hotel and hospital figures plus
stated assumptions (`data/market_sizing.csv`):

| | Low | Base | High |
|---|---|---|---|
| New-build + retrofit (TAM) | 131 | **612** | 2,027 |
| Reachable by this company (SOM) | 33 (floored at pilot sales) | **61** | 304 |

- The assumed lead volume (220 a year) is within TAM.
- Partner volume (48 a year) is within SOM.
- A pod (~66 a year at full speed) would exceed the ceiling, so it is capped.
- **Distribution intensity:** the reachable market supports about **10
  dealers** at 6 installs each. The plan's ~8 dealers is selective, not
  intensive.

**Economics** (24 months, gross margin after each option's own costs, every
option capped at the reachable market; base case):

| Option | Accounts won | Contribution ₹M | Pays back vs. existing force |
|---|---|---|---|
| Existing sales force | 66 | 0.7 | — |
| Dedicated pod (3 redeployed reps) | 118 (capped) | −0.1 | Not within 24 months |
| **Channel partners** (lift dealers; 45-day credit, 10% commission) | 86 | **1.5** | Month 14 |
| Partners + architect programme (pull) | 98 | 0.9 | Month 21 |

- **By case:** partners lead in the pessimistic case; the pod leads only
  in the optimistic one.
- **Market cap:** **no pod win rate beats partners in the base case.**
  The reachable market caps the pod's extra capacity.
- **Architect programme:** it wins 12 more accounts but doesn't cover its
  ₹0.6M a year at today's price.

**Price check (EVC).**
- The pilot's average ticket is **₹1.66 lakh**, against a competitor median
  of about **₹2.5 lakh** (IndiaMART). The EVC is about ₹2.7 lakh, leaving
  **about ₹1.0 lakh of headroom**.
- A hotel or hospital recovers the price in about 1.5 years of saved
  helper wages.
- At +20% price with 10% fewer wins, 24-month contribution (₹M):
  - pod **3.5**
  - partners **3.4**
  - partners + architect programme 3.0
  - existing force 2.2

  The channel choice is no longer clear-cut; price matters more than route.

**Decision it enables.**
- **Route:** take the Dumb Waiter out of the generalists' bag. Sell it
  through about 8 lift dealers, managed by one redeployed rep.
- **Price:** run the first year's dealer quotes as a price test toward the
  market median.
- **Revisit** the pod (or the architect programme) only if price and
  measured win rates both come in high.

---

## Economics — does the redesign pay?

| | Today | Redesigned |
|---|---|---|
| Sales reps | 56 | 45 |
| Cost to serve (payroll + travel) | ₹67.4M | ₹55.1M |
| Cost to serve per account | ₹104K | ₹85K |
| Cost to serve, % of revenue | 21.4% | 17.5% |
| Revenue per rep | ₹5.6M | ₹7.0M |
| Engineering-led accounts served by a product expert | 79% | 69% |
| Net margin (final year, after tax) | 1.2% | 4.1% |

- **Saving:** ₹12.3M a year.
- **One-time cost of the change:** ₹4.6M base (₹2.9M–₹8.8M). That covers
  severance for 10 reps, 2 relocations, retraining, and margin lost on 248
  handovers.
- **Payback:** month 6 (months 8–10 pessimistic).
- **Not computed:** CAC, LTV and ROAS, because there is no marketing-spend
  or retention data.

Rollout sequence, owners and post-rollout KPIs: `docs/rollout_plan.md`.

## Open items

1. **The biggest answers rest on assumptions.** Selling hours per rep, the
   expertise-loss rate and the Dumb Waiter price drive them. Each should
   be measured before acting: visit logs, engineering-led account revenue
   in Haryana, and dealer quote outcomes.
2. **Module D's market sizing has gaps.** It rests partly on assumptions,
   including restaurant openings, adoption shares and reachable share.
   Only the hotel, housing, hospital and price figures are sourced.
3. **The service-output scores are judgements.** The ranking holds to any
   single one-point change, but not necessarily to several changing
   together.
4. **Module A's false-alarm rate (24%)** means it should open a review,
   not decide one.
