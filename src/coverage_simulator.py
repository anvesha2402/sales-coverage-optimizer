"""
coverage_simulator.py — Module B: Coverage Model Simulator

Business question: Which structure -- Geographic, Product Specialist, or a
Segmented Hybrid -- covers the book of business at the lowest total cost?

What changed from the first version, and why:
  * Everything is in one currency. A structure's total cost is
        payroll of reps needed + travel + expertise risk + uncovered margin
    Earlier versions compared salary only, which made travel free -- and
    travel is the reason the real company went geographic in 2009. The old
    "specialization depth" score (100% / 0% by definition) is replaced by
    expertise risk: margin expected to be lost on complex accounts served
    by someone without expertise in that product (the Haryana lesson).
  * Workload is in hours from the workload build-up in assumptions.py, not
    an invented 55-point cap.
  * The Hybrid is built from account segmentation (who handles complex
    accounts), not a random 30% of reps, and specialists are sized from the
    complex-account workload.
  * No randomness inside a structure. Robustness is tested by re-running all
    three structures on 100 different generated account bases
    (robustness()), and the two most judgement-heavy inputs -- travel cost
    and the expertise-loss rate -- are swept in what_if_grid().

The assignment inside each structure is a greedy rule (biggest accounts
first, cheapest eligible rep with room). It compares structures; Module C
then optimises the winning one properly.
"""

import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import assumptions as A  # noqa: E402

STRUCTURES = ["Geographic", "Product Specialist", "Segmented Hybrid"]
TIE_TOLERANCE = 0.01


def recommend(results_df):
    """Cheapest structure; if the runner-up is within TIE_TOLERANCE, prefer
    the simpler one to run (Geographic < Segmented Hybrid < Product Specialist)."""
    simplicity = {"Geographic": 0, "Segmented Hybrid": 1, "Product Specialist": 2}
    best = results_df["total_cost_inr_m"].min()
    close = results_df[results_df["total_cost_inr_m"] <= best * (1 + TIE_TOLERANCE)]
    return min(close["structure"], key=simplicity.get)


# ---------------------------------------------------------------------------
# Workload and cost building blocks (shared with Module C)
# ---------------------------------------------------------------------------
def prepare_accounts(accounts_df):
    df = accounts_df.copy()
    df["tier"] = A.assign_tiers(df)
    df["visits"] = [A.visits_per_year(c, t) for c, t in zip(df["complexity_score"], df["tier"])]
    df["base_hours"] = df["visits"] * A.HOURS_PER_VISIT + A.ACCOUNT_ADMIN_HOURS_PER_YEAR
    df["is_complex"] = df["complexity_score"] >= A.COMPLEX_ACCOUNT_THRESHOLD
    return df.reset_index(drop=True)


def pair_matrices(acc, reps_df, travel_multiplier=1.0, expertise_loss=A.EXPERTISE_GAP_MARGIN_LOSS,
                  rep_skill=None):
    """Hours and rupee cost (travel + expertise risk) of every rep serving
    every account. Shape: (n_reps, n_accounts)."""
    regions = sorted(A.REGION_CENTROIDS)
    idx = {r: i for i, r in enumerate(regions)}
    th = np.zeros((6, 6))
    tc = np.zeros((6, 6))
    for a in regions:
        for b in regions:
            th[idx[a], idx[b]], tc[idx[a], idx[b]] = A.travel_per_visit(a, b, travel_multiplier)
    rr = reps_df["region_id"].map(idx).values
    ar = acc["region_id"].map(idx).values
    visits = acc["visits"].values
    hours = acc["base_hours"].values[None, :] + visits[None, :] * th[rr][:, ar]
    travel = visits[None, :] * tc[rr][:, ar]
    skill = rep_skill if rep_skill is not None else reps_df["specialization"].to_numpy(dtype=object)
    matched = skill[:, None] == acc["product_line"].to_numpy(dtype=object)[None, :]
    risk = (~matched) * acc["is_complex"].values[None, :] * (
        acc["annual_revenue_inr"].values[None, :] * A.GROSS_MARGIN * expertise_loss)
    return hours, travel, risk, matched


def usable_hours(selling_hours=A.SELLING_HOURS_PER_REP):
    return selling_hours * A.MAX_UTILISATION


# ---------------------------------------------------------------------------
# Structure design: who is allowed to serve what
# ---------------------------------------------------------------------------
def _fill_skills_by_workload(acc, reps_df, skills, rep_order):
    """Give generalists (skill None) a product line, largest workload gap first."""
    need = acc.groupby("product_line")["base_hours"].sum()
    have = pd.Series(0.0, index=need.index)
    for s in skills:
        if s in have.index:
            have[s] += usable_hours()
    for i in rep_order:
        if skills[i] is None:
            gap = (need - have).sort_values(ascending=False)
            skills[i] = gap.index[0]
            have[gap.index[0]] += usable_hours()
    return skills


def design_structure(name, acc, reps_df, specialist_share=None):
    """Returns (skill array, eligibility matrix [reps x accounts])."""
    n_r = len(reps_df)
    base_skill = np.array([s if s != "Generalist" else None for s in reps_df["specialization"]], dtype=object)
    same_region = reps_df["region_id"].to_numpy(dtype=object)[:, None] == acc["region_id"].to_numpy(dtype=object)[None, :]
    product = acc["product_line"].to_numpy(dtype=object)[None, :]

    if name == "Geographic":
        return base_skill, same_region

    if name == "Product Specialist":
        skills = _fill_skills_by_workload(acc, reps_df, list(base_skill), range(n_r))
        skills = np.array(skills, dtype=object)
        return skills, skills[:, None] == product

    if name == "Segmented Hybrid":
        # Segmentation: complex accounts (>= threshold) go to a pooled
        # product-specialist overlay; everything else to regional reps.
        # Overlay size per product = complex-account workload / usable hours,
        # drawn from reps already skilled in that line, based where the
        # line's complex accounts concentrate.
        complex_acc = acc[acc["is_complex"]]
        avg_travel_extra = complex_acc["visits"].mean() * 4.0   # rough cross-region uplift
        hrs = complex_acc.groupby("product_line")["base_hours"].sum() + \
            complex_acc.groupby("product_line").size() * avg_travel_extra
        overlay = np.zeros(n_r, dtype=bool)
        skills = base_skill.copy()
        for line, h in hrs.items():
            k = math.ceil(h / usable_hours())
            hot = complex_acc[complex_acc["product_line"] == line]["region_id"].value_counts()
            cands = reps_df[(reps_df["specialization"] == line)].copy()
            cands["heat"] = cands["region_id"].map(hot).fillna(0)
            cands = cands.sort_values(["heat", "tenure_years"], ascending=False)
            chosen = cands.index[:k]
            overlay[chosen] = True
        is_complex = acc["is_complex"].values[None, :]
        # Overlay specialists take complex accounts of their line anywhere and
        # can still pick up any account in their home region; regional reps
        # cover their region, including complex accounts the overlay has no
        # room for (priced with expertise risk).
        elig_overlay = overlay[:, None] & (skills[:, None] == product) & is_complex
        return skills, elig_overlay | same_region

    if name == "Spectrum":
        # Dial from Geographic (0) to Product Specialist (1): the first
        # `share` of reps (existing specialists first, then generalists)
        # become cross-region product specialists; the rest stay regional.
        k = int(round(n_r * specialist_share))
        order = sorted(range(n_r), key=lambda i: (base_skill[i] is None, -reps_df["tenure_years"].iloc[i]))
        pooled = np.zeros(n_r, dtype=bool)
        pooled[order[:k]] = True
        skills = list(base_skill)
        skills = np.array(_fill_skills_by_workload(acc, reps_df, skills, [i for i in order[:k]]), dtype=object)
        elig = np.where(pooled[:, None], skills[:, None] == product, same_region)
        return skills, elig

    raise ValueError(name)


# ---------------------------------------------------------------------------
# Greedy assignment + costing
# ---------------------------------------------------------------------------
def greedy_assign(acc, reps_df, elig, hours, travel, risk, selling_hours=A.SELLING_HOURS_PER_REP):
    cap = np.full(len(reps_df), usable_hours(selling_hours))
    salary = reps_df["annual_cost_inr"].values
    active = np.zeros(len(reps_df), dtype=bool)
    owner = np.full(len(acc), -1)
    for j in np.argsort(-acc["base_hours"].values, kind="stable"):
        ok = elig[:, j] & (cap >= hours[:, j])
        if not ok.any():
            continue
        # cost of the rep time this account uses + travel + expertise risk;
        # cheapest reps fill up first, so the book is packed onto few reps
        score = travel[:, j] + risk[:, j] + salary * hours[:, j] / usable_hours(selling_hours)
        score = np.where(ok, score, np.inf)
        i = int(np.argmin(score))
        owner[j] = i
        cap[i] -= hours[i, j]
        active[i] = True
    return owner


def cost_assignment(acc, reps_df, owner, hours, travel, risk, matched, selling_hours=A.SELLING_HOURS_PER_REP):
    served = owner >= 0
    cols = np.where(served)[0]
    used = np.unique(owner[served])
    payroll = reps_df["annual_cost_inr"].values[used].sum()
    travel_cost = travel[owner[cols], cols].sum()
    risk_cost = risk[owner[cols], cols].sum()
    gap_cost = (acc["annual_revenue_inr"].values[~served] * A.GROSS_MARGIN).sum()
    complex_served = served & acc["is_complex"].values
    cx_cols = np.where(complex_served)[0]
    expert_share = matched[owner[cx_cols], cx_cols].mean() if len(cx_cols) else 1.0
    load = np.bincount(owner[served], weights=hours[owner[cols], cols], minlength=len(reps_df))[used]
    rev = acc["annual_revenue_inr"].values
    return {
        "reps_used": len(used),
        "payroll_inr_m": payroll / 1e6,
        "travel_inr_m": travel_cost / 1e6,
        "expertise_risk_inr_m": risk_cost / 1e6,
        "uncovered_margin_inr_m": gap_cost / 1e6,
        "total_cost_inr_m": (payroll + travel_cost + risk_cost + gap_cost) / 1e6,
        "revenue_covered": rev[served].sum() / rev.sum(),
        "complex_accounts_with_expert": expert_share,
        "utilisation_min": (load / selling_hours).min() if len(load) else 0.0,
        "utilisation_max": (load / selling_hours).max() if len(load) else 0.0,
    }


def simulate(name, accounts_df, reps_df, travel_multiplier=1.0,
             expertise_loss=A.EXPERTISE_GAP_MARGIN_LOSS, specialist_share=None,
             selling_hours=A.SELLING_HOURS_PER_REP, acc=None, return_owner=False):
    acc = acc if acc is not None else prepare_accounts(accounts_df)
    reps_df = reps_df.reset_index(drop=True)
    skills, elig = design_structure(name, acc, reps_df, specialist_share)
    hours, travel, risk, matched = pair_matrices(acc, reps_df, travel_multiplier, expertise_loss, skills)
    owner = greedy_assign(acc, reps_df, elig, hours, travel, risk, selling_hours)
    out = {"structure": name if name != "Spectrum" else f"Spectrum {specialist_share:.0%}"}
    out.update(cost_assignment(acc, reps_df, owner, hours, travel, risk, matched, selling_hours))
    if return_owner:
        return out, owner, skills, elig
    return out


def run_all(accounts_path="data/generated/accounts.csv", reps_path="data/generated/reps.csv", **kw):
    accounts_df, reps_df = pd.read_csv(accounts_path), pd.read_csv(reps_path)
    acc = prepare_accounts(accounts_df)
    return pd.DataFrame([simulate(s, accounts_df, reps_df, acc=acc, **kw) for s in STRUCTURES])


def spectrum(accounts_df, reps_df, shares=range(0, 101, 5), **kw):
    acc = prepare_accounts(accounts_df)
    return pd.DataFrame([dict(simulate("Spectrum", accounts_df, reps_df, specialist_share=s / 100, acc=acc, **kw),
                              share=s) for s in shares])


def robustness(n_runs=100):
    """Re-generate the account base and rep pool 100 times (seeds 1-100) and
    re-run all three structures. Reports each structure's cost range and how
    often it wins -- the answer to 'is the ranking a fluke of one dataset?'."""
    from data import generate_synthetic_company as gen
    rows = []
    for seed in range(1, n_runs + 1):
        t = gen.generate(seed)
        acc = prepare_accounts(t["accounts"])
        for s in STRUCTURES:
            r = simulate(s, t["accounts"], t["reps"], acc=acc)
            r["seed"] = seed
            rows.append(r)
    runs = pd.DataFrame(rows)
    # Within 1% of the cheapest counts as a tie, not a win: differences that
    # small are inside the precision of the assumptions.
    best = runs.groupby("seed")["total_cost_inr_m"].transform("min")
    within = runs["total_cost_inr_m"] <= best * (1 + TIE_TOLERANCE)
    n_within = within.groupby(runs["seed"]).transform("sum")
    runs["outright_win"] = within & (n_within == 1)
    runs["tied_best"] = within & (n_within > 1)
    summary = runs.groupby("structure").agg(
        cost_mean=("total_cost_inr_m", "mean"),
        cost_p10=("total_cost_inr_m", lambda x: x.quantile(0.10)),
        cost_p90=("total_cost_inr_m", lambda x: x.quantile(0.90)),
        outright_win_share=("outright_win", "mean"),
        tied_best_share=("tied_best", "mean"),
        reps_mean=("reps_used", "mean"),
        expert_share_mean=("complex_accounts_with_expert", "mean"),
    ).reindex(STRUCTURES)
    return runs, summary


def what_if_grid(accounts_df, reps_df, travel_multipliers=(0.5, 1.0, 1.5, 2.0),
                 expertise_losses=(0.0, 0.05, 0.10, 0.15, 0.20, 0.25)):
    """Which structure wins as the two judgement-heavy inputs move."""
    acc = prepare_accounts(accounts_df)
    rows = []
    for tm in travel_multipliers:
        for el in expertise_losses:
            res = {s: simulate(s, accounts_df, reps_df, travel_multiplier=tm, expertise_loss=el, acc=acc)
                   for s in STRUCTURES}
            best = min(res, key=lambda s: res[s]["total_cost_inr_m"])
            rows.append({"travel_multiplier": tm, "expertise_loss": el, "winner": best,
                         **{f"{s}_cost": res[s]["total_cost_inr_m"] for s in STRUCTURES}})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(run_all().round(3).to_string(index=False))
