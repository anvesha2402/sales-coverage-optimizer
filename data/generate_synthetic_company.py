"""
generate_synthetic_company.py

Builds a synthetic sales-org dataset generalized from the Lakshmi Projects
case (Ivey W15219), for the Sales Coverage & GTM Structure Optimizer.

DISCLOSURE: This is synthetic data. No real company export was used.
- The company, regions, accounts, reps and current account owners are
  invented.
- The headcount trajectory (16 -> 56 sales reps, 3.5x, against 2.1x revenue)
  is a STRESS SCENARIO invented to test the Diagnostic Engine. The real case
  shows the opposite (reps ~1.4x vs revenue ~2.1x). See docs/case_reference.md.
- The Dumb Waiter is modelled the way the case describes it: a smaller,
  simpler product sold to builders, hotels and hospitals in cities, with a
  shorter deal cycle. Its ~5% of accounts are pilot customers won in the
  launch year (2024) by the existing sales force.

Produces five tables into --outdir (default: data/generated/):
    regions.csv, accounts.csv, reps.csv, yearly_financials.csv
    (accounts.csv carries the current owner, `current_rep_id`)

Usage:
    python data/generate_synthetic_company.py [--seed 42] [--outdir data/generated]

`generate(seed)` is also importable, so the robustness analysis in
src/coverage_simulator.py can draw 100 alternative account bases.
"""

import argparse
import os

import numpy as np
import pandas as pd

YEARS = list(range(2019, 2025))
BASE_REVENUE_INR_M = 150.0
REVENUE_GROWTH_MULTIPLE = 2.1
BASE_SALES_HEADCOUNT = 16
FINAL_SALES_HEADCOUNT = 56          # 3.5x -- stress scenario, see disclosure
N_ACCOUNTS = 650

REGIONS = [
    # name, state, complexity_index (1 = standard accounts, 5 = technically
    # demanding multi-product accounts -- Haryana-style, per the case)
    ("Delhi NCR", "Delhi", 3),
    ("Haryana Belt", "Haryana", 5),
    ("Maharashtra West", "Maharashtra", 4),
    ("Gujarat Industrial Corridor", "Gujarat", 3),
    ("Karnataka South", "Karnataka", 2),
    ("Tamil Nadu Coastal", "Tamil Nadu", 3),
]
REGION_COST_OF_LIVING = {"R01": 1.15, "R02": 1.00, "R03": 1.20, "R04": 1.05, "R05": 1.10, "R06": 0.95}

CORE_LINES = ["Conveyor Systems", "Elevator Systems", "Bulk Material Handling"]
NEW_PRODUCT = "Dumb Waiter (New Product)"
PRODUCT_LINES = CORE_LINES + [NEW_PRODUCT]
CORE_LINE_WEIGHTS = [0.45, 0.34, 0.21]
NEW_PRODUCT_SHARE = 0.05

# Industrial buyers spread across regions in proportion to industrial
# activity; Dumb Waiter buyers (builders, hotels, hospitals) cluster in the
# big cities.
DW_REGION_WEIGHTS = {"R01": 0.30, "R02": 0.05, "R03": 0.30, "R04": 0.05, "R05": 0.20, "R06": 0.10}
DW_BUYER_SEGMENTS = (["Builder / real estate", "Hotel / restaurant", "Hospital"], [0.55, 0.30, 0.15])
CORE_BUYER_SEGMENTS = (["Cement / steel / mining", "Ports / logistics", "Food / process plant"],
                       [0.50, 0.20, 0.30])

# Typical first-meeting-to-order cycle, days (CRM-style field; synthetic)
DEAL_CYCLE_MEAN_DAYS = {"Conveyor Systems": 95, "Elevator Systems": 80,
                        "Bulk Material Handling": 105, NEW_PRODUCT: 45}

# P&L structure (share of revenue unless stated)
COST_OF_SALES_SHARE = (0.58, 0.60)   # first year -> last year (gross margin 42% -> 40%)
OTHER_OPEX_SHARE = 0.13               # admin, after-sales, design, quality
DEPRECIATION_INTEREST_SHARE = 0.04
TAX_RATE = 0.25
SALES_EXPENSE_LOADING = 0.12          # travel, phones, incentives on top of payroll
REP_COST_INFLATION = 0.06


def build_regions():
    df = pd.DataFrame(REGIONS, columns=["region_name", "state", "complexity_index"])
    df.insert(0, "region_id", [f"R{i+1:02d}" for i in range(len(df))])
    return df


def build_accounts(rng, regions_df, names=None):
    region_ids = regions_df["region_id"].tolist()
    cx = dict(zip(regions_df["region_id"], regions_df["complexity_index"]))

    is_new = rng.random(N_ACCOUNTS) < NEW_PRODUCT_SHARE
    n_new = int(is_new.sum())
    n_core = N_ACCOUNTS - n_new

    core_w = np.array([cx[r] for r in region_ids], dtype=float)
    core_w /= core_w.sum()
    region = np.empty(N_ACCOUNTS, dtype=object)
    region[~is_new] = rng.choice(region_ids, size=n_core, p=core_w)
    region[is_new] = rng.choice(region_ids, size=n_new, p=[DW_REGION_WEIGHTS[r] for r in region_ids])

    product = np.empty(N_ACCOUNTS, dtype=object)
    product[~is_new] = rng.choice(CORE_LINES, size=n_core, p=CORE_LINE_WEIGHTS)
    product[is_new] = NEW_PRODUCT

    segment = np.empty(N_ACCOUNTS, dtype=object)
    segment[~is_new] = rng.choice(CORE_BUYER_SEGMENTS[0], size=n_core, p=CORE_BUYER_SEGMENTS[1])
    segment[is_new] = rng.choice(DW_BUYER_SEGMENTS[0], size=n_new, p=DW_BUYER_SEGMENTS[1])

    # Revenue: lognormal; Dumb Waiter tickets about a third of an industrial
    # account's. Whole book scaled to the final-year company revenue.
    raw = rng.lognormal(mean=1.0, sigma=0.9, size=N_ACCOUNTS)
    raw[is_new] *= 0.35
    revenue = raw / raw.sum() * (BASE_REVENUE_INR_M * REVENUE_GROWTH_MULTIPLE * 1e6)

    # Complexity: industrial accounts follow their region; Dumb Waiter is a
    # standardised product (mostly 1-2).
    region_cx = np.array([cx[r] for r in region])
    core_cx = region_cx * 0.6 + 0.8 + rng.normal(0, 0.6, N_ACCOUNTS)
    new_cx = 1.5 + rng.normal(0, 0.5, N_ACCOUNTS)
    complexity = np.clip(np.round(np.where(is_new, new_cx, core_cx)), 1, 5).astype(int)

    cycle = np.array([DEAL_CYCLE_MEAN_DAYS[p] for p in product]) * rng.lognormal(0, 0.25, N_ACCOUNTS)

    core_years = YEARS
    w = np.linspace(0.6, 1.4, len(core_years))
    acq = rng.choice(core_years, size=N_ACCOUNTS, p=w / w.sum())
    acq[is_new] = YEARS[-1]   # pilot customers, launch year

    return pd.DataFrame({
        "account_id": [f"A{i+1:04d}" for i in range(N_ACCOUNTS)],
        "account_name": names if names is not None else [f"Account {i+1:04d}" for i in range(N_ACCOUNTS)],
        "region_id": region,
        "product_line": product,
        "buyer_segment": segment,
        "annual_revenue_inr": revenue.round(0),
        "complexity_score": complexity,
        "deal_cycle_days": cycle.round(0).astype(int),
        "acquisition_year": acq,
    })


def build_reps(rng, regions_df, accounts_df, names=None):
    """56 reps. Regional headcount follows account count loosely, with the
    historical over-hiring landing unevenly (noise), at least 3 per region.
    No one specialises in the Dumb Waiter yet -- it is a new product."""
    region_ids = regions_df["region_id"].tolist()
    share = accounts_df["region_id"].value_counts(normalize=True).reindex(region_ids).fillna(0).values
    noisy = share * rng.lognormal(0, 0.20, len(region_ids))
    counts = np.maximum(3, np.round(noisy / noisy.sum() * FINAL_SALES_HEADCOUNT)).astype(int)
    while counts.sum() != FINAL_SALES_HEADCOUNT:
        i = int(np.argmax(counts)) if counts.sum() > FINAL_SALES_HEADCOUNT else int(np.argmax(noisy))
        counts[i] += -1 if counts.sum() > FINAL_SALES_HEADCOUNT else 1

    rep_region = np.repeat(region_ids, counts)
    n = len(rep_region)
    specialization = rng.choice(CORE_LINES + ["Generalist"], size=n, p=[0.30, 0.25, 0.15, 0.30])
    tenure = rng.integers(0, 7, size=n)
    col = np.array([REGION_COST_OF_LIVING[r] for r in rep_region])
    cost = (900_000 * col * (1 + 0.04 * tenure) + rng.normal(0, 25_000, n)).round(0)

    return pd.DataFrame({
        "rep_id": [f"REP{i+1:03d}" for i in range(n)],
        "rep_name": names if names is not None else [f"Rep {i+1:03d}" for i in range(n)],
        "region_id": rep_region,
        "specialization": specialization,
        "annual_cost_inr": cost,
        "tenure_years": tenure,
        "hire_year": YEARS[-1] - tenure,
    })


def assign_current_owners(rng, accounts_df, reps_df):
    """Today's (unplanned) assignment: each account sits with a rep in its
    region -- a product-matched rep 70% of the time if one exists, otherwise
    whoever picked it up. This is the as-is baseline Module C starts from."""
    by_region = reps_df.groupby("region_id")
    owners = []
    for _, a in accounts_df.iterrows():
        local = by_region.get_group(a["region_id"])
        matched = local[local["specialization"] == a["product_line"]]
        pool = matched if (len(matched) and rng.random() < 0.7) else local
        owners.append(pool["rep_id"].iloc[rng.integers(0, len(pool))])
    out = accounts_df.copy()
    out["current_rep_id"] = owners
    return out


def build_yearly_financials(rng, reps_df):
    n = len(YEARS)
    t = np.linspace(0, 1, n)
    revenue = BASE_REVENUE_INR_M * (REVENUE_GROWTH_MULTIPLE ** t) * (1 + rng.normal(0, 0.015, n))
    revenue[0], revenue[-1] = BASE_REVENUE_INR_M, BASE_REVENUE_INR_M * REVENUE_GROWTH_MULTIPLE

    hc_mult = FINAL_SALES_HEADCOUNT / BASE_SALES_HEADCOUNT
    sales_hc = np.round(BASE_SALES_HEADCOUNT * hc_mult ** (t ** 0.75)).astype(int)
    sales_hc[-1] = len(reps_df)

    # Tie the P&L to the rep table: final-year payroll is the actual sum of
    # reps.csv; earlier years deflate the average cost per rep at 6%/yr.
    final_payroll_m = reps_df["annual_cost_inr"].sum() / 1e6
    avg_cost_final = final_payroll_m / len(reps_df)
    avg_cost = avg_cost_final / (1 + REP_COST_INFLATION) ** np.arange(n - 1, -1, -1)
    payroll = sales_hc * avg_cost
    payroll[-1] = final_payroll_m
    sales_opex = payroll * (1 + SALES_EXPENSE_LOADING)

    cos_share = np.linspace(*COST_OF_SALES_SHARE, n)
    cost_of_sales = revenue * cos_share
    other_opex = revenue * OTHER_OPEX_SHARE
    dep_int = revenue * DEPRECIATION_INTEREST_SHARE
    pbt = revenue - cost_of_sales - sales_opex - other_opex - dep_int
    tax = np.where(pbt > 0, pbt * TAX_RATE, 0.0)
    net_income = pbt - tax
    total_cost = cost_of_sales + sales_opex + other_opex + dep_int + tax

    return pd.DataFrame({
        "year": YEARS,
        "revenue_inr_m": revenue.round(2),
        "cost_of_sales_inr_m": cost_of_sales.round(2),
        "sales_payroll_inr_m": payroll.round(2),
        "sales_opex_inr_m": sales_opex.round(2),
        "other_opex_inr_m": other_opex.round(2),
        "depreciation_interest_inr_m": dep_int.round(2),
        "tax_inr_m": tax.round(2),
        "total_cost_inr_m": total_cost.round(2),
        "net_income_inr_m": net_income.round(2),
        "sales_headcount": sales_hc,
    })


def generate(seed=42, with_names=False):
    rng = np.random.default_rng(seed)
    regions = build_regions()
    account_names = rep_names = None
    if with_names:
        from faker import Faker
        fake = Faker("en_IN")
        Faker.seed(seed)
        account_names = [fake.company() for _ in range(N_ACCOUNTS)]
        rep_names = [fake.name() for _ in range(FINAL_SALES_HEADCOUNT)]
    accounts = build_accounts(rng, regions, account_names)
    reps = build_reps(rng, regions, accounts, rep_names)
    accounts = assign_current_owners(rng, accounts, reps)
    financials = build_yearly_financials(rng, reps)
    return {"regions": regions, "accounts": accounts, "reps": reps, "yearly_financials": financials}


def main():
    here = os.path.dirname(__file__)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--outdir", default=os.path.join(here, "generated"))
    p.add_argument("--sample-outdir", default=os.path.join(here, "sample"))
    p.add_argument("--sample-rows", type=int, default=15)
    args = p.parse_args()

    tables = generate(args.seed, with_names=True)
    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.sample_outdir, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(os.path.join(args.outdir, f"{name}.csv"), index=False)
        df.head(args.sample_rows).to_csv(os.path.join(args.sample_outdir, f"{name}_sample.csv"), index=False)
        print(f"wrote {name}.csv ({len(df)} rows)")

    f = tables["yearly_financials"]
    print(f"\nSales headcount {f.sales_headcount.iloc[0]} -> {f.sales_headcount.iloc[-1]} "
          f"({f.sales_headcount.iloc[-1] / f.sales_headcount.iloc[0]:.2f}x); revenue "
          f"{f.revenue_inr_m.iloc[0]:.0f}M -> {f.revenue_inr_m.iloc[-1]:.0f}M "
          f"({f.revenue_inr_m.iloc[-1] / f.revenue_inr_m.iloc[0]:.2f}x)")
    print("Net margin by year:", (f.net_income_inr_m / f.revenue_inr_m).round(3).tolist())


if __name__ == "__main__":
    main()
