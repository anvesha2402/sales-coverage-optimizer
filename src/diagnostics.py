"""
diagnostics.py — Module A: Diagnostic Engine

Business question: Is the sales org structurally sustainable, or is sales
cost quietly outrunning growth before it shows up in the numbers leadership
watches (revenue)?

Method: ratio analysis on yearly_financials -- no ML, no optimisation.

Two separate things are computed, and kept separate on purpose:
  1. An EARLY WARNING: the first year cumulative sales-headcount growth runs
     more than 20% ahead of cumulative revenue growth
     ((headcount_t / headcount_0) / (revenue_t / revenue_0) > 1.20).
  2. A MARGIN BREACH: the first year net margin falls below half of its
     base-year level. (Relative, not a fixed 10%, so it works for any
     starting margin. The 50% cut-off is a judgement call, stated.)

Because the stress scenario in the dataset was built to contain this
pattern, catching it there proves little. `backtest()` therefore runs the
same rule on 200 generated histories -- healthy and strained mixed -- and
reports how often the warning is right, how often it is a false alarm, and
how many years ahead of the margin breach it fires. It also compares the
warning against the metric most leadership teams watch: revenue growth.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data import generate_synthetic_company as gen  # noqa: E402

WARNING_RATIO = 1.20
BREACH_SHARE_OF_BASE_MARGIN = 0.50
REVENUE_SLOWDOWN_WARNING = 0.08     # "revenue-watcher" baseline: YoY growth < 8%


def load_yearly_financials(path="data/generated/yearly_financials.csv"):
    return pd.read_csv(path).sort_values("year").reset_index(drop=True)


def compute_yoy_table(df):
    out = df.copy()
    out["revenue_growth_yoy"] = out["revenue_inr_m"].pct_change()
    out["headcount_growth_yoy"] = out["sales_headcount"].pct_change()
    out["cum_growth_ratio"] = (
        (out["sales_headcount"] / out["sales_headcount"].iloc[0])
        / (out["revenue_inr_m"] / out["revenue_inr_m"].iloc[0])
    )
    out["sales_cost_pct_of_revenue"] = out["sales_opex_inr_m"] / out["revenue_inr_m"]
    out["net_margin"] = out["net_income_inr_m"] / out["revenue_inr_m"]
    return add_operating_leverage(out)


def add_operating_leverage(df, variable_pay_share=0.0):
    """Degree of operating leverage (DOL) = contribution / operating profit:
    the % change in profit for a 1% change in revenue.

    Cost behaviour in this P&L: cost of sales, other opex and depreciation/
    interest are modelled as shares of revenue (variable). The whole sales
    cost -- payroll plus the travel/incentive loading -- scales with
    HEADCOUNT, not revenue, so it is the fixed block. As headcount outruns
    revenue, that block grows, profit thins, and DOL climbs: the business
    becomes fragile to any revenue dip.

    variable_pay_share: what-if share of rep pay converted to commission
    (paid as a share of revenue), which moves cost from fixed to variable."""
    out = df.copy()
    fixed = out["sales_opex_inr_m"] * (1 - variable_pay_share)
    pbt = out["total_cost_inr_m"] - out["tax_inr_m"]
    pbt = out["revenue_inr_m"] - pbt                      # operating profit before tax
    variable = out["revenue_inr_m"] - pbt - fixed
    out["fixed_cost_inr_m"] = fixed
    out["variable_cost_inr_m"] = variable
    out["contribution_inr_m"] = out["revenue_inr_m"] - variable
    out["operating_profit_inr_m"] = pbt
    out["operating_leverage"] = np.where(pbt > 0, out["contribution_inr_m"] / pbt, np.nan)
    out["profit_change_if_revenue_falls_10pct"] = np.where(
        pbt > 0, -0.10 * out["contribution_inr_m"] / pbt, np.nan)
    return out


def decompose_revenue(financials_df, yearly_accounts_df):
    """Revenue per rep = accounts per rep x revenue per account.

    Splits the change in revenue per rep into (a) each rep covering fewer or
    more accounts and (b) each account being worth less or more. Uses log
    changes so the two parts add up exactly.

    Two of the four classic terms (win rate, repeat-order rate) are left out
    on purpose: they need deal-level data (opportunities won and lost) that
    this dataset does not have. accounts_won / accounts_lost are reported as
    context, not as a decomposition term."""
    df = financials_df[["year", "revenue_inr_m", "sales_headcount"]].merge(yearly_accounts_df, on="year")
    df["revenue_per_rep_inr_m"] = df["revenue_inr_m"] / df["sales_headcount"]
    df["accounts_per_rep"] = df["active_accounts"] / df["sales_headcount"]
    df["revenue_per_account_inr_k"] = df["revenue_inr_m"] * 1e3 / df["active_accounts"]
    df["d_ln_revenue_per_rep"] = np.log(df["revenue_per_rep_inr_m"]).diff()
    df["from_accounts_per_rep"] = np.log(df["accounts_per_rep"]).diff()
    df["from_revenue_per_account"] = np.log(df["revenue_per_account_inr_k"]).diff()
    first, last = df.iloc[0], df.iloc[-1]
    total = np.log(last["revenue_per_rep_inr_m"] / first["revenue_per_rep_inr_m"])
    part_a = np.log(last["accounts_per_rep"] / first["accounts_per_rep"])
    part_b = np.log(last["revenue_per_account_inr_k"] / first["revenue_per_account_inr_k"])
    summary = {
        "revenue_per_rep_change": float(last["revenue_per_rep_inr_m"] / first["revenue_per_rep_inr_m"] - 1),
        "accounts_per_rep_change": float(last["accounts_per_rep"] / first["accounts_per_rep"] - 1),
        "revenue_per_account_change": float(last["revenue_per_account_inr_k"] / first["revenue_per_account_inr_k"] - 1),
        "share_explained_by_accounts_per_rep": float(part_a / total) if total else None,
        "share_explained_by_revenue_per_account": float(part_b / total) if total else None,
    }
    return df, summary


def leverage_what_if(df, variable_pay_shares=(0.0, 0.2, 0.4)):
    """Final-year DOL if part of rep pay were commission instead of salary."""
    rows = []
    for s in variable_pay_shares:
        last = add_operating_leverage(df, s).iloc[-1]
        rows.append({"variable_pay_share": s, "operating_leverage": last["operating_leverage"],
                     "profit_change_if_revenue_falls_10pct": last["profit_change_if_revenue_falls_10pct"]})
    return pd.DataFrame(rows)


def find_warning_year(yoy, ratio=None):
    ratio = WARNING_RATIO if ratio is None else ratio
    hit = yoy[yoy["cum_growth_ratio"] > ratio]
    return int(hit.iloc[0]["year"]) if len(hit) else None


def find_breach_year(yoy, share=BREACH_SHARE_OF_BASE_MARGIN):
    line = yoy["net_margin"].iloc[0] * share
    hit = yoy[yoy["net_margin"] < line]
    return int(hit.iloc[0]["year"]) if len(hit) else None


def find_revenue_watch_year(yoy, floor=REVENUE_SLOWDOWN_WARNING):
    hit = yoy[yoy["revenue_growth_yoy"] < floor]
    return int(hit.iloc[0]["year"]) if len(hit) else None


def sustainability_score(yoy):
    """0-100: penalises (a) cumulative headcount growth running ahead of
    revenue growth by the final year and (b) margin lost since the base year."""
    excess = max(0.0, yoy["cum_growth_ratio"].iloc[-1] - 1.0)
    ratio_penalty = min(60.0, excess * 60.0)
    compression = max(0.0, yoy["net_margin"].iloc[0] - yoy["net_margin"].iloc[-1])
    margin_penalty = min(40.0, compression * 400.0)
    return round(max(0.0, 100.0 - ratio_penalty - margin_penalty), 1)


def diagnose_from_df(df):
    df = df.sort_values("year").reset_index(drop=True)
    yoy = compute_yoy_table(df)
    warn, breach = find_warning_year(yoy), find_breach_year(yoy)
    hc = df["sales_headcount"].iloc[-1] / df["sales_headcount"].iloc[0]
    rev = df["revenue_inr_m"].iloc[-1] / df["revenue_inr_m"].iloc[0]
    return {
        "yoy_table": yoy,
        "sustainability_score": sustainability_score(yoy),
        "warning_year": warn,
        "breach_year": breach,
        "lead_years": (breach - warn) if (warn and breach) else None,
        "revenue_watch_year": find_revenue_watch_year(yoy),
        "base_margin": yoy["net_margin"].iloc[0],
        "breach_line": yoy["net_margin"].iloc[0] * BREACH_SHARE_OF_BASE_MARGIN,
        "cumulative_headcount_growth": round(hc, 2),
        "cumulative_revenue_growth": round(rev, 2),
        "cumulative_growth_ratio": round(hc / rev, 2),
        # Headcount the company would have today had it grown in step with revenue
        "in_step_headcount": round(df["sales_headcount"].iloc[0] * rev, 1),
    }


def diagnose(path="data/generated/yearly_financials.csv"):
    return diagnose_from_df(load_yearly_financials(path))


def scenario_yearly_financials(revenue_growth_multiple=2.1, headcount_growth_multiple=3.5,
                               base_revenue_inr_m=150.0, base_sales_headcount=16,
                               final_avg_rep_cost_inr_m=1.07, noise=0.0, rng=None):
    """Same P&L structure as the data generator, driven by two multiples --
    used by the live dashboard and by backtest()."""
    n = len(gen.YEARS)
    t = np.linspace(0, 1, n)
    rng = rng or np.random.default_rng(0)
    revenue = base_revenue_inr_m * revenue_growth_multiple ** t
    hc = base_sales_headcount * headcount_growth_multiple ** (t ** 0.75)
    if noise:
        revenue = revenue * (1 + rng.normal(0, noise, n))
        hc = hc * (1 + rng.normal(0, noise * 2, n))
        revenue[0], hc[0] = base_revenue_inr_m, base_sales_headcount
    hc = np.maximum(1, np.round(hc)).astype(int)
    avg_cost = final_avg_rep_cost_inr_m / (1 + gen.REP_COST_INFLATION) ** np.arange(n - 1, -1, -1)
    payroll = hc * avg_cost
    sales_opex = payroll * (1 + gen.SALES_EXPENSE_LOADING)
    cos = revenue * np.linspace(*gen.COST_OF_SALES_SHARE, n)
    other = revenue * gen.OTHER_OPEX_SHARE
    dep = revenue * gen.DEPRECIATION_INTEREST_SHARE
    pbt = revenue - cos - sales_opex - other - dep
    tax = np.where(pbt > 0, pbt * gen.TAX_RATE, 0.0)
    return pd.DataFrame({
        "year": gen.YEARS, "revenue_inr_m": revenue, "cost_of_sales_inr_m": cos,
        "sales_payroll_inr_m": payroll, "sales_opex_inr_m": sales_opex, "other_opex_inr_m": other,
        "depreciation_interest_inr_m": dep, "tax_inr_m": tax,
        "total_cost_inr_m": cos + sales_opex + other + dep + tax,
        "net_income_inr_m": pbt - tax, "sales_headcount": hc,
    })


def backtest(n_histories=200, seed=7):
    """Run the warning rule on generated histories it was not tuned on.
    Headcount multiple is drawn from 0.7x to 2.0x the revenue multiple, so
    roughly half the histories are healthy and half strained. Each history's
    outcome (did margin actually breach?) is what the warning is scored
    against -- not the label it was generated with."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_histories):
        rev_mult = rng.uniform(1.3, 2.8)
        hc_mult = rev_mult * rng.uniform(0.7, 2.0)
        df = scenario_yearly_financials(rev_mult, hc_mult, noise=0.03, rng=rng)
        d = diagnose_from_df(df)
        rows.append({
            "history": i, "revenue_multiple": rev_mult, "headcount_multiple": hc_mult,
            "warning_year": d["warning_year"], "breach_year": d["breach_year"],
            "revenue_watch_year": d["revenue_watch_year"],
        })
    res = pd.DataFrame(rows)
    breached = res["breach_year"].notna()
    warned = res["warning_year"].notna()
    early = breached & warned & (res["warning_year"] <= res["breach_year"])
    rev_early = breached & res["revenue_watch_year"].notna() & (res["revenue_watch_year"] <= res["breach_year"])
    lead = (res.loc[early, "breach_year"] - res.loc[early, "warning_year"])
    summary = {
        "histories": n_histories,
        "histories_with_breach": int(breached.sum()),
        "detection_rate": float(early.sum() / max(1, breached.sum())),
        "false_alarm_rate": float((warned & ~breached).sum() / max(1, (~breached).sum())),
        "median_lead_years": float(lead.median()) if len(lead) else None,
        "revenue_watch_detection_rate": float(rev_early.sum() / max(1, breached.sum())),
        "revenue_watch_false_alarm_rate": float(
            (res["revenue_watch_year"].notna() & ~breached).sum() / max(1, (~breached).sum())),
    }
    return res, summary


if __name__ == "__main__":
    r = diagnose()
    print(r["yoy_table"][["year", "revenue_growth_yoy", "headcount_growth_yoy", "cum_growth_ratio",
                          "sales_cost_pct_of_revenue", "net_margin"]].round(3).to_string(index=False))
    print(f"\nSustainability score: {r['sustainability_score']}/100")
    print(f"Early warning year: {r['warning_year']}  |  margin breach year "
          f"(net margin < {r['breach_line']:.1%}, half of base): {r['breach_year']}  |  lead: {r['lead_years']} yrs")
    print(f"Revenue-watcher (YoY growth < 8%) would have flagged: {r['revenue_watch_year']}")
    print(f"Headcount if it had grown in step with revenue: {r['in_step_headcount']} (actual 56)")
    _, s = backtest()
    print("\nBacktest on 200 generated histories:")
    for k, v in s.items():
        print(f"  {k}: {v}")
