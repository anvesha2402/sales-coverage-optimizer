# Sales Coverage & GTM Structure Optimizer

**Live demo:** [sales-coverage-optimizer-x3momyht3cgit6ck7jkarz.streamlit.app](https://sales-coverage-optimizer-x3momyht3cgit6ck7jkarz.streamlit.app)

A sales-organisation design tool that diagnoses, simulates, optimises and
prices coverage decisions for a B2B equipment seller. It is generalised
from the Ivey case *Lakshmi Projects: Sales Structure Dilemma* (W15219).
The five modules run as one chain, and the chain is meant to be re-run
every planning cycle.

On the synthetic dataset:
- The redesign takes the sales force from **56 to 45 reps** and cuts cost
  to serve by **18% (₹12.3M a year)**.
- The change itself costs **₹4.6M** and **pays back in month 6**.
- **Haryana is understaffed** even though the company as a whole is
  overstaffed.
- An early-warning ratio flags the margin problem **2 years before** it
  shows in the P&L. In testing it catches 99% of cases, with a stated
  24% false-alarm rate.

## How the modules connect

```
A Diagnostic Engine     is sales cost outrunning growth?            -> early warning + 200-history test
        |
B Coverage Simulator    which structure is cheapest in total?       -> recommends a structure
        |                (payroll + travel + expertise risk)
C Territory Optimizer   optimises THAT structure: how many reps,    -> frees reps, flags short regions
        |                who owns which account
D GTM Scorer            how to sell the new product                 -> redeploys a freed rep
        |
$ Economics             before/after metrics, transition cost,      -> rollout plan + KPIs that
                         payback                                       trigger the next re-run of A
```

`run_pipeline.py` runs the chain end to end and writes every result to
`data/results/`. The Streamlit dashboard reads those results and re-runs
Modules A, B and D live from sliders.

## The questions, and what the code found

| # | Question | Answer |
|---|---|---|
| A | Is sales cost outrunning growth? | **Yes.** Headcount 3.5× vs revenue 2.1×; net margin 11.6% → 1.2%. The warning fires in **2020**, and margin breaches in **2022** (99% of breaches caught on 200 test histories, 24% false alarms). Revenue per rep fell 40%, all of it from reps covering 46% fewer accounts. Operating leverage rose from 1.6 to 14 |
| B | Which structure covers the book at the lowest total cost? | **Geographic, with engineering-led accounts matched to in-region product expertise.** Product Specialist costs ~25% more once travel is priced. The Hybrid ties Geographic in 65% of 100 generated datasets but rarely beats it |
| C | How many reps, and who owns what? | **45 (from 56):** 2 relocated *into* Haryana, 13 fewer elsewhere (net −11). Haryana is the one binding constraint (₹978 per extra selling hour today, ₹0 in most regions). The optimiser beats a greedy rule by 7% on cost and moves 248 accounts instead of 548 |
| D | How should the new product (Dumb Waiter) be sold? | **Channel partners** (~8 lift dealers), managed by one redeployed rep. They also lead on buyers' service needs. The reachable market (~61 units a year) caps a pod's extra capacity. Price is ~₹0.8 lakh below the competitor median; at +20% the pod and partners draw level |
| $ | Does the redesign pay? | **₹12.3M a year saved, ₹4.6M one-time cost, payback month 6** (month 8–10 pessimistic). Cost to serve falls from 21.4% to 17.5% of revenue |

Full reasoning: [`docs/business_insights.md`](docs/business_insights.md).
Rollout sequence and KPIs: [`docs/rollout_plan.md`](docs/rollout_plan.md).

## What makes the numbers checkable

- **Every assumption is in one register with a range**:
  [`docs/assumptions.md`](docs/assumptions.md). The code reads it from
  `src/assumptions.py`.
- **Workload is built up from visits and hours** (the standard method for
  sizing a sales force), not an invented capacity cap.
- **Baselines, not a strawman.** The optimiser is compared against today's
  actual assignment and a simple greedy rule. It is reported where it adds
  little (cost) as well as where it adds a lot (fewer account moves).
- **Robustness:**
  - The structure comparison is re-run on 100 generated datasets.
  - The two most judgement-heavy inputs (travel cost, expertise loss) are
    swept.
  - Headcount is re-solved across selling hours from 750 to 1,200 a year
    (38–56 reps).
- **Results that went against the original hypothesis are kept.** The
  hybrid structure does not win. The dedicated pod does not pay.

## Frameworks, and where each one changes a number

| Framework | Module | What it decides |
|---|---|---|
| Workload build-up (sales-force sizing) | C | How many reps the book needs |
| Revenue decomposition (reps × accounts per rep × revenue per account) | A | Why revenue per rep fell |
| Operating leverage | A | Why margin fell faster than costs rose; the case for variable pay |
| Sales coverage architecture (geographic / specialist / hybrid) | B | Which structure |
| Mixed-integer optimisation + shadow prices (Theory of Constraints) | C | Who owns what; where the bottleneck is |
| B2B buying centre | B, C, D | Which accounts need an expert; how different the new buyer is |
| Service output demands, trade terms, push vs pull | D | Which channel fits the buyer; dealer terms; the architect pull option |
| TAM / SAM / SOM, distribution intensity | D | Caps on every option's volume; how many dealers |
| EVC pricing | D | Price headroom vs. competitors |

Frameworks considered and left out because they would change nothing here
are listed in `docs/business_insights.md`.

## Tech stack

`Python` · `pandas` / `numpy` · `PuLP` + CBC (mixed-integer optimisation)
· `Streamlit` · `Plotly` · `Faker`

The project is optimisation and simulation, not machine learning. It is
paired with a predictive-ML capstone elsewhere in the portfolio.

## How to run it

```bash
pip install -r requirements.txt
python data/generate_synthetic_company.py   # dataset (seed 42)
python run_pipeline.py                      # full chain, ~15 min (results already committed)
streamlit run dashboard/app.py
```

## Synthetic data disclosure

All company, account and rep data is synthetic. The industry, the 2009
Haryana restructuring failure, and the Dumb Waiter dilemma come from the
case.

**The headcount trend does not.** In the case, reps grew about 1.4× while
revenue grew 2.1×. The 3.5× vs 2.1× series here is a stress scenario
invented to test the Diagnostic Engine. That is why the engine is also
judged on 200 histories, half of them healthy. Details:
[`docs/case_reference.md`](docs/case_reference.md).

## What a real CRM/HRIS export would change

- **Visit logs** to measure selling hours per rep, the input that moves
  headcount most (±6 reps).
- **Complex-account revenue history**, to size the expertise-loss rate.
  That one number decides Geographic vs Hybrid.
- **Account-owner history**, to validate the as-is baseline.
- **Real pay bands.**
- **Dumb Waiter lead and win-rate data**, to replace Module D's assumed
  rates.

## Repo layout

```
sales-coverage-optimizer/
├─ run_pipeline.py              runs A → B → C → D → economics, writes data/results/
├─ data/
│  ├─ generate_synthetic_company.py
│  ├─ data_dictionary.md
│  ├─ market_sizing.csv         TAM/SAM/SOM inputs with sources
│  ├─ sample/                   CSV previews (full set is generated)
│  └─ results/                  every module's output (committed)
├─ src/
│  ├─ assumptions.py            every operating assumption, one place
│  ├─ diagnostics.py            Module A
│  ├─ coverage_simulator.py     Module B
│  ├─ territory_optimizer.py    Module C (PuLP)
│  ├─ gtm_scorer.py             Module D
│  └─ economics.py              before/after, transition cost, payback
├─ dashboard/app.py             Module E (Streamlit)
└─ docs/
   ├─ business_insights.md      findings, with what changed and why
   ├─ rollout_plan.md           phasing, owners, KPIs with trigger levels
   ├─ assumptions.md            assumption register with ranges
   ├─ case_reference.md         what's real vs synthetic
   ├─ project_brief.md
   └─ demo_video_script.md
```
