# Sales Coverage & GTM Structure Optimizer

**Status: Stage 3 — Product Layer: the Dashboard (built, deploy to Streamlit Community Cloud pending)**

A sales-org design simulator that diagnoses, models, optimizes, and scores
coverage-structure decisions — generalized from the Ivey case *Lakshmi
Projects: Sales Structure Dilemma* (W15219) — instead of just narrating them
in a write-up.

> One-line problem statement + headline insight go here once Modules A–D
> produce real numbers (Stage 2).

## Source case

Generalized from **Lakshmi Projects: Sales Structure Dilemma (W15219)**,
Ivey Publishing, 2015 — a Delhi-based bulk-material-handling-equipment (BMHE)
manufacturer whose sales force grew from 2 reps (1997) to 58 field staff
(2013) while revenue grew from INR170M (2009) to INR363M (2013), and whose
2009 geography-only restructuring caused a documented multi-product coverage
failure (Haryana region). See `docs/case_reference.md` for the full credit
and what's synthetic vs. case-derived.

## 1. System Architecture — Five Modules

```
Diagnostic Engine → Coverage Model Simulator → Territory Optimizer
→ New-Product GTM Scorer → Scenario Dashboard → (loops back to Diagnostic Engine)
```

| Module | What It Does | Output |
|---|---|---|
| A. Diagnostic Engine | Flags structural strain before it hits the P&L | Sustainability score + danger-threshold year |
| B. Coverage Model Simulator | Scores specialist vs. geographic vs. hybrid structures | Quantified trade-off table |
| C. Territory Optimizer | Assigns accounts to reps/pods | Territory map + % improvement over naive baseline |
| D. New-Product GTM Scorer | Dedicated pod vs. existing sales force | Recommendation + breakeven-time comparison |
| E. Scenario Dashboard | Stress-tests the recommendation | Sensitivity band |

## 2. The Five Business Questions

Every table and column in `/data` traces back to one of these.

1. **Diagnostic Engine** — Is the sales org structurally sustainable, or is
   cost quietly outrunning growth before it shows up in the numbers
   leadership actually watches?
   - *Hypothesis:* headcount-growth ÷ revenue-growth is a leading indicator
     of margin pressure — it moves before the growth-target miss does.
   - *Insight to derive:* the exact year the ratio crosses a sustainability
     threshold, computed from `yearly_financials`.
2. **Coverage Model Simulator** — Which structure (product-specialist,
   geographic, or segmented hybrid) actually minimizes cost while holding
   coverage and specialization depth?
   - *Hypothesis:* a segmented hybrid beats both pure models on a combined
     score, not just on paper.
3. **Territory Optimizer** — Given a fixed rep count and account base, how
   should accounts be assigned to reps to minimize cost without breaking
   coverage?
   - *Hypothesis:* constrained optimization beats naive equal-split on
     cost-per-account-covered.
4. **New-Product GTM Scorer** — Should a new product go through the existing
   sales force or a dedicated pod?
   - *Hypothesis:* buyer-persona distance and technical-complexity distance
     from the existing motion predict whether a generalist rollout fails —
     exactly what sank Lakshmi's 2009 undifferentiated rollout.
5. **Scenario Dashboard** — Does the recommended structure hold up across a
   range of plausible futures, or only under the exact conditions it was
   designed for?
   - *Hypothesis:* the hybrid structure stays cost-effective across most
     growth scenarios but breaks down past some specialization threshold.

## Repo layout

```
sales-coverage-optimizer/
├─ data/
│  ├─ generate_synthetic_company.py
│  ├─ data_dictionary.md
│  └─ sample/          (small CSV previews — full set is generated, not committed)
├─ notebooks/           (Stage 2)
├─ src/                 (Stage 2)
├─ dashboard/           (Stage 3)
└─ docs/
   └─ case_reference.md
```

## How to run it locally

```bash
pip install -r requirements.txt
python data/generate_synthetic_company.py
```
Generates `regions.csv`, `accounts.csv`, `reps.csv`, and
`yearly_financials.csv` into `data/generated/` (gitignored — regenerate
any time; a small preview of each lives in `data/sample/`).
