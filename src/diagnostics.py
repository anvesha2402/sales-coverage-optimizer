"""
diagnostics.py — Module A: Diagnostic Engine

Business question: Is the sales org structurally sustainable, or is cost
quietly outrunning growth before it shows up in the numbers leadership
actually watches?

Method: ratio analysis on yearly_financials — headcount growth vs. revenue
growth, and the sales-cost-to-total-cost trend. No ML, no optimization:
this module is direct computation on purpose (see build plan §3) because
the question is "read the trend correctly," not "predict" or "optimize."
"""

import numpy as np
import pandas as pd


def load_yearly_financials(path="data/generated/yearly_financials.csv"):
    return pd.read_csv(path).sort_values("year").reset_index(drop=True)


def compute_yoy_table(df):
    """Year-over-year growth rates and the diagnostic ratios derived from them."""
    out = df.copy()
    out["revenue_growth_yoy"] = out["revenue_inr_m"].pct_change()
    out["headcount_growth_yoy"] = out["sales_headcount"].pct_change()
    # The leading indicator: how many units of headcount growth are being
    # bought per unit of revenue growth, year over year. 1.0 = growing in
    # lockstep. >1.0 = headcount outrunning revenue that year.
    out["growth_ratio"] = out["headcount_growth_yoy"] / out["revenue_growth_yoy"]
    out["sales_cost_pct_of_total"] = out["sales_opex_inr_m"] / out["total_cost_inr_m"]
    out["net_margin"] = out["net_income_inr_m"] / out["revenue_inr_m"]
    return out


def find_threshold_year(yoy_table, margin_threshold=0.10):
    """
    First year net margin drops below `margin_threshold`. This is the
    'insight to derive': the exact year the ratio crosses a sustainability
    threshold, computed from the data -- not eyeballed from a chart.
    """
    breach = yoy_table[yoy_table["net_margin"] < margin_threshold]
    if breach.empty:
        return None
    return int(breach.iloc[0]["year"])


def sustainability_score(yoy_table):
    """
    0-100 composite: penalizes (a) how far the average YoY growth_ratio sits
    above 1.0 (headcount consistently outrunning revenue) and (b) how much
    net margin has compressed from its first to its last observed year.
    100 = fully sustainable trajectory, 0 = severe structural strain.
    """
    valid_ratios = yoy_table["growth_ratio"].dropna()
    valid_ratios = valid_ratios[valid_ratios.apply(lambda x: x == x)]  # drop NaN/inf
    avg_excess_ratio = max(0.0, valid_ratios.mean() - 1.0)
    ratio_penalty = min(60.0, avg_excess_ratio * 30.0)  # cap contribution at 60 pts

    margin_start = yoy_table["net_margin"].iloc[0]
    margin_end = yoy_table["net_margin"].iloc[-1]
    margin_compression = max(0.0, margin_start - margin_end)
    margin_penalty = min(40.0, margin_compression * 100.0)  # cap at 40 pts

    return round(max(0.0, 100.0 - ratio_penalty - margin_penalty), 1)


def scenario_yearly_financials(
    revenue_growth_multiple=2.1, headcount_growth_multiple=5.4,
    base_revenue_inr_m=150.0, base_sales_headcount=22,
    years=range(2019, 2025),
):
    """
    Deterministic (no-noise) re-derivation of the same trajectory shape used
    in data/generate_synthetic_company.py, parameterized so the Scenario
    Dashboard can recompute Module A live as sliders move -- without
    re-running the data generator or touching the committed dataset.
    """
    years = list(years)
    n = len(years)
    t = np.linspace(0, 1, n)

    revenue = base_revenue_inr_m * (revenue_growth_multiple ** t)
    sales_hc = np.round(base_sales_headcount * (headcount_growth_multiple ** (t ** 0.75))).astype(int)
    support_ratio = np.linspace(1.75, 1.55, n)
    total_hc = np.round(sales_hc * support_ratio).astype(int)

    cos_ratio = np.linspace(0.44, 0.39, n)
    cost_of_sales = revenue * cos_ratio
    cost_per_rep = 0.9 * (1.06 ** np.arange(n))
    sales_opex = sales_hc * cost_per_rep
    other_opex = (total_hc - sales_hc) * 0.55 * (1.05 ** np.arange(n))
    total_cost = cost_of_sales + sales_opex + other_opex
    net_income = revenue - total_cost

    return pd.DataFrame({
        "year": years,
        "revenue_inr_m": revenue.round(2),
        "cost_of_sales_inr_m": cost_of_sales.round(2),
        "sales_opex_inr_m": sales_opex.round(2),
        "other_opex_inr_m": other_opex.round(2),
        "total_cost_inr_m": total_cost.round(2),
        "net_income_inr_m": net_income.round(2),
        "sales_headcount": sales_hc,
        "total_headcount": total_hc,
    })


def diagnose_from_df(df, margin_threshold=0.10):
    """Same as diagnose(), but takes an in-memory dataframe (e.g. from
    scenario_yearly_financials) instead of reading a CSV -- used by the
    live dashboard."""
    df = df.sort_values("year").reset_index(drop=True)
    yoy = compute_yoy_table(df)
    threshold_year = find_threshold_year(yoy, margin_threshold)
    score = sustainability_score(yoy)
    cum_headcount_growth = df["sales_headcount"].iloc[-1] / df["sales_headcount"].iloc[0]
    cum_revenue_growth = df["revenue_inr_m"].iloc[-1] / df["revenue_inr_m"].iloc[0]
    return {
        "yoy_table": yoy,
        "sustainability_score": score,
        "threshold_year": threshold_year,
        "margin_threshold": margin_threshold,
        "cumulative_headcount_growth": round(cum_headcount_growth, 2),
        "cumulative_revenue_growth": round(cum_revenue_growth, 2),
        "cumulative_growth_ratio": round(cum_headcount_growth / cum_revenue_growth, 2),
    }


def diagnose(path="data/generated/yearly_financials.csv", margin_threshold=0.10):
    df = load_yearly_financials(path)
    return diagnose_from_df(df, margin_threshold)


if __name__ == "__main__":
    result = diagnose()
    print(result["yoy_table"][
        ["year", "revenue_growth_yoy", "headcount_growth_yoy", "growth_ratio",
         "sales_cost_pct_of_total", "net_margin"]
    ].round(3).to_string(index=False))
    print(f"\nSustainability score: {result['sustainability_score']} / 100")
    print(f"Threshold year (net margin < {result['margin_threshold']:.0%}): "
          f"{result['threshold_year']}")
    print(f"Cumulative headcount growth: {result['cumulative_headcount_growth']}x")
    print(f"Cumulative revenue growth:   {result['cumulative_revenue_growth']}x")
    print(f"Cumulative growth ratio:     {result['cumulative_growth_ratio']}x")
