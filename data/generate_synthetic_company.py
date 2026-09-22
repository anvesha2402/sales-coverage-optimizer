"""
generate_synthetic_company.py

Builds a synthetic sales-org dataset generalized from the Lakshmi Projects
case (Ivey W15219), for the Sales Coverage & GTM Structure Optimizer.

DISCLOSURE: This is synthetic data. No real company export was used. The
company, its regions, accounts and reps are invented; the *pattern* they
follow (a sales force that grows materially faster than revenue, one
higher-complexity region, a new product that doesn't fit the existing
motion) is generalized from the case narrative. See docs/case_reference.md.

Produces four tables into --outdir (default: data/generated/):
    regions.csv
    accounts.csv
    reps.csv
    yearly_financials.csv

Usage:
    python data/generate_synthetic_company.py [--seed 42] [--outdir data/generated]
"""

import argparse
import os

import numpy as np
import pandas as pd

try:
    from faker import Faker
except ImportError as e:
    raise SystemExit(
        "Missing dependency 'faker'. Install with: pip install faker"
    ) from e


# ---------------------------------------------------------------------------
# Fixed reference points (design targets, not fitted from data)
# ---------------------------------------------------------------------------
YEARS = list(range(2019, 2025))  # 6-year trajectory, mirrors the case's span
BASE_REVENUE_INR_M = 150.0        # Year 1 net revenue, INR million
REVENUE_GROWTH_MULTIPLE = 2.1     # Year6 / Year1 revenue  (case: 2009->2013 ~2.1x)
BASE_SALES_HEADCOUNT = 22         # Year 1 sales reps
HEADCOUNT_GROWTH_MULTIPLE = 5.4   # Year6 / Year1 sales headcount (scaled-up echo
                                   # of the case's structural-strain pattern)

N_ACCOUNTS = 650
N_REGIONS_ACTIVE = 6

REGIONS = [
    # name, state, complexity_index (1=simple/standard accounts, 5=technically
    # demanding, multi-product accounts -- Haryana-style, per the case)
    ("Delhi NCR", "Delhi", 3),
    ("Haryana Belt", "Haryana", 5),
    ("Maharashtra West", "Maharashtra", 4),
    ("Gujarat Industrial Corridor", "Gujarat", 3),
    ("Karnataka South", "Karnataka", 2),
    ("Tamil Nadu Coastal", "Tamil Nadu", 3),
]

PRODUCT_LINES = [
    "Conveyor Systems",
    "Elevator Systems",
    "Bulk Material Handling",
    "Dumb Waiter (New Product)",
]
# New product gets a small share of the current account base -- it only
# launched recently, matching the case's April 2014 design / Oct 2014 launch.
PRODUCT_LINE_WEIGHTS = [0.42, 0.33, 0.20, 0.05]


def build_regions():
    df = pd.DataFrame(REGIONS, columns=["region_name", "state", "complexity_index"])
    df.insert(0, "region_id", [f"R{i+1:02d}" for i in range(len(df))])
    return df


def build_accounts(rng, fake, regions_df):
    region_ids = regions_df["region_id"].tolist()
    complexity_by_region = dict(
        zip(regions_df["region_id"], regions_df["complexity_index"])
    )

    # Regions with more industrial activity get proportionally more accounts
    # (weight loosely tracks each region's complexity_index, since higher-
    # complexity regions in the case were also the higher-volume ones e.g.
    # Haryana).
    weights = np.array([complexity_by_region[r] for r in region_ids], dtype=float)
    weights = weights / weights.sum()

    account_region = rng.choice(region_ids, size=N_ACCOUNTS, p=weights)
    account_product = rng.choice(
        PRODUCT_LINES, size=N_ACCOUNTS, p=PRODUCT_LINE_WEIGHTS
    )

    # Revenue: lognormal, scaled so the account base sums close to the final
    # year's company revenue (accounts.csv is a snapshot of the *current*
    # book of business, used by Modules B/C).
    raw_revenue = rng.lognormal(mean=1.0, sigma=0.9, size=N_ACCOUNTS)
    final_year_revenue_m = BASE_REVENUE_INR_M * REVENUE_GROWTH_MULTIPLE
    revenue_inr = raw_revenue / raw_revenue.sum() * (final_year_revenue_m * 1_000_000)

    # Complexity score (1-5): region complexity is the base, product line and
    # noise perturb it. Dumb Waiter accounts skew higher (new to the sales
    # motion, per the GTM Scorer's hypothesis).
    region_complexity = np.array([complexity_by_region[r] for r in account_region])
    product_bump = np.where(account_product == "Dumb Waiter (New Product)", 1.2, 0.0)
    noise = rng.normal(0, 0.6, size=N_ACCOUNTS)
    complexity_score = np.clip(
        np.round(region_complexity * 0.6 + 2.0 * 0.4 + product_bump + noise), 1, 5
    ).astype(int)

    acquisition_year = rng.choice(YEARS, size=N_ACCOUNTS, p=_recency_weighted(YEARS))

    df = pd.DataFrame(
        {
            "account_id": [f"A{i+1:04d}" for i in range(N_ACCOUNTS)],
            "account_name": [fake.company() for _ in range(N_ACCOUNTS)],
            "region_id": account_region,
            "product_line": account_product,
            "annual_revenue_inr": revenue_inr.round(0),
            "complexity_score": complexity_score,
            "acquisition_year": acquisition_year,
        }
    )
    return df


def _recency_weighted(years):
    # More accounts acquired in recent years than early years -- mild ramp,
    # not uniform.
    w = np.linspace(0.6, 1.4, len(years))
    return w / w.sum()


def build_yearly_financials(rng):
    n = len(YEARS)
    t = np.linspace(0, 1, n)

    # Revenue: smooth ramp to the 2.1x target with mild noise, endpoints exact.
    revenue = BASE_REVENUE_INR_M * (REVENUE_GROWTH_MULTIPLE ** t)
    revenue *= 1 + rng.normal(0, 0.015, size=n)
    revenue[0] = BASE_REVENUE_INR_M
    revenue[-1] = BASE_REVENUE_INR_M * REVENUE_GROWTH_MULTIPLE

    # Sales headcount: convex ramp to the 5.4x target -- grows faster than
    # revenue especially in the later years, which is exactly the pattern
    # Module A's diagnostic ratio needs to catch.
    sales_hc = BASE_SALES_HEADCOUNT * (HEADCOUNT_GROWTH_MULTIPLE ** (t ** 0.75))
    sales_hc[0] = BASE_SALES_HEADCOUNT
    sales_hc[-1] = BASE_SALES_HEADCOUNT * HEADCOUNT_GROWTH_MULTIPLE
    sales_hc = np.round(sales_hc).astype(int)

    # Total headcount includes after-sales + quality + support, scaling a
    # bit more slowly than sales headcount (per the case's own department
    # split), roughly 1.7-2x the sales headcount throughout.
    support_ratio = np.linspace(1.75, 1.55, n)
    total_hc = np.round(sales_hc * support_ratio).astype(int)

    # Cost of sales: tracks revenue (materials/fabrication cost), ~40% of
    # revenue with slight improvement from scale (matches the case's
    # cost-of-sales/revenue drift from ~44% to ~39%).
    cos_ratio = np.linspace(0.44, 0.39, n)
    cost_of_sales = revenue * cos_ratio

    # Sales opex: driven by headcount, not revenue -- annual fully-loaded
    # cost per sales rep, inflating modestly year over year.
    cost_per_rep_inr_m = 0.9 * (1.06 ** t_index(n))
    sales_opex = sales_hc * cost_per_rep_inr_m

    # Other opex (after-sales/quality/admin): scales with total headcount,
    # smaller per-head cost.
    other_opex = (total_hc - sales_hc) * 0.55 * (1.05 ** t_index(n))

    total_cost = cost_of_sales + sales_opex + other_opex
    net_income = revenue - total_cost

    df = pd.DataFrame(
        {
            "year": YEARS,
            "revenue_inr_m": revenue.round(2),
            "cost_of_sales_inr_m": cost_of_sales.round(2),
            "sales_opex_inr_m": sales_opex.round(2),
            "other_opex_inr_m": other_opex.round(2),
            "total_cost_inr_m": total_cost.round(2),
            "net_income_inr_m": net_income.round(2),
            "sales_headcount": sales_hc,
            "total_headcount": total_hc,
        }
    )
    return df


def t_index(n):
    return np.arange(n)


def build_reps(rng, fake, regions_df, yearly_financials_df):
    final_sales_hc = int(yearly_financials_df["sales_headcount"].iloc[-1])
    region_ids = regions_df["region_id"].tolist()
    complexity_by_region = dict(
        zip(regions_df["region_id"], regions_df["complexity_index"])
    )
    weights = np.array([complexity_by_region[r] for r in region_ids], dtype=float)
    weights = weights / weights.sum()

    rep_region = rng.choice(region_ids, size=final_sales_hc, p=weights)

    # Current-state specialization: reflects the case's actual 2013 endpoint
    # -- a geography-cum-product-specific combination, so most reps carry a
    # named product specialization within their region, a minority are
    # cross-trained generalists. This is descriptive of today's baseline
    # only; Module B (Coverage Model Simulator) tests counterfactual
    # structures independently of this field.
    specialization = rng.choice(
        PRODUCT_LINES + ["Generalist"],
        size=final_sales_hc,
        p=[0.30, 0.25, 0.15, 0.05, 0.25],
    )

    tenure_years = rng.integers(0, 7, size=final_sales_hc)
    hire_year = 2024 - tenure_years

    # Annual fully-loaded cost: base + region cost-of-living adjustment +
    # tenure premium.
    region_col_index = {
        "Delhi NCR": 1.15,
        "Haryana Belt": 1.0,
        "Maharashtra West": 1.2,
        "Gujarat Industrial Corridor": 1.05,
        "Karnataka South": 1.1,
        "Tamil Nadu Coastal": 0.95,
    }
    region_name_by_id = dict(zip(regions_df["region_id"], regions_df["region_name"]))
    col_multiplier = np.array(
        [region_col_index[region_name_by_id[r]] for r in rep_region]
    )
    base_cost_inr = 900_000
    annual_cost_inr = (
        base_cost_inr * col_multiplier * (1 + 0.04 * tenure_years)
        + rng.normal(0, 25_000, size=final_sales_hc)
    ).round(0)

    df = pd.DataFrame(
        {
            "rep_id": [f"REP{i+1:03d}" for i in range(final_sales_hc)],
            "rep_name": [fake.name() for _ in range(final_sales_hc)],
            "region_id": rep_region,
            "specialization": specialization,
            "annual_cost_inr": annual_cost_inr,
            "tenure_years": tenure_years,
            "hire_year": hire_year,
        }
    )
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--outdir", type=str, default=os.path.join(os.path.dirname(__file__), "generated")
    )
    parser.add_argument(
        "--sample-outdir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "sample"),
    )
    parser.add_argument("--sample-rows", type=int, default=15)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    fake = Faker("en_IN")
    Faker.seed(args.seed)

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.sample_outdir, exist_ok=True)

    regions_df = build_regions()
    yearly_financials_df = build_yearly_financials(rng)
    accounts_df = build_accounts(rng, fake, regions_df)
    reps_df = build_reps(rng, fake, regions_df, yearly_financials_df)

    tables = {
        "regions": regions_df,
        "accounts": accounts_df,
        "reps": reps_df,
        "yearly_financials": yearly_financials_df,
    }

    for name, df in tables.items():
        full_path = os.path.join(args.outdir, f"{name}.csv")
        df.to_csv(full_path, index=False)
        sample_path = os.path.join(args.sample_outdir, f"{name}_sample.csv")
        df.head(args.sample_rows).to_csv(sample_path, index=False)
        print(f"wrote {full_path}  ({len(df)} rows)  + sample -> {sample_path}")

    # Sanity check: print the headline diagnostic ratio the build plan calls for
    hc0, hc1 = yearly_financials_df["sales_headcount"].iloc[[0, -1]]
    rev0, rev1 = yearly_financials_df["revenue_inr_m"].iloc[[0, -1]]
    print(
        f"\nHeadcount growth: {hc0} -> {hc1}  ({hc1 / hc0:.2f}x)"
        f"\nRevenue growth:   {rev0:.1f}M -> {rev1:.1f}M  ({rev1 / rev0:.2f}x)"
    )


if __name__ == "__main__":
    main()
