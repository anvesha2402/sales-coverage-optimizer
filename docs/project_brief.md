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

## 4. The questions this project answers

| # | Question | Module | Method | Answer |
|---|---|---|---|---|
| A | Is sales cost outrunning growth? | `src/diagnostics.py` | Ratio analysis + a test on 200 generated histories | Yes. Warning in 2020, margin breach in 2022. The warning catches 99% of breaches ~2 years early, with 24% false alarms |
| B | Which structure covers the book at the lowest total cost? | `src/coverage_simulator.py` | Rule-based simulation, all costs in rupees, 100-dataset robustness | Geographic, with accounts matched to in-region expertise. Product Specialist ~29% dearer; Hybrid ties |
| C | How many reps, and who owns what? | `src/territory_optimizer.py` | Mixed-integer optimisation (PuLP/CBC) vs. as-is and greedy baselines | 45 reps (from 56): +2 into Haryana, −13 elsewhere. 247 accounts move |
| D | How should the new product be sold? | `src/gtm_scorer.py` | Fit score + 24-month, three-option economics | Channel partners. A pod needs a 29% win rate to compete |
| $ | Does the redesign pay? | `src/economics.py` | Before/after, transition cost, two release paths × three cases | ₹12.2M a year saved; ₹4.5M one-time; payback month 6 |
| E | Which assumptions would change the answers? | `dashboard/app.py` + what-if tables | Live sliders, precomputed sweeps | Selling hours per rep (±6 reps) and expertise loss (Geographic vs Hybrid) |

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
the numbers leadership watches?

**Method.** Two separate signals.
- **Early warning:** cumulative headcount growth running more than 20%
  ahead of cumulative revenue growth.
- **Margin breach:** net margin below half its base-year level.

Because the dataset was built to contain this pattern, the rule is also
run on 200 generated histories, healthy and strained mixed. It is scored
against what actually happened in each.

**Result.**
- Net margin falls from 11.6% to 1.2% while revenue grows 2.1×.
  Headcount grows 3.5×, and sales cost goes from 9.6% to 21.4% of revenue.
- Warning in 2020; breach in 2022; score 20/100.
- Revenue growth never dips below 14%, so a revenue-watcher sees nothing.
- On the 200-history test, the warning at 20% catches 99% of breaches with
  a median 2 years' notice and 24% false alarms. At 30% it catches 91%
  with 4% false alarms and 1 year's notice. Watching revenue catches 34%.

**Use.** A quarterly indicator that opens a review: 20% means
investigate, 30% means act. It should not trigger a restructuring on its
own.

### Module B — Coverage Model Simulator

**Question.** Geographic, Product Specialist or Segmented Hybrid: which
costs least in total?

**Method.** Each structure is a rule for who may serve which account. A
greedy assignment (biggest accounts first, cheapest eligible rep with
room) fills it. Total cost is counted in one currency:
- payroll of reps needed
- travel, with cross-region trips costed by distance
- **expertise risk**: margin expected to be lost on complex accounts
  served by someone without that product background. This is the Haryana
  lesson, priced.
- margin on any accounts left uncovered.

The Hybrid's specialist overlay is sized from the complex-account
workload, not set at a random 30%.

**Result.**

| Structure | Reps | Travel ₹M | Total ₹M | Complex accounts with expert |
|---|---|---|---|---|
| Geographic | 45 | 7.0 | 56.5 | 70% |
| Segmented Hybrid | 45 | 7.6 | 56.5 | 72% |
| Product Specialist | 53 | 18.1 | 76.8 | 100% |

Across 100 generated datasets, Geographic and Hybrid tie (within 1%) 73%
of the time. Geographic is cheapest outright 21% of the time and Hybrid
6%. Product Specialist never wins. Sweeping travel cost (0.5–2×) and
expertise loss (0–100%), Hybrid leads only when travel is cheap and
expertise loss is 10% or more, and never by more than 3%.

**Insight.** Pricing travel reverses the first version's answer. Most
regions already have reps with product backgrounds, so matching complex
accounts to them inside each region captures most of the expertise without
the travel.

### Module C — Territory Optimizer

**Question.** Under B's structure, how many reps does the book need, and
who should own each account?

**Method.** A mixed-integer program in PuLP (CBC), solved region by region.
- **Decides:** which reps to keep, and which rep owns each account.
- **Minimises:**
  - payroll
  - travel and expertise risk
  - a **continuity charge**: 5% of an account's yearly margin when it
    moves away from its current owner.
- **Rules:**
  - every account has exactly one owner
  - every kept rep works 50–90% of selling hours
  - a region short of capacity can take a rep relocated from elsewhere at
    ₹150K.

Compared against today's actual assignment, a greedy rule, and itself
without the continuity charge.

**Result.**

| Method | Reps | Total ₹M | Accounts moved | Rep load |
|---|---|---|---|---|
| As-is | 56 | 68.0 | 0 | 5%–223% |
| Greedy | 47 | 57.6 | 558 | 5%–90% |
| **Optimiser** | **45** | **55.5** | **247** | **51%–90%** |
| Optimiser ignoring owners | 45 | 55.3 | 551 | 53%–90% |

- **Haryana is short by 2 reps.** One rep there is at 223% of selling
  hours. Tamil Nadu has 5 surplus reps, and Maharashtra and Gujarat 3 each.
- **The optimiser adds little on cost and a lot on continuity.** It is
  ₹2.1M (3.6%) cheaper than greedy and moves 311 fewer accounts.
- **Selling hours per rep is the dominant assumption.** At 750 / 850 /
  990 / 1,100 / 1,200 hours, the team needs 56 / 51 / 45 / 40 / 38 reps.
- **Trade-off:** expert coverage of complex accounts falls from 80% to 67%
  at base settings, or to 73% if the optimiser assumes a 25% expertise loss.

### Module D — New-Product GTM Scorer

**Question.** How should the Dumb Waiter be sold?

**Method.** Two steps.

1. **Fit score.** Three distances computed from the data:
   - buyer distance: buyer-segment overlap, regional mix and ticket size
   - complexity distance
   - deal-cycle distance (from the `deal_cycle_days` field)

   These are weighted 0.40 / 0.35 / 0.25. A score of 0.5 or more means a
   poor fit for the existing motion.
2. **Economics.** A 24-month, month-by-month model of three options,
   compared on gross margin after their own costs:
   - **Existing sales force:** rep time is costed.
   - **Dedicated pod:** 3 reps redeployed from those C frees, so severance
     is avoided but salaries continue.
   - **Channel partners:** lift dealers, with commission and one
     redeployed rep as partner manager.

   Each option is run in low, base and high cases, plus the pod's
   break-even win rate.

**Result.**
- **Fit 0.52**: a borderline poor fit. Buyer 0.66, complexity 0.37, deal
  cycle 0.50.
- **Base case, 24 months:**
  - channel partners ₹1.7M (86 accounts)
  - existing force ₹0.7M (66)
  - pod ₹0.5M (127)
- Partners also lead in the pessimistic case; the pod leads only in the
  optimistic one. The pod needs a 29% win rate (25% assumed) to beat
  partners.

**Insight.** The pod wins the most accounts but can't cover three salaries
on ₹166K tickets. "Pod or existing force" was a false choice. For a
small-ticket product sold to builders, dealers who already call on
builders are the cheaper route.

### Economics

| | Today | Redesigned |
|---|---|---|
| Sales reps | 56 | 45 |
| Cost to serve | ₹67.4M | ₹55.1M |
| Per account | ₹104K | ₹85K |
| % of revenue | 21.4% | 17.5% |
| Revenue per rep | ₹5.6M | ₹7.0M |
| Net margin | 1.2% | 4.1% |

- **One-time cost:** ₹4.5M base (₹2.8M–₹8.6M). That covers severance for
  10 reps, 2 relocations, retraining, and margin lost on 247 handovers.
- **Payback:** month 6 in the base case, months 8–10 in the pessimistic
  case.
- **Recommended path:** a hiring freeze plus attrition. It gives up about
  ₹1.2M over 24 months versus releasing now, in exchange for no forced
  exits.
- **Not computed:** CAC, LTV and ROAS. There is no marketing-spend or
  retention data, so these would be invented.

### Module E — Scenario Dashboard

Streamlit app, reading `data/results/`:
- **Live:**
  - Module A from two growth sliders
  - Module B from travel-cost and expertise-loss sliders
  - Module D from the three fit inputs, pod win rate and partner volume
- **From the pipeline (too slow to run live):**
  - optimiser baselines and the capacity what-if
  - the 100-dataset robustness test and the 200-history backtest
  - economics

## 6. Rollout

`docs/rollout_plan.md` sets out the deployment:
1. Fix Haryana first: relocate 2 reps, with joint handovers on every
   complex account.
2. Pilot the reduction in Karnataka South: no complex accounts, 21 moves.
3. Roll out to Gujarat, then Tamil Nadu, then Maharashtra West.
4. In parallel, set up the dealer channel for the Dumb Waiter.

Six KPIs with trigger levels decide when to re-run the pipeline:
- cost to serve as % of revenue
- the Module A ratio
- rep load
- revenue retained on moved accounts
- expert coverage of complex accounts
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

- **Selling hours per rep and the expertise-loss rate are assumptions**,
  and they drive the two biggest answers. Both are swept, but only real
  visit logs and complex-account revenue history can settle them.
- **Module D's win rates and partner volumes are assumptions.** Only the
  pilot account count is data.
- **Module A's 24% false-alarm rate** at the chosen threshold means it
  opens reviews rather than deciding them.
- **No marketing-funnel data**, so CAC, LTV and ROAS are out of scope by
  design.
- **The optimiser's solve time** (about 2 minutes per run) keeps it out of
  the live dashboard; its sweeps are precomputed.
- **MBA frameworks are used only where they change a number:** workload
  build-up, account segmentation and option economics. Porter, VRIO and
  others were not added for show.

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

- **56 → 45 reps**, with Haryana *up* 2. The problem was distribution, not
  only size.
- **18% lower cost to serve** (₹12.2M a year); **₹4.5M** one-time cost;
  **payback in month 6**.
- **2 years' early warning** on margin, tested on 200 histories: 99% of
  breaches caught, 24% false alarms.
- **Product Specialist costs ~29% more** than Geographic once travel is
  priced. The tested "specialist" instinct was wrong.
- **Channel partners** beat a dedicated pod for the new product, unless
  the pod's win rate exceeds 29%.
