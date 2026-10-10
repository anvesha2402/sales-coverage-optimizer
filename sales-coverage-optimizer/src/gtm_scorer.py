"""
gtm_scorer.py — Module D: New-Product Go-to-Market Scorer

Business question: How should the Dumb Waiter be sold -- through the
existing sales force, a dedicated pod, or channel partners?

Two steps, kept separate:

1. FIT SCORE (is the existing motion a good fit?). A transparent weighted
   score over three 0-1 distances between the new product's accounts and
   the existing book, all computed from the data:
     buyer distance      mean of: buyer-segment overlap, regional mix,
                         ticket-size gap
     complexity distance gap in average technical complexity (1-5 scale)
     deal-cycle distance gap in average first-meeting-to-order days
   >= 0.5 means the new product does not fit the existing motion.
   This says WHETHER to move it out of the generalist bag, not WHERE to.

2. ECONOMICS (which option makes the most money, and how fast does the
   change pay back?). A 24-month month-by-month model of three options,
   compared on gross-margin contribution after their own costs. Payback is
   measured against the existing sales force as the baseline. Each option
   is run under low / base / high assumptions, and the pod's break-even win
   rate is reported, so the answer's sensitivity is visible.

What changed from the first version, and why:
  * The old "2.4-month breakeven" treated 3 reps' ANNUAL pay as a one-time
    cost, counted revenue instead of margin, credited the pod with all of
    the product's revenue (not just the extra it brings), and assumed 40
    accounts when the data has ~33. All four are fixed here.
  * Deal-cycle length now comes from the accounts' deal_cycle_days field
    instead of a hard-coded table.
  * Buyer distance now uses the buyer segment the case describes
    (builders, hotels, hospitals vs. industrial plants).
  * A third option -- channel partners -- is included, because "pod or
    existing force" was a false two-way choice for a product bought by
    builders.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import assumptions as A  # noqa: E402

NEW_PRODUCT = "Dumb Waiter (New Product)"
DEFAULT_WEIGHTS = {"buyer_distance": 0.40, "complexity_distance": 0.35, "deal_cycle_distance": 0.25}
FIT_THRESHOLD = 0.5
MONTHS = 24

# Option assumptions: (low, base, high) from the option's own point of view
# -- "low" is the pessimistic case for that option. All stated in
# docs/assumptions.md; none come from real data.
GTM_ASSUMPTIONS = {
    "existing_win_rate": (0.10, 0.15, 0.20),      # base calibrated so pilot leads x rate = pilot accounts
    "rep_hours_per_lead": (10, 8, 6),             # regional rep time spent per Dumb Waiter lead
    "pod_reps": 3,
    "pod_win_rate": (0.18, 0.25, 0.32),           # focused, trained reps close more
    "pod_lead_uplift": (1.0, 1.2, 1.4),           # focused prospecting finds more leads
    "pod_ramp_months": (4, 3, 2),
    "pod_one_time_inr": (1_600_000, 1_200_000, 900_000),   # training + launch events/listings
    "pod_travel_per_rep_inr": (250_000, 200_000, 150_000),
    "partner_accounts_per_year": (24, 48, 72),    # e.g. 8 lift dealers x ~6 installs a year
    "partner_commission": (0.12, 0.10, 0.08),
    "partner_ramp_months": (9, 6, 4),
    "partner_one_time_inr": (1_000_000, 800_000, 600_000),  # onboarding, training, demo units
    "partner_manager_reps": 1,
    "amc_share_of_ticket": 0.08,                  # yearly service contract after year 1
}


def _tvd(a, b):
    keys = set(a.index) | set(b.index)
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys) / 2


def compute_inputs(accounts_df):
    new = accounts_df[accounts_df["product_line"] == NEW_PRODUCT]
    core = accounts_df[accounts_df["product_line"] != NEW_PRODUCT]
    seg = _tvd(new["buyer_segment"].value_counts(normalize=True), core["buyer_segment"].value_counts(normalize=True))
    reg = _tvd(new["region_id"].value_counts(normalize=True), core["region_id"].value_counts(normalize=True))
    t_new, t_core = new["annual_revenue_inr"].mean(), core["annual_revenue_inr"].mean()
    ticket = abs(t_new - t_core) / max(t_new, t_core)
    cyc_new, cyc_core = new["deal_cycle_days"].mean(), core["deal_cycle_days"].mean()
    return {
        "n_pilot_accounts": len(new),
        "buyer_segment_distance": seg,
        "buyer_region_distance": reg,
        "ticket_size_distance": ticket,
        "buyer_distance": (seg + reg + ticket) / 3,
        "complexity_distance": min(1.0, abs(new["complexity_score"].mean() - core["complexity_score"].mean()) / 4),
        "deal_cycle_distance": min(1.0, abs(cyc_new - cyc_core) / cyc_core),
        "avg_ticket_new_inr": t_new,
        "avg_ticket_core_inr": t_core,
        "deal_cycle_new_days": cyc_new,
        "deal_cycle_core_days": cyc_core,
    }


def fit_score(buyer_distance, complexity_distance, deal_cycle_distance, weights=None):
    w = weights or DEFAULT_WEIGHTS
    s = (w["buyer_distance"] * buyer_distance + w["complexity_distance"] * complexity_distance
         + w["deal_cycle_distance"] * deal_cycle_distance)
    return {"score": round(float(s), 3),
            "verdict": "Poor fit for the existing motion" if s >= FIT_THRESHOLD else "Fits the existing motion"}


def flip_points(inputs, weights=None):
    """How far each input would have to move, on its own, to cross 0.5."""
    w = weights or DEFAULT_WEIGHTS
    keys = ["buyer_distance", "complexity_distance", "deal_cycle_distance"]
    base = sum(w[k] * inputs[k] for k in keys)
    out = {}
    for k in keys:
        rest = base - w[k] * inputs[k]
        needed = (FIT_THRESHOLD - rest) / w[k]
        out[k] = round(float(needed), 3) if 0 <= needed <= 1 else None   # None = cannot flip alone
    return out


def _ramp(months, ramp):
    return np.minimum(1.0, np.arange(1, months + 1) / max(1, ramp))


def option_cashflows(inputs, case="base", avg_rep_cost_inr=1_070_000, overrides=None):
    """Monthly gross-margin contribution of each option, after its own costs.
    Returns a DataFrame indexed by month 0..24 (month 0 = one-time costs)."""
    k = {"low": 0, "base": 1, "high": 2}[case]
    g = {key: (v[k] if isinstance(v, tuple) else v) for key, v in GTM_ASSUMPTIONS.items()}
    g.update(overrides or {})
    ticket = inputs["avg_ticket_new_inr"]
    gm = A.GROSS_MARGIN
    # Pilot calibration: leads a year = pilot accounts / existing base win rate
    leads_per_month = inputs["n_pilot_accounts"] / GTM_ASSUMPTIONS["existing_win_rate"][1] / 12
    hourly_cost = avg_rep_cost_inr / A.SELLING_HOURS_PER_REP
    m = np.arange(1, MONTHS + 1)

    def margin_stream(wins_per_month):
        cum_wins = np.cumsum(wins_per_month)
        amc = np.where(m > 12, np.concatenate([[0] * 12, cum_wins[:-12]]) * ticket * g["amc_share_of_ticket"] / 12, 0)
        return wins_per_month * ticket * gm + amc * gm, wins_per_month

    # 1. Existing sales force
    wins_e = np.full(MONTHS, leads_per_month * g["existing_win_rate"])
    margin_e, _ = margin_stream(wins_e)
    time_cost = leads_per_month * g["rep_hours_per_lead"] * hourly_cost
    existing = margin_e - time_cost

    # 2. Dedicated pod (reps redeployed from those Module C frees -- so a
    #    one-time severance is avoided, but their salaries continue)
    wins_p = leads_per_month * g["pod_lead_uplift"] * g["pod_win_rate"] * _ramp(MONTHS, g["pod_ramp_months"])
    margin_p, _ = margin_stream(wins_p)
    pod_monthly = g["pod_reps"] * (avg_rep_cost_inr + g["pod_travel_per_rep_inr"]) / 12
    pod = margin_p - pod_monthly
    severance_avoided = g["pod_reps"] * avg_rep_cost_inr / 12 * A.SEVERANCE_MONTHS_OF_PAY
    pod_one_time = g["pod_one_time_inr"] - severance_avoided

    # 3. Channel partners (lift dealers / installers who already sell to builders)
    wins_c = g["partner_accounts_per_year"] / 12 * _ramp(MONTHS, g["partner_ramp_months"])
    margin_c, _ = margin_stream(wins_c)
    commission = wins_c * ticket * g["partner_commission"]
    manager = g["partner_manager_reps"] * avg_rep_cost_inr / 12
    channel = margin_c - commission - manager
    mgr_severance_avoided = g["partner_manager_reps"] * avg_rep_cost_inr / 12 * A.SEVERANCE_MONTHS_OF_PAY
    channel_one_time = g["partner_one_time_inr"] - mgr_severance_avoided

    df = pd.DataFrame({
        "month": np.arange(0, MONTHS + 1),
        "Existing sales force": np.concatenate([[0.0], existing]),
        "Dedicated pod": np.concatenate([[-pod_one_time], pod]),
        "Channel partners": np.concatenate([[-channel_one_time], channel]),
    })
    accounts = {"Existing sales force": wins_e.sum(), "Dedicated pod": wins_p.sum(), "Channel partners": wins_c.sum()}
    return df, accounts


def payback_month(option_series, baseline_series):
    """First month the option's cumulative contribution catches up with the
    existing-force baseline (None if not within 24 months)."""
    gap = np.cumsum(option_series.values - baseline_series.values)
    hit = np.where(gap >= 0)[0]
    return int(hit[0]) if len(hit) else None


def evaluate(accounts_df, avg_rep_cost_inr=1_070_000):
    inputs = compute_inputs(accounts_df)
    rows = []
    flows = {}
    for case in ("low", "base", "high"):
        cf, accts = option_cashflows(inputs, case, avg_rep_cost_inr)
        flows[case] = cf
        for opt in ("Existing sales force", "Dedicated pod", "Channel partners"):
            rows.append({
                "case": case, "option": opt,
                "accounts_won_24m": accts[opt],
                "contribution_24m_inr_m": cf[opt].sum() / 1e6,
                "payback_month_vs_existing": (0 if opt == "Existing sales force"
                                              else payback_month(cf[opt], cf["Existing sales force"])),
            })
    table = pd.DataFrame(rows)
    base = table[table["case"] == "base"].set_index("option")
    best = base["contribution_24m_inr_m"].idxmax()
    holds = {c: table[table["case"] == c].set_index("option")["contribution_24m_inr_m"].idxmax()
             for c in ("low", "base", "high")}
    return {
        "inputs": inputs,
        "fit": fit_score(inputs["buyer_distance"], inputs["complexity_distance"], inputs["deal_cycle_distance"]),
        "flip_points": flip_points(inputs),
        "options": table,
        "flows": flows,
        "recommendation": best,
        "best_by_case": holds,
        "pod_break_even_win_rate": pod_break_even(inputs, avg_rep_cost_inr),
    }


def pod_break_even(inputs, avg_rep_cost_inr=1_070_000):
    """Pod win rate at which it matches the best other option over 24 months."""
    for wr in np.arange(0.10, 0.81, 0.01):
        cf, _ = option_cashflows(inputs, "base", avg_rep_cost_inr, overrides={"pod_win_rate": wr})
        others = max(cf["Existing sales force"].sum(), cf["Channel partners"].sum())
        if cf["Dedicated pod"].sum() >= others:
            return round(float(wr), 2)
    return None


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    r = evaluate(pd.read_csv("data/generated/accounts.csv"))
    for k, v in r["inputs"].items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    print("\nFit:", r["fit"], "\nFlip points (value each input needs, alone):", r["flip_points"])
    print(r["options"].round(2).to_string(index=False))
    print("\nRecommendation (base):", r["recommendation"], "| best by case:", r["best_by_case"])
    print("Pod win rate needed to beat the best alternative:", r["pod_break_even_win_rate"])
