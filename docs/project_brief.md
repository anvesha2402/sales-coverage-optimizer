# Project Brief — Sales Coverage & GTM Structure Optimizer

**Live demo:** [sales-coverage-optimizer-x3momyht3cgit6ck7jkarz.streamlit.app](https://sales-coverage-optimizer-x3momyht3cgit6ck7jkarz.streamlit.app)
**Repo:** `anvesha2402/sales-coverage-optimizer`
**Source case:** *Lakshmi Projects: Sales Structure Dilemma* (Ivey W15219), Sandeep Puri, Mehmet A. Begen, Akshay Nangia, Arjit Rawal and Mayank Rawat, Richard Ivey School of Business Foundation, 2015.

---

## 1. Background — why this project exists

This is the second of two capstone projects built for a placements portfolio,
paired deliberately with a **Revenue Pipeline Capstone** (a predictive/ML,
full-funnel B2B SaaS revenue project). Most portfolio-building MBA students
show one of two things: a case-study write-up with no working code, or a
generic ML model with no real business framing behind it. This project is
built to avoid both — it takes a real, well-known Ivey case and turns it
into a **working, re-runnable decision tool**, so the pairing across both
capstones reads as "predictive AND prescriptive," two distinct and
complementary analytical skills, rather than the same trick done twice.

The build followed a 4-stage plan over roughly 5–6 weeks: data & framing,
core modules, dashboard, and packaging (GitHub repo, live Streamlit
deployment, demo video, LinkedIn case study). It was built and iterated in
Google Colab, then pushed to GitHub (`anvesha2402/sales-coverage-optimizer`)
and deployed live on Streamlit Community Cloud.

## 2. The underlying business problem (the case)

**Lakshmi Projects** is a Delhi-based bulk-material-handling-equipment
(BMHE) manufacturer — conveyor and elevator systems — that grew from 5
employees in 1997 to roughly 100 by 2013, operating across 16 Indian
states. Its dedicated sales force grew from 2 reps (1997) to 8 (2002) to 28
(2008) to 40 (2013), while total field force (sales + after-sales +
quality) reached 58. Net revenue rose from INR 170M (2009) to INR 363M
(2013).

Two structural episodes anchor the case:

1. **The 2009 restructuring failure.** To reduce travel burden, the company
   moved from a product-specialist structure to a pure **geographic**
   structure. This backfired in Haryana — the company's highest-client
   region — where generalist reps could not answer product-specific
   technical questions across the full portfolio, costing the company
   credibility and deals. This is the case's central cautionary example:
   optimizing for one thing (travel cost) broke another (technical
   coverage depth).
2. **The 2014 new-product dilemma.** By 2014 the company had designed a new
   product — internally called the "dumb waiter" — for launch in October
   2014, aimed at a somewhat different buyer (builders/real estate rather
   than industrial turnkey buyers) with a shorter, more transactional deal
   cycle. Leadership had to decide: route it through the existing
   generalist sales force, or stand up a dedicated pod for it?

One thing the case does **not** show is a sales force outgrowing revenue:
reps grew about 1.4× (2008–2013) while revenue grew about 2.1×. The case's
tension is structural, not a cost blow-out. This project's Module A
therefore runs on an invented stress scenario, and says so.

The case leaves both structural questions open-ended, meant to be argued in
a classroom discussion. This project instead **answers them computationally**
— not by re-litigating the case narrative, but by building a general-purpose
toolkit that could answer the same class of question for any B2B sales
organization facing a coverage-structure or new-product-motion decision, and
then applying it to a dataset generalized from Lakshmi Projects.

## 3. What this project is

A sales-organisation design tool with five modules and an economics layer,
run as one chain by `run_pipeline.py`:

```
A Diagnostic Engine   → is sales cost outrunning growth?
B Coverage Simulator  → which structure is cheapest in total?
C Territory Optimizer → optimises B's structure: how many reps, who owns what
D GTM Scorer          → how to sell the new product (uses a rep freed by C)
$ Economics           → before/after metrics, transition cost, payback, rollout
E Dashboard           → re-runs A, B and D live from sliders
```

Each module's output feeds the next. B's recommended structure is the one
C optimises. C's freed reps staff D's chosen route. C and D together drive
the economics. The rollout plan's KPIs say when to re-run A.

The project is built to be **re-run every planning cycle** with real data
replacing the stated assumptions. It is not a report read once.

It is **optimisation and simulation, not machine learning**: ratio
analysis, rule-based simulation, mixed-integer optimisation and a
transparent scoring formula. That pairs with the ML-based Revenue Pipeline
Capstone. It also fits the questions: there is no historical
launch-outcome data to train a classifier for the new-product decision, so
a transparent formula plus explicit economics is more honest than a black
box.

### Revision note

A critical review of the first version found that its headline numbers
came mostly from data-construction choices, not analysis:
- "38 reps, not 119; 70.9% cheaper" rested on an unsourced capacity figure
  and a baseline that counted idle reps as free.
- Travel was free.
- The pod payback treated annual salaries as a one-time cost.
- The case's headcount pattern was described backwards.

Version 2 rebuilt each of these. The before-and-after is tabulated at the
top of `docs/business_insights.md`.

Version 3 added the MBA frameworks that change a number or a decision:
- revenue decomposition and operating leverage (A)
- Theory of Constraints shadow prices (C)
- the B2B buying centre (B, C, D)
- service output demands, trade terms and push vs pull (D)
- TAM / SAM / SOM and distribution intensity (D)
- EVC pricing (D).

Frameworks that would only decorate are listed as deliberately left out.

## 4. The questions this project answers

| # | Question | Module | Method | Answer |
|---|---|---|---|---|
| A | Is sales cost outrunning growth, and why? | `src/diagnostics.py` | Ratio analysis, 200-history test, revenue decomposition, operating leverage | Yes. Warning in 2020, breach in 2022 (99% of breaches caught, 24% false alarms). Revenue per rep fell 40%, all from reps covering 46% fewer accounts. Operating leverage rose from 1.6 to 14 |
| B | Which structure covers the book at the lowest total cost? | `src/coverage_simulator.py` | Rule-based simulation, all costs in rupees, buying-centre-based expertise risk, 100-dataset robustness | Geographic, with engineering-led accounts matched to in-region expertise. Product Specialist ~25% dearer; Hybrid ties |
| C | How many reps, who owns what, and where is the bottleneck? | `src/territory_optimizer.py` | Mixed-integer optimisation vs. as-is and greedy baselines; shadow prices | 45 reps (from 56): +2 into Haryana, −13 elsewhere; 248 accounts move. Haryana is the only binding constraint |
| D | How should the new product be sold, and at what price? | `src/gtm_scorer.py` | Fit score (buying centre), service outputs, TAM/SAM/SOM, four-option economics, EVC | Channel partners (~8 dealers). The market caps a pod. Price sits ~₹0.8 lakh below the competitor median |
| $ | Does the redesign pay? | `src/economics.py` | Before/after, transition cost, two release paths × three cases | ₹12.3M a year saved; ₹4.6M one-time; payback month 6 |
| E | Which assumptions would change the answers? | `dashboard/app.py` + what-if tables | Live sliders, precomputed sweeps | Selling hours per rep (±7 reps), expertise loss, Dumb Waiter price |

## 5. Module detail

### Shared foundation — `src/assumptions.py`

Every operating assumption lives in one file with a base value and a
range. Each is listed in plain language in `docs/assumptions.md`, with
where it is tested. Workload follows the standard **workload build-up**
method for sizing a sales force:

- Hours an account needs per year = visits × (3 h per visit + travel) +
  12 h of admin.
- Visits depend on complexity (4–12 a year) and revenue tier (Key ×1.5,
  Core ×1.0, Small ×0.6).
- Each rep has 990 selling hours a year (225 days × 8 h × 55%), used at
  50–90%.

### Module A — Diagnostic Engine

**Question.** Is sales cost quietly outrunning growth before it shows up in
the numbers leadership watches, and if so, why?

**Method.**
- **Early warning:** cumulative headcount growth running more than 20%
  ahead of cumulative revenue growth.
- **Margin breach:** net margin below half its base-year level.
- **Test:** the warning is scored on 200 generated histories, healthy and
  strained mixed.
- **Decomposition:** revenue per rep = accounts per rep × revenue per
  account. Win rate and repeat rate are left out because there is no
  deal-level data.
- **Operating leverage:** contribution ÷ operating profit, with a what-if
  on converting rep pay to commission.

**Result.**
- Net margin falls from 11.6% to 1.2% while revenue grows 2.1×. Headcount
  grows 3.5×; sales cost goes from 9.6% to 21.4% of revenue.
- Warning in 2020; breach in 2022. Revenue growth never dips below 14%, so
  a revenue-watcher sees nothing.
- At 20%, the warning catches 99% of breaches with 2 years' notice and 24%
  false alarms. At 30%, it catches 91% with 4% false alarms and 1 year's
  notice. Watching revenue catches 34%.
- **Revenue per rep fell 40%.** Accounts per rep fell 46%; revenue per
  account *rose* 11%. The customers didn't weaken; coverage thinned.
- **Operating leverage rose from 1.6 to 14.2.** In 2024 a 10% revenue dip
  would wipe out operating profit. Moving 20% / 40% of rep pay to
  commission brings it to 11.6 / 8.9.

### Module B — Coverage Model Simulator

**Question.** Geographic, Product Specialist or Segmented Hybrid: which
costs least in total?

**Method.** Each structure is a rule for who may serve which account,
filled by a greedy assignment. Total cost is counted in rupees:
- payroll
- travel, costed by distance
- **expertise risk**: margin lost on accounts whose **buying centre
  includes engineering** (250 of 650) when served by a rep without that
  product background. This is the Haryana lesson, tied to the role that
  asks the technical questions.
- margin on any accounts left uncovered.

**Result.**

| Structure | Reps | Travel ₹M | Total ₹M | Engineering-led accounts with expert |
|---|---|---|---|---|
| Geographic | 47 | 7.0 | 58.9 | 71% |
| Segmented Hybrid | 47 | 8.5 | 59.2 | 74% |
| Product Specialist | 53 | 18.1 | 76.8 | 100% |

- **Across 100 generated datasets:** Geographic and Hybrid tie (within 1%)
  65% of the time. Geographic is cheapest outright 31% of the time and
  Hybrid 4%. Product Specialist never wins and costs ~25% more on average.
- **Sweeping travel cost and expertise loss:** Hybrid leads only when
  travel is at half its base cost. Product Specialist is at least 15%
  dearer everywhere.

### Module C — Territory Optimizer

**Question.** Under B's structure, how many reps does the book need, who
should own each account, and where is the bottleneck?

**Method.** A mixed-integer program in PuLP (CBC), solved region by region.
- **Decides:** which reps to keep, and which rep owns each account.
- **Minimises:** payroll, travel, expertise risk, and a **continuity
  charge** (5% of an account's yearly margin when it changes owner).
- **Rules:**
  - every account has exactly one owner
  - every kept rep works 50–90% of selling hours
  - a short region can take a relocated rep at ₹150K.
- **Theory of Constraints:** shadow prices give the value of one more
  selling hour in each region. The keep/release decisions are fixed first,
  then the assignment is re-solved continuously; one-extra-rep re-solves
  cross-check the result.

**Result.**

| Method | Reps | Total ₹M | Accounts moved | Rep load |
|---|---|---|---|---|
| As-is | 56 | 68.3 | 0 | 5%–223% |
| Greedy | 49 | 60.0 | 548 | 4%–90% |
| **Optimiser** | **45** | **55.7** | **248** | **50%–90%** |
| Optimiser ignoring owners | 45 | 55.4 | 543 | 50%–90% |

- **The optimiser beats greedy** by ₹4.3M (7%), uses 4 fewer reps and
  moves 300 fewer accounts.
- **Haryana is the one binding constraint today.** It is 1,160 hours short,
  and one more selling hour is worth ₹978 (₹0 in most regions). After the
  redesign that falls to ₹202.
  - **Caveat:** a full extra rep there recovers ~₹4.3 lakh of margin a
    year, less than a rep costs. The relocations rest on the policy of
    covering every account.
- **Selling hours per rep is the dominant assumption:** 750 / 850 / 990 /
  1,100 / 1,200 hours need 56 / 52 / 45 / 40 / 38 reps.
- **Trade-off:** expert coverage of engineering-led accounts falls from
  79% to 69%, or 71% if the optimiser assumes a 25% expertise loss
  (₹0.8M more a year).

### Module D — New-Product GTM Scorer

**Question.** How should the Dumb Waiter be sold, and at what price?

**Method.**

1. **Fit score.** Three distances from the data:
   - **buyer distance:** overlap in **buying-centre roles**: architects,
     project managers, owners and F&B heads vs. plant heads, engineering,
     procurement and finance
   - complexity distance
   - deal-cycle distance

   Weighted 0.40 / 0.35 / 0.25; 0.5 or more means a poor fit.
2. **Service output demands.** Five buyer needs, weighted, with each route
   scored 1–5:
   - local presence
   - installation speed
   - after-sales service
   - single-unit orders
   - technical specification support

   A ±1 sensitivity test checks every score.
3. **Market sizing.** TAM / SAM / SOM is built bottom-up from sourced
   housing, hotel and hospital figures plus stated assumptions
   (`data/market_sizing.csv`). It caps every option's volume and sets the
   dealer count. The reachable market is floored at observed pilot sales.
4. **Economics.** 24 months, four options, each in low, base and high
   cases:
   - existing force
   - dedicated pod (3 redeployed reps)
   - channel partners (10% commission, 45-day credit costed)
   - partners plus an architect-specification programme (pull)
5. **EVC.** Competitor median price plus a differentiation value, against
   the current ticket. The economics are re-run at +20% price.

**Result.**
- **Fit 0.62:** a clear poor fit. Buyer distance is 0.92; procurement is
  the only shared role.
- **Service outputs:** dealers 4.10, pod 3.20, existing force 2.65. No
  single one-point change flips the leader.
- **Market:** TAM ~612 units a year, SOM ~61 (base). That supports ~10
  dealers at 6 installs each, so ~8 is selective distribution.
- **Base case, 24 months:**
  - channel partners ₹1.5M (86 accounts)
  - architect programme ₹0.9M
  - existing force ₹0.7M
  - pod −₹0.1M (capped at the market)
- **No pod win rate beats partners** at today's price.
- **Price:** ₹1.66 lakh vs. a ~₹2.5 lakh competitor median. EVC is ~₹2.7
  lakh, so the headroom is ~₹1.0 lakh. At +20% price, the pod (₹3.5M) and
  partners (₹3.4M) draw level.

**Insight.** The buyer is different, the channel needs point to dealers,
and the market is too small for a pod's extra capacity. But price is the
lever that matters most, so the first year of dealer sales doubles as a
price test.

### Economics

| | Today | Redesigned |
|---|---|---|
| Sales reps | 56 | 45 |
| Cost to serve | ₹67.4M | ₹55.1M |
| Per account | ₹104K | ₹85K |
| % of revenue | 21.4% | 17.5% |
| Revenue per rep | ₹5.6M | ₹7.0M |
| Net margin | 1.2% | 4.1% |

- **One-time cost:** ₹4.6M base (₹2.9M–₹8.8M). That covers severance for
  10 reps, 2 relocations, retraining, and margin lost on 248 handovers.
- **Payback:** month 6 (months 8–10 pessimistic).
- **Recommended path:** a hiring freeze plus attrition, giving up ~₹1.3M
  over 24 months to avoid forced exits.
- **Not computed:** CAC, LTV and ROAS (no marketing or retention data).

### Module E — Scenario Dashboard

Streamlit app, reading `data/results/`:
- **Live:**
  - Module A from two growth sliders: margin, warning and operating
    leverage
  - Module B from travel-cost and expertise-loss sliders
  - Module D from the fit inputs, pod win rate, partner volume and price
- **From the pipeline (too slow to run live):**
  - optimiser baselines, capacity what-if and bottleneck values
  - the 100-dataset robustness test and the 200-history backtest
  - service outputs, market sizing and EVC
  - economics

## 6. Rollout

`docs/rollout_plan.md` sets out the deployment:
1. Fix Haryana first. It is the binding constraint: relocate 2 reps, with
   joint handovers on every engineering-led account.
2. Pilot the reduction in Karnataka South: no complex accounts, 23 moves.
3. Roll out to Gujarat, then Tamil Nadu, then Maharashtra West.
4. In parallel, sign ~8 dealers for the Dumb Waiter on 10% / 45-day terms,
   with a price test toward the market median.

Seven KPIs with trigger levels decide when to re-run the pipeline:
- cost to serve as % of revenue
- accounts per rep
- the Module A ratio
- rep load
- revenue retained on moved accounts
- expert coverage of engineering-led accounts
- partner-sourced accounts

## 7. Tech stack

`Python` · `pandas` / `numpy` · `PuLP` + CBC · `Streamlit` · `Plotly` ·
`Faker` (en_IN)

## 8. The dataset

Synthetic, generated by `data/generate_synthetic_company.py` (seed 42).
Full schema: `data/data_dictionary.md`.

- **regions** (6): complexity index 1–5; Haryana = 5.
- **accounts** (650):
  - region, product line, buyer segment, revenue, complexity, deal cycle
    and current owner
  - about 5% are Dumb Waiter pilot customers won in 2024: builders,
    hotels and hospitals in the big cities, tickets about a third of
    industrial ones, ~45-day cycles.
- **accounts** also carry a **buying centre**: the roles in each
  purchase decision.
- **yearly_accounts** (2019–2024): active accounts, won and lost; feeds
  the decomposition.
- **market_sizing.csv**: TAM/SAM/SOM inputs, each with a source or an
  "Assumption" label.
- **reps** (56): home region, product background (no Dumb Waiter
  specialists yet), fully loaded cost and tenure.
- **yearly_financials** (2019–2024):
  - a full P&L with cost of sales, sales payroll and expenses, other
    opex, depreciation and interest, and tax
  - 2024 sales payroll equals the rep table exactly
  - net margin goes from ~12% to ~1%.

What's real versus invented: `docs/case_reference.md`. Every assumption
and its range: `docs/assumptions.md`.

## 9. Limitations that remain

- **Assumptions drive the biggest answers:** selling hours per rep, the
  expertise-loss rate and the Dumb Waiter price. All three are swept, but
  only visit logs, engineering-led account revenue and real price tests
  can settle them.
- **Module D's market sizing** is sourced for housing, hotels, hospitals
  and competitor price. Adoption shares, restaurant openings and the
  reachable share are assumptions.
- **The service-output scores are judgements.** They are robust to any
  single one-point change, not to several at once.
- **Module D's win rates and partner volumes are assumptions.** Only the
  pilot count (33) is data.
- **The revenue decomposition stops at three terms.** Win rate and repeat
  rate need deal-level data.
- **Module A's 24% false-alarm rate** means it opens reviews rather than
  deciding them.
- **No marketing-funnel data**, so CAC, LTV and ROAS are out of scope.
- **The optimiser takes ~2 minutes per run**, so its sweeps are precomputed.

## 10. Repo layout

```
sales-coverage-optimizer/
├─ run_pipeline.py
├─ data/  generate_synthetic_company.py · data_dictionary.md · sample/ · results/
├─ src/   assumptions.py · diagnostics.py · coverage_simulator.py ·
│         territory_optimizer.py · gtm_scorer.py · economics.py
├─ dashboard/app.py
└─ docs/  business_insights.md · rollout_plan.md · assumptions.md ·
          case_reference.md · project_brief.md · demo_video_script.md
```

## 11. Key numbers (CV / LinkedIn)

- **56 → 45 reps**, with Haryana *up* 2. It is the only binding
  constraint (₹978 per extra selling hour).
- **18% lower cost to serve** (₹12.3M a year); **₹4.6M** one-time cost;
  **payback in month 6**.
- **2 years' early warning** on margin, tested on 200 histories: 99% of
  breaches caught, 24% false alarms.
- **Revenue per rep −40%**, all from coverage thinning (accounts per rep
  −46%, revenue per account +11%).
- **Operating leverage 1.6 → 14**: the sales cost behaves as fixed.
- **Product Specialist costs ~25% more** than Geographic once travel is
  priced.
- **Channel partners** for the new product. The reachable market (~61
  units a year) caps a pod, and price sits ~₹0.8 lakh below the
  competitor median.
