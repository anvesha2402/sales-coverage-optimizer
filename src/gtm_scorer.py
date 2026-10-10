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

Version 3 adds the marketing/channel frameworks that change a number here:
  * B2B buying centre: buyer distance is now the overlap in WHO takes part in
    the buying decision (plant head, engineering, procurement vs. project
    manager, architect, F&B head), replacing region/ticket proxies.
  * Service output demands (Bucklin): what Dumb Waiter buyers need from a
    channel, scored per option, with a sensitivity check -- an independent
    test alongside the economics.
  * Trade terms and push vs. pull: dealer commission AND credit days are
    costed; an architect-specification programme is a fourth option (pull).
  * TAM / SAM / SOM: every option's volume is capped at the reachable market
    built bottom-up from public construction, hotel and hospital data
    (data/market_sizing.csv), and the dealer count follows from it
    (distribution intensity).
  * EVC: the price a buyer could justify vs. the current ticket, and the
    economics re-run at a higher price as a scenario.
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
OPTIONS = ["Existing sales force", "Dedicated pod", "Channel partners", "Partners + architect programme"]
MARKET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "market_sizing.csv")

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
    "partner_commission": (0.12, 0.10, 0.08),     # trade term 1: margin to the dealer
    "partner_credit_days": (60, 45, 30),          # trade term 2: dealer pays after N days
    "cost_of_capital": 0.12,
    "partner_ramp_months": (9, 6, 4),
    "partner_one_time_inr": (1_000_000, 800_000, 600_000),  # onboarding, training, demo units
    "partner_manager_reps": 1,
    "architect_programme_inr_per_year": (800_000, 600_000, 400_000),  # pull: CPD sessions, spec listings
    "architect_uplift": (0.0, 0.15, 0.25),        # extra partner accounts from architects specifying it
    "architect_start_month": (6, 4, 3),
    "min_installs_per_dealer": 6,                 # below this a dealer stops pushing the product
    "amc_share_of_ticket": 0.08,                  # yearly service contract after year 1
}

# Service output demands (Bucklin): what a Dumb Waiter buyer needs from
# whoever sells it, weighted, and how well each route delivers (1-5).
# Judgement calls, stated -- the sensitivity check shows how robust the
# ranking is to any single score being off by one point.
SERVICE_OUTPUTS = {
    # need: (weight, existing force, pod, partners)
    "Local presence near the site": (0.20, 3, 2, 5),
    "Fast delivery and installation": (0.25, 2, 3, 4),
    "After-sales service on call": (0.25, 3, 3, 4),
    "Single-unit orders, little paperwork": (0.10, 2, 3, 5),
    "Technical specification support": (0.20, 3, 5, 3),
}

# EVC inputs (assumptions; competitor price is sourced in market_sizing.csv)
EVC = {
    "helper_cost_inr_per_month": 18_000,     # metro kitchen/ward helper, fully loaded
    "helper_fte_saved": (0.3, 0.5, 0.75),
    "life_years": 10,
    "discount_rate": 0.12,
    "differentiation_inr": 20_000,           # brand, service reliability vs. a local fabricator
    "price_scenario_uplift": 0.20,
    "win_rate_factor_at_higher_price": 0.90,
}


def _tvd(a, b):
    keys = set(a.index) | set(b.index)
    return sum(abs(a.get(k, 0) - b.get(k, 0)) for k in keys) / 2


def _role_profile(df):
    roles = df["buying_centre"].str.split("; ").explode()
    return roles.value_counts() / len(df)


def buying_centre_distance(new, core):
    """1 - weighted Jaccard similarity of how often each role sits in the
    buying decision. 0 = same people decide; 1 = no one in common."""
    p, q = _role_profile(new), _role_profile(core)
    keys = set(p.index) | set(q.index)
    num = sum(min(p.get(k, 0), q.get(k, 0)) for k in keys)
    den = sum(max(p.get(k, 0), q.get(k, 0)) for k in keys)
    return 1 - num / den, p, q


def compute_inputs(accounts_df):
    new = accounts_df[accounts_df["product_line"] == NEW_PRODUCT]
    core = accounts_df[accounts_df["product_line"] != NEW_PRODUCT]
    reg = _tvd(new["region_id"].value_counts(normalize=True), core["region_id"].value_counts(normalize=True))
    t_new, t_core = new["annual_revenue_inr"].mean(), core["annual_revenue_inr"].mean()
    ticket = abs(t_new - t_core) / max(t_new, t_core)
    cyc_new, cyc_core = new["deal_cycle_days"].mean(), core["deal_cycle_days"].mean()
    bc, p_new, p_core = buying_centre_distance(new, core)
    return {
        "n_pilot_accounts": len(new),
        "buyer_distance": bc,
        "buying_centre_new": {k: round(float(v), 2) for k, v in p_new.items()},
        "buying_centre_core": {k: round(float(v), 2) for k, v in p_core.items()},
        "buyer_region_distance": reg,       # context only
        "ticket_size_distance": ticket,     # context only
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


# ---------------------------------------------------------------------------
# Service output demands
# ---------------------------------------------------------------------------
def service_output_scorecard():
    names = ["Existing sales force", "Dedicated pod", "Channel partners"]
    rows = [{"need": k, "weight": v[0], **dict(zip(names, v[1:]))} for k, v in SERVICE_OUTPUTS.items()]
    table = pd.DataFrame(rows)
    totals = {n: float((table["weight"] * table[n]).sum()) for n in names}
    leader = max(totals, key=totals.get)
    # Sensitivity: move every single score by +/-1 and see if the leader changes
    flips, tests = 0, 0
    for i in range(len(table)):
        for n in names:
            for d in (-1, 1):
                t = table.copy()
                t.loc[i, n] = min(5, max(1, t.loc[i, n] + d))
                tot = {m: (t["weight"] * t[m]).sum() for m in names}
                tests += 1
                flips += max(tot, key=tot.get) != leader
    gap = totals[leader] - sorted(totals.values())[-2]
    return {"table": table, "totals": totals, "leader": leader,
            "leader_margin": gap, "single_score_changes_that_flip_leader": f"{flips} of {tests}"}


# ---------------------------------------------------------------------------
# Market sizing (TAM / SAM / SOM)
# ---------------------------------------------------------------------------
def market_size(case="base", path=MARKET_PATH):
    """Bottom-up units a year in the covered regions. TAM = all new-build +
    retrofit installs; SOM = the share this company can realistically win
    against local fabricators. (SAM = TAM here: the covered regions and
    target segments are already applied inside each segment's build-up.)"""
    m = pd.read_csv(path)
    col = {"low": "value_low", "base": "value_base", "high": "value_high"}[case]
    v = {(r.segment, r.step): r[col] for _, r in m.iterrows()}
    builders = (v[("Builder / real estate", "Luxury housing units launched a year in covered cities")]
                / v[("Builder / real estate", "Average luxury project size")]
                * v[("Builder / real estate", "Share of luxury projects installing a dumb waiter")]
                * v[("Builder / real estate", "Dumb waiters per installing project")])
    hotels = (v[("Hotel / restaurant", "Branded hotels opened a year (India)")]
              * v[("Hotel / restaurant", "Share of openings in covered regions")]
              * v[("Hotel / restaurant", "Share of new hotels installing")]
              * v[("Hotel / restaurant", "Dumb waiters per installing hotel")])
    restaurants = (v[("Hotel / restaurant", "Multi-floor restaurants opened a year in covered regions")]
                   * v[("Hotel / restaurant", "Share of those restaurants installing")])
    hospitals = (v[("Hospital", "Private hospital beds added a year (India)")]
                 / v[("Hospital", "Average new hospital size")]
                 * v[("Hospital", "Share of new hospitals in covered regions")]
                 * v[("Hospital", "Share installing; dumb waiters per hospital")]
                 * v[("Hospital", "Dumb waiters per installing hospital")])
    new_build = builders + hotels + restaurants + hospitals
    tam = new_build * (1 + v[("All", "Retrofit market as a multiple of new-build")])
    som = tam * v[("All", "Reachable share for this company (vs local fabricators)")]
    return {"case": case, "builders": builders, "hotels": hotels, "restaurants": restaurants,
            "hospitals": hospitals, "new_build_units": new_build, "tam_units": tam, "som_units": som,
            "competitor_price_inr": v[("All", "Typical competitor price")]}


def market_for(inputs, case="base"):
    """market_size(), with the reachable market floored at what the existing
    force already sold in the pilot year -- observed sales are a lower bound
    on what is reachable. (Multiplying every pessimistic input together
    otherwise gives a market smaller than the pilot.)"""
    mk = market_size(case)
    mk["som_floored_at_pilot"] = mk["som_units"] < inputs["n_pilot_accounts"]
    mk["som_units"] = max(mk["som_units"], float(inputs["n_pilot_accounts"]))
    return mk


# ---------------------------------------------------------------------------
# Option economics
# ---------------------------------------------------------------------------
def _ramp(months, ramp, start=1):
    m = np.arange(1, months + 1)
    return np.clip((m - start + 1) / max(1, ramp), 0, 1)


def option_cashflows(inputs, case="base", avg_rep_cost_inr=1_070_000, overrides=None,
                     market=None, price_factor=1.0, win_factor=1.0):
    """Monthly gross-margin contribution of each option, after its own costs.
    Month 0 holds one-time costs. Every option's wins are capped at the
    reachable market (SOM) for the same case."""
    k = {"low": 0, "base": 1, "high": 2}[case]
    g = {key: (v[k] if isinstance(v, tuple) else v) for key, v in GTM_ASSUMPTIONS.items()}
    g.update(overrides or {})
    market = market or market_for(inputs, case)
    som_month = market["som_units"] / 12
    ticket = inputs["avg_ticket_new_inr"] * price_factor
    gm_share = 1 - (1 - A.GROSS_MARGIN) / price_factor      # higher price, same unit cost
    leads_per_month = inputs["n_pilot_accounts"] / GTM_ASSUMPTIONS["existing_win_rate"][1] / 12
    hourly_cost = avg_rep_cost_inr / A.SELLING_HOURS_PER_REP
    m = np.arange(1, MONTHS + 1)

    def cap(w):
        return np.minimum(w, som_month)

    def margin_stream(wins):
        cum = np.cumsum(wins)
        installed_a_year_ago = np.concatenate([[0] * 12, cum[:-12]])
        amc = np.where(m > 12, installed_a_year_ago * ticket * g["amc_share_of_ticket"] / 12, 0)
        return wins * ticket * gm_share + amc * A.GROSS_MARGIN

    wins = {}
    wins["Existing sales force"] = cap(np.full(MONTHS, leads_per_month * g["existing_win_rate"] * win_factor))
    existing = margin_stream(wins["Existing sales force"]) - leads_per_month * g["rep_hours_per_lead"] * hourly_cost

    wins["Dedicated pod"] = cap(leads_per_month * g["pod_lead_uplift"] * g["pod_win_rate"] * win_factor
                                * _ramp(MONTHS, g["pod_ramp_months"]))
    pod = margin_stream(wins["Dedicated pod"]) - g["pod_reps"] * (avg_rep_cost_inr + g["pod_travel_per_rep_inr"]) / 12
    pod_one_time = g["pod_one_time_inr"] - g["pod_reps"] * avg_rep_cost_inr / 12 * A.SEVERANCE_MONTHS_OF_PAY

    def channel(wins_c, extra_monthly=0.0):
        commission = wins_c * ticket * g["partner_commission"]
        credit = wins_c * ticket * g["partner_credit_days"] / 365 * g["cost_of_capital"]
        manager = g["partner_manager_reps"] * avg_rep_cost_inr / 12
        return margin_stream(wins_c) - commission - credit - manager - extra_monthly

    base_partner = g["partner_accounts_per_year"] / 12 * win_factor * _ramp(MONTHS, g["partner_ramp_months"])
    wins["Channel partners"] = cap(base_partner)
    pull = 1 + g["architect_uplift"] * (m >= g["architect_start_month"])
    wins["Partners + architect programme"] = cap(base_partner * pull)
    chan = channel(wins["Channel partners"])
    chan_pull = channel(wins["Partners + architect programme"], g["architect_programme_inr_per_year"] / 12)
    chan_one_time = g["partner_one_time_inr"] - g["partner_manager_reps"] * avg_rep_cost_inr / 12 * A.SEVERANCE_MONTHS_OF_PAY

    df = pd.DataFrame({
        "month": np.arange(0, MONTHS + 1),
        "Existing sales force": np.concatenate([[0.0], existing]),
        "Dedicated pod": np.concatenate([[-pod_one_time], pod]),
        "Channel partners": np.concatenate([[-chan_one_time], chan]),
        "Partners + architect programme": np.concatenate([[-chan_one_time], chan_pull]),
    })
    uncapped = {"Existing sales force": leads_per_month * 12 * g["existing_win_rate"],
                "Dedicated pod": leads_per_month * 12 * g["pod_lead_uplift"] * g["pod_win_rate"],
                "Channel partners": g["partner_accounts_per_year"],
                "Partners + architect programme": g["partner_accounts_per_year"] * (1 + g["architect_uplift"])}
    capped = {o: bool(uncapped[o] * win_factor > market["som_units"]) for o in OPTIONS}
    return df, {o: float(w.sum()) for o, w in wins.items()}, capped


def payback_month(option_series, baseline_series):
    gap = np.cumsum(option_series.values - baseline_series.values)
    hit = np.where(gap >= 0)[0]
    return int(hit[0]) if len(hit) else None


def evc(inputs, case="base"):
    """Economic value to the customer for a hotel/hospital buyer.
    Reference value = what a comparable dumb waiter costs from a competitor
    (IndiaMART median); differentiation = brand and service reliability.
    Also shows the value against the true alternative (staff carrying loads)."""
    k = {"low": 0, "base": 1, "high": 2}[case]
    mkt = market_size(case)   # only the competitor price is used here
    fte = EVC["helper_fte_saved"][k]
    yearly_saving = EVC["helper_cost_inr_per_month"] * 12 * fte
    r, n = EVC["discount_rate"], EVC["life_years"]
    annuity = (1 - (1 + r) ** -n) / r
    pv_saving = yearly_saving * annuity
    evc_value = mkt["competitor_price_inr"] + EVC["differentiation_inr"]
    price = inputs["avg_ticket_new_inr"]
    return {"case": case, "current_price_inr": price, "competitor_price_inr": mkt["competitor_price_inr"],
            "evc_inr": evc_value, "headroom_inr": evc_value - price,
            "pv_staff_saving_inr": pv_saving, "payback_years_for_buyer": price / yearly_saving}


def evaluate(accounts_df, avg_rep_cost_inr=1_070_000):
    inputs = compute_inputs(accounts_df)
    rows, flows, markets = [], {}, {}
    for case in ("low", "base", "high"):
        markets[case] = market_for(inputs, case)
        cf, accts, capped = option_cashflows(inputs, case, avg_rep_cost_inr, market=markets[case])
        flows[case] = cf
        for opt in OPTIONS:
            rows.append({
                "case": case, "option": opt,
                "accounts_won_24m": accts[opt],
                "capped_by_market": capped[opt],
                "contribution_24m_inr_m": cf[opt].sum() / 1e6,
                "payback_month_vs_existing": (0 if opt == "Existing sales force"
                                              else payback_month(cf[opt], cf["Existing sales force"])),
            })
    table = pd.DataFrame(rows)
    base = table[table["case"] == "base"].set_index("option")
    best = base["contribution_24m_inr_m"].idxmax()
    holds = {c: table[table["case"] == c].set_index("option")["contribution_24m_inr_m"].idxmax()
             for c in ("low", "base", "high")}

    # Price scenario from EVC: +20% price, 10% fewer wins
    e = evc(inputs)
    cf_p, _, _ = option_cashflows(inputs, "base", avg_rep_cost_inr, market=markets["base"],
                                  price_factor=1 + EVC["price_scenario_uplift"],
                                  win_factor=EVC["win_rate_factor_at_higher_price"])
    price_scenario = {o: float(cf_p[o].sum() / 1e6) for o in OPTIONS}

    som = markets["base"]["som_units"]
    dealers = som / GTM_ASSUMPTIONS["min_installs_per_dealer"]
    leads_a_year = inputs["n_pilot_accounts"] / GTM_ASSUMPTIONS["existing_win_rate"][1]
    return {
        "inputs": inputs,
        "fit": fit_score(inputs["buyer_distance"], inputs["complexity_distance"], inputs["deal_cycle_distance"]),
        "flip_points": flip_points(inputs),
        "options": table,
        "flows": flows,
        "recommendation": best,
        "best_by_case": holds,
        "pod_break_even_win_rate": pod_break_even(inputs, avg_rep_cost_inr, markets["base"]),
        "service_outputs": service_output_scorecard(),
        "market": markets,
        "market_check": {"assumed_leads_a_year": leads_a_year, "tam_units": markets["base"]["tam_units"],
                         "som_units": som, "assumed_partner_accounts_a_year": GTM_ASSUMPTIONS["partner_accounts_per_year"][1],
                         "dealers_supportable": dealers},
        "evc": {c: evc(inputs, c) for c in ("low", "base", "high")},
        "price_scenario_contribution_24m_inr_m": price_scenario,
    }


def pod_break_even(inputs, avg_rep_cost_inr=1_070_000, market=None):
    """Pod win rate at which it matches the best other option over 24 months
    (None if the market cap stops it from ever catching up)."""
    for wr in np.arange(0.10, 0.81, 0.01):
        cf, _, _ = option_cashflows(inputs, "base", avg_rep_cost_inr, overrides={"pod_win_rate": wr}, market=market)
        others = max(cf[o].sum() for o in OPTIONS if o != "Dedicated pod")
        if cf["Dedicated pod"].sum() >= others:
            return round(float(wr), 2)
    return None


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    r = evaluate(pd.read_csv("data/generated/accounts.csv"))
    for k, v in r["inputs"].items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    print("\nFit:", r["fit"], "\nFlip points:", r["flip_points"])
    print(r["options"].round(2).to_string(index=False))
    print("\nRecommendation (base):", r["recommendation"], "| best by case:", r["best_by_case"])
    print("Pod break-even win rate:", r["pod_break_even_win_rate"])
    so = r["service_outputs"]
    print("\nService outputs:", {k: round(v, 2) for k, v in so["totals"].items()}, so["leader"],
          "margin", round(so["leader_margin"], 2), "flips:", so["single_score_changes_that_flip_leader"])
    for c, mk in r["market"].items():
        print(c, {k: (round(v) if isinstance(v, float) else v) for k, v in mk.items()})
    print("Market check:", {k: round(v, 1) for k, v in r["market_check"].items()})
    print("EVC:", {c: {k: round(v) if isinstance(v, float) else v for k, v in e.items()} for c, e in r["evc"].items()})
    print("Price +20% scenario:", {k: round(v, 2) for k, v in r["price_scenario_contribution_24m_inr_m"].items()})
