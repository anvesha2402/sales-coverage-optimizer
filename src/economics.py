"""
economics.py — the financial close of the loop

Business question: What does the recommended redesign actually save, what
does the change itself cost, and how long until it pays back?

Takes Module C's as-is and optimised results and Module D's channel choice
and produces:
  1. A before/after table of executive sales metrics (cost to serve per
     account, sales cost as % of revenue, revenue per rep, net margin).
  2. One-time transition costs: severance, relocation, retraining, and the
     margin lost when accounts change hands.
  3. Payback under two paths -- release surplus reps now, or let normal
     attrition take headcount down with a hiring freeze -- each under low /
     base / high transition assumptions.
  4. A region-by-region change list that the rollout plan is built from.

CAC, LTV and ROAS are deliberately not computed: there is no marketing
spend, acquisition-channel or retention data in this dataset, and inventing
them would be decoration. The sales-side equivalents above are the metrics
a VP of Sales would actually be held to here.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import assumptions as A  # noqa: E402
from data import generate_synthetic_company as gen  # noqa: E402

HORIZON_MONTHS = 24


def before_after(as_is_row, opt_row, financials_df, n_accounts):
    fy = financials_df.sort_values("year").iloc[-1]
    revenue = fy["revenue_inr_m"]
    net_income = fy["net_income_inr_m"]

    def metrics(row, label):
        cost_to_serve = row["payroll_inr_m"] + row["travel_inr_m"]
        return {
            "": label,
            "Sales reps": int(row["reps_used"]),
            "Sales payroll (₹M)": row["payroll_inr_m"],
            "Field travel (₹M)": row["travel_inr_m"],
            "Cost to serve (₹M)": cost_to_serve,
            "Cost to serve per account (₹ '000)": cost_to_serve * 1e3 / n_accounts,
            "Cost to serve, % of revenue": cost_to_serve / revenue,
            "Revenue per rep (₹M)": revenue / row["reps_used"],
            "Engineering-led accounts served by a product expert": row["expert_coverage"],
            "Rep utilisation range": f"{row['utilisation_min']:.0%}–{row['utilisation_max']:.0%}",
        }

    before = metrics(as_is_row, "Today")
    after = metrics(opt_row, "Redesigned")
    saving = before["Cost to serve (₹M)"] - after["Cost to serve (₹M)"]
    after_tax_saving = saving * (1 - gen.TAX_RATE)
    before["Net margin"] = net_income / revenue
    after["Net margin"] = (net_income + after_tax_saving) / revenue
    return pd.DataFrame([before, after]).set_index(""), saving


def transition_costs(opt_row, accounts_df, assignment_df, reps_df, redeployed_to_new_product=1, case="base"):
    k = {"low": 0, "base": 1, "high": 2}[case]
    severance_months = (2, A.SEVERANCE_MONTHS_OF_PAY, 6)[k]
    handover_loss = (0.02, A.ACCOUNT_HANDOVER_REVENUE_LOSS, 0.10)[k]
    avg_pay = reps_df["annual_cost_inr"].mean()
    released = max(0, opt_row["existing_reps_freed"] - opt_row["transfers_in"] - redeployed_to_new_product)
    moved = assignment_df[assignment_df["current_rep_id"] != assignment_df["new_rep_id"]]
    moved_rev = accounts_df.set_index("account_id").loc[moved["account_id"], "annual_revenue_inr"].sum()
    items = {
        "Severance": released * avg_pay / 12 * severance_months,
        "Relocation": opt_row["transfers_in"] * A.RELOCATION_COST_PER_REP_INR,
        "Retraining (relocated + redeployed)": (opt_row["transfers_in"] + redeployed_to_new_product)
        * A.RETRAINING_COST_PER_REP_INR,
        "Margin lost on handed-over accounts": moved_rev * A.GROSS_MARGIN * handover_loss,
    }
    return {"case": case, "reps_released": released, "accounts_moved": len(moved),
            "items_inr_m": {k2: v / 1e6 for k2, v in items.items()},
            "total_inr_m": sum(items.values()) / 1e6,
            "severance_part_inr_m": items["Severance"] / 1e6}


def payback(annual_saving_inr_m, transition, reps_released, pool_size, path="release now"):
    """Monthly cumulative net benefit. 'release now': full saving from month
    2 (one month notice), all transition costs in month 1. 'attrition':
    hiring freeze; headcount falls as reps leave at the normal attrition
    rate, so saving ramps up and no severance is paid."""
    monthly_full = annual_saving_inr_m / 12
    months = np.arange(1, HORIZON_MONTHS + 1)
    if path == "release now":
        saving = np.where(months >= 2, monthly_full, 0.0)
        one_off = transition["total_inr_m"]
    else:
        exits_per_month = pool_size * A.SALES_ATTRITION_PER_YEAR / 12
        share = np.minimum(1.0, months * exits_per_month / max(1, reps_released))
        saving = monthly_full * share
        one_off = transition["total_inr_m"] - transition["severance_part_inr_m"]
    cum = np.cumsum(saving) - one_off
    hit = np.where(cum >= 0)[0]
    return {
        "path": path,
        "one_off_cost_inr_m": one_off,
        "payback_month": int(months[hit[0]]) if len(hit) else None,
        "net_benefit_24m_inr_m": float(cum[-1]),
        "months_to_target_headcount": (1 if path == "release now"
                                       else int(np.ceil(reps_released / (pool_size * A.SALES_ATTRITION_PER_YEAR / 12)))),
        "cumulative": cum,
    }


def region_changes(assignment_df, reps_df, accounts_df):
    """Per region: reps today vs. reps needed, accounts changing owner."""
    today = reps_df.groupby("region_id").size()
    kept = assignment_df.dropna(subset=["new_rep_id"]).groupby("region_id")["new_rep_id"].nunique()
    moved = assignment_df[assignment_df["current_rep_id"] != assignment_df["new_rep_id"]].groupby("region_id").size()
    complex_n = accounts_df[accounts_df["complexity_score"] >= A.COMPLEX_ACCOUNT_THRESHOLD].groupby("region_id").size()
    names = dict(zip(gen.build_regions()["region_id"], gen.build_regions()["region_name"]))
    df = pd.DataFrame({
        "region": [names[r] for r in today.index],
        "reps_today": today.values,
        "reps_needed": kept.reindex(today.index).fillna(0).astype(int).values,
        "accounts": accounts_df.groupby("region_id").size().reindex(today.index).values,
        "complex_accounts": complex_n.reindex(today.index).fillna(0).astype(int).values,
        "accounts_changing_owner": moved.reindex(today.index).fillna(0).astype(int).values,
    }, index=today.index)
    df["change"] = df["reps_needed"] - df["reps_today"]
    return df
