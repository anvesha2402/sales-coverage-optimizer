# Sales Coverage & GTM Structure Optimizer

**Live demo:** [sales-coverage-optimizer-x3momyht3cgit6ck7jkarz.streamlit.app](https://sales-coverage-optimizer-x3momyht3cgit6ck7jkarz.streamlit.app)

Optimized territory assignment cuts cost-to-serve by **70.9%** versus a naive
equal-split baseline, and flags that the sales org's headcount was already
growing 2.6x faster than revenue a full year before margin compression
became visible on the P&L. A sales-org design simulator that diagnoses,
models, optimizes, and scores coverage-structure decisions — generalized
from the Ivey case *Lakshmi Projects: Sales Structure Dilemma* (W15219) —
instead of just narrating them in a write-up.

## Architecture

```
Diagnostic Engine → Coverage Model Simulator → Territory Optimizer
→ New-Product GTM Scorer → Scenario Dashboard → (loops back to Diagnostic Engine)
```

The loop back to the Diagnostic Engine is deliberate: this is built to be
re-run every planning cycle, not read once as a static report.

## The five business questions — and what the code found

| # | Question | Answer |
|---|---|---|
| 1 | Is the sales org structurally sustainable? | **No.** Sustainability score 14/100. Net margin crosses below 10% in **2023** — a full year before the worst YoY revenue print, because headcount grew 5.41x against 2.10x revenue (module: `src/diagnostics.py`) |
| 2 | Which coverage structure minimizes cost while holding coverage and depth? | **Product Specialist**, on this data — cheapest (₹35.6M), zero coverage gap, full specialization depth. Segmented Hybrid did *not* win, tested across a 30–60% specialist-share sweep (module: `src/coverage_simulator.py`) |
| 3 | How should accounts be assigned to reps to minimize cost? | **38 reps, not 119** — a real MILP solved per region cuts cost-to-serve 70.9% vs. naive equal-split at identical 100% coverage (module: `src/territory_optimizer.py`) |
| 4 | Should the new product go through the existing sales force or a dedicated pod? | **Existing sales force** (GTM score 0.29 of 1.0) — though a pod would break even in 2.4 months if built anyway; two different questions, both answered (module: `src/gtm_scorer.py`) |
| 5 | Does the recommendation hold across plausible futures? | Explored live in the dashboard — sliders recompute Modules A, B, and D in real time; the coverage-model comparison is visibly jagged (a real property of the greedy heuristic, not noise) (module: `dashboard/app.py`) |

## Tech stack

`Python` · `pandas` / `numpy` (diagnostics & simulation) · `PuLP` (territory
optimization, MILP) · `Streamlit` (dashboard) · `Plotly` (charts) · `Faker`
(synthetic data)

Deliberately optimization/simulation-based rather than ML — paired with a
predictive-ML capstone elsewhere in the portfolio, "predictive" and
"prescriptive" read as a stronger combination than two ML projects doing
the same trick twice.

## Key results

- **70.9%** lower cost-to-serve from the territory optimizer vs. naive
  equal-split (₹38.2M vs. ₹131.3M), at identical 100% coverage
- **2023** — the year the diagnostic engine's margin threshold is breached,
  a year ahead of the worst headline revenue print
- **2.4 months** — breakeven for a dedicated GTM pod on the new product,
  even though the weighted-scoring formula recommends against building one

## How to run it locally

```bash
pip install -r requirements.txt
python data/generate_synthetic_company.py   # optional -- the dashboard self-generates on first run
streamlit run dashboard/app.py
```

## Synthetic data disclosure

All company, account, and rep data is synthetic, generalized from a real
Ivey business case (**W15219**, Lakshmi Projects: Sales Structure Dilemma).
No real company export was used. Full disclosure of what's real vs.
synthetic — and exactly how the headcount/revenue mismatch was
constructed — in `docs/case_reference.md`.

## What I'd change with a real CRM/HRIS export

Actual account-level revenue and account-rep assignment history (to
validate the Territory Optimizer's baseline against what was really done),
real compensation bands by region (currently modeled, not sourced), real
deal-cycle data for the GTM Scorer (currently the least-grounded input in
the build — see `src/gtm_scorer.py`), and a longer financial history to
test the Diagnostic Engine's threshold-year claim out of sample.

## Repo layout

```
sales-coverage-optimizer/
├─ README.md
├─ requirements.txt
├─ data/
│  ├─ generate_synthetic_company.py
│  ├─ data_dictionary.md
│  └─ sample/               (small CSV previews -- full set is generated, not committed)
├─ src/
│  ├─ diagnostics.py         (Module A)
│  ├─ coverage_simulator.py  (Module B)
│  ├─ territory_optimizer.py (Module C, PuLP)
│  └─ gtm_scorer.py          (Module D)
├─ dashboard/
│  └─ app.py                 (Module E, Streamlit)
└─ docs/
   ├─ case_reference.md
   └─ business_insights.md   (the five answers above, with full reasoning)
```
