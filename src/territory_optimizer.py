"""
territory_optimizer.py — Module C: Territory Optimizer

Business question: Under the structure Module B recommends, how many reps
does this book of business need, and who should own which account?

Method: a mixed-integer program in PuLP (CBC solver).
  Decisions   keep rep i (y_i, yes/no); rep i owns account j (x_ij, yes/no)
  Objective   payroll of kept reps
              + travel + expertise risk of each assignment
              + a continuity charge for moving an account away from its
                current owner (5% of that account's yearly margin -- the
                relationship cost of a handover)
  Rules       every account has exactly one owner
              a kept rep works between 50% and 90% of selling hours
                (balance band -- no rep left with a token book)
              owners must be allowed by the structure (Module B's rules)
              an account may be left uncovered only at a prohibitive
                penalty, which flags a region that needs a hire

Workload is in hours from the workload build-up in assumptions.py. The
earlier version used an unsourced "55 complexity points per rep", which on
its own decided the answer (650 accounts x ~3 points / 55 = ~36 reps).

The optimiser is compared against three baselines, so its value is shown
rather than claimed:
  1. As-is: today's actual owners, every rep on payroll
  2. Greedy: the simple fill-the-cheapest-rep-first rule from Module B
  3. Optimiser without the continuity charge (shows what ignoring
     relationships would cost in moved accounts)

capacity_what_if() re-solves for a range of selling hours per rep, because
the headcount answer depends on that assumption more than on anything else.
"""

import os
import sys
import time

import numpy as np
import pandas as pd
import pulp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import assumptions as A  # noqa: E402
from src import coverage_simulator as B  # noqa: E402

UNCOVERED_PENALTY_INR = 5_000_000


def with_transfer_slots(reps_df, k=A.TRANSFER_SLOTS_PER_REGION):
    """Add up to k 'transfer-in' slots per region: a rep relocated from a
    region with surplus, costed at that region's average salary plus a
    one-time relocation cost (counted in year 1). Their product background
    is unknown in advance, so they count as generalists for expertise risk."""
    rows = []
    for r, g in reps_df.groupby("region_id"):
        for n in range(1, k + 1):
            rows.append({"rep_id": f"XFER-{r}-{n}", "rep_name": "Transfer-in slot", "region_id": r,
                         "specialization": "Generalist",
                         "annual_cost_inr": g["annual_cost_inr"].mean() + A.RELOCATION_COST_PER_REP_INR,
                         "tenure_years": 0, "hire_year": None})
    return pd.concat([reps_df, pd.DataFrame(rows)], ignore_index=True)


def _move_cost(acc, reps_df):
    current = acc["current_rep_id"].to_numpy(dtype=object)
    rep_ids = reps_df["rep_id"].to_numpy(dtype=object)
    moved = rep_ids[:, None] != current[None, :]
    return moved * (acc["annual_revenue_inr"].values[None, :] * A.GROSS_MARGIN * A.ACCOUNT_HANDOVER_REVENUE_LOSS)


def _solve_block(rep_idx, acc_idx, reps_df, hours, cost, elig, selling_hours, time_limit):
    prob = pulp.LpProblem("territory", pulp.LpMinimize)
    y = {i: pulp.LpVariable(f"y_{i}", cat="Binary") for i in rep_idx}
    pairs = [(i, j) for i in rep_idx for j in acc_idx if elig[i, j]]
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary") for i, j in pairs}
    u = {j: pulp.LpVariable(f"u_{j}", cat="Binary") for j in acc_idx}
    salary = reps_df["annual_cost_inr"].values
    cap_hi = selling_hours * A.MAX_UTILISATION
    cap_lo = selling_hours * A.MIN_UTILISATION

    prob += (pulp.lpSum(salary[i] * y[i] for i in rep_idx)
             + pulp.lpSum(cost[i, j] * v for (i, j), v in x.items())
             + pulp.lpSum(UNCOVERED_PENALTY_INR * u[j] for j in acc_idx))
    by_acc = {j: [] for j in acc_idx}
    by_rep = {i: [] for i in rep_idx}
    for (i, j), v in x.items():
        by_acc[j].append(v)
        by_rep[i].append((j, v))
    for j in acc_idx:
        prob += pulp.lpSum(by_acc[j]) + u[j] == 1
    for i in rep_idx:
        load = pulp.lpSum(hours[i, j] * v for j, v in by_rep[i])
        prob += load <= cap_hi * y[i]
        prob += load >= cap_lo * y[i]
    status = prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=time_limit, gapRel=0.01))

    owner = {}
    for (i, j), v in x.items():
        if v.value() and v.value() > 0.5:
            owner[j] = i
    return owner, pulp.LpStatus[status]


def optimise(accounts_df, reps_df, structure="Geographic", selling_hours=A.SELLING_HOURS_PER_REP,
             continuity=True, travel_multiplier=1.0, expertise_loss=A.EXPERTISE_GAP_MARGIN_LOSS,
             time_limit=40):
    acc = B.prepare_accounts(accounts_df)
    reps_df = with_transfer_slots(reps_df.reset_index(drop=True))
    skills, elig = B.design_structure(structure, acc, reps_df)
    hours, travel, risk, matched = B.pair_matrices(acc, reps_df, travel_multiplier, expertise_loss, skills)
    cost = travel + risk + (_move_cost(acc, reps_df) if continuity else 0.0)

    t0 = time.time()
    owner = np.full(len(acc), -1)
    statuses = []
    # Region-locked structures split into independent regional problems.
    if structure == "Geographic":
        blocks = [(np.where(reps_df["region_id"] == r)[0], np.where(acc["region_id"] == r)[0])
                  for r in sorted(acc["region_id"].unique())]
    else:
        blocks = [(np.arange(len(reps_df)), np.arange(len(acc)))]
    for rep_idx, acc_idx in blocks:
        o, s = _solve_block(list(rep_idx), list(acc_idx), reps_df, hours, cost, elig, selling_hours, time_limit)
        statuses.append(s)
        for j, i in o.items():
            owner[j] = i
    summary = summarise(acc, reps_df, owner, hours, travel, risk, matched, selling_hours)
    summary.update({"method": "Optimiser" + ("" if continuity else " (ignores current owners)"),
                    "solve_seconds": round(time.time() - t0, 1), "solver_status": ",".join(sorted(set(statuses)))})
    return summary, owner, acc


def summarise(acc, reps_df, owner, hours, travel, risk, matched, selling_hours=A.SELLING_HOURS_PER_REP):
    out = B.cost_assignment(acc, reps_df, owner, hours, travel, risk, matched, selling_hours)
    used = set(owner[owner >= 0].tolist())
    is_slot = reps_df["rep_id"].str.startswith("XFER").values
    out["transfers_in"] = int(sum(1 for i in used if is_slot[i]))
    out["transfers_by_region"] = (reps_df.iloc[[i for i in used if is_slot[i]]]["region_id"]
                                  .value_counts().sort_index().to_dict())
    out["existing_reps_kept"] = int(sum(1 for i in used if not is_slot[i]))
    out["existing_reps_freed"] = int((~is_slot).sum()) - out["existing_reps_kept"]
    current_idx = acc["current_rep_id"].map({r: k for k, r in enumerate(reps_df["rep_id"])}).values
    served = owner >= 0
    out["accounts_moved"] = int((served & (owner != current_idx)).sum())
    out["regions_short_of_capacity"] = sorted(acc.loc[~served, "region_id"].unique().tolist())
    return out


def as_is(accounts_df, reps_df, selling_hours=A.SELLING_HOURS_PER_REP):
    """Today: every rep on payroll, accounts with their current owners."""
    acc = B.prepare_accounts(accounts_df)
    reps_df = reps_df.reset_index(drop=True)
    hours, travel, risk, matched = B.pair_matrices(acc, reps_df)
    owner = acc["current_rep_id"].map({r: k for k, r in enumerate(reps_df["rep_id"])}).values
    cols = np.arange(len(acc))
    load = np.bincount(owner, weights=hours[owner, cols], minlength=len(reps_df)) / selling_hours
    out = {
        "method": "As-is (today)",
        "reps_used": len(reps_df),
        "payroll_inr_m": reps_df["annual_cost_inr"].sum() / 1e6,
        "travel_inr_m": travel[owner, cols].sum() / 1e6,
        "expertise_risk_inr_m": risk[owner, cols].sum() / 1e6,
        "uncovered_margin_inr_m": 0.0,
        "revenue_covered": 1.0,
        "expert_coverage": matched[owner[acc["needs_expert"].values], cols[acc["needs_expert"].values]].mean(),
        "utilisation_min": load.min(), "utilisation_max": load.max(),
        "reps_over_capacity": int((load > 1.0).sum()),
        "reps_under_half_loaded": int((load < A.MIN_UTILISATION).sum()),
        "accounts_moved": 0,
    }
    out["total_cost_inr_m"] = out["payroll_inr_m"] + out["travel_inr_m"] + out["expertise_risk_inr_m"]
    return out, owner


def greedy(accounts_df, reps_df, structure="Geographic", selling_hours=A.SELLING_HOURS_PER_REP):
    acc = B.prepare_accounts(accounts_df)
    reps_df = with_transfer_slots(reps_df.reset_index(drop=True))
    skills, elig = B.design_structure(structure, acc, reps_df)
    hours, travel, risk, matched = B.pair_matrices(acc, reps_df, rep_skill=skills)
    owner = B.greedy_assign(acc, reps_df, elig, hours, travel, risk, selling_hours)
    out = summarise(acc, reps_df, owner, hours, travel, risk, matched, selling_hours)
    out["method"] = "Greedy (fill cheapest first)"
    return out, owner


def compare(accounts_path="data/generated/accounts.csv", reps_path="data/generated/reps.csv", structure=None):
    accounts_df, reps_df = pd.read_csv(accounts_path), pd.read_csv(reps_path)
    if structure is None:
        structure = B.recommend(B.run_all(accounts_path, reps_path))
    base, base_owner = as_is(accounts_df, reps_df)
    g, _ = greedy(accounts_df, reps_df, structure)
    opt, opt_owner, acc = optimise(accounts_df, reps_df, structure)
    opt_free, _, _ = optimise(accounts_df, reps_df, structure, continuity=False)
    table = pd.DataFrame([base, g, opt, opt_free])
    reps_df = reps_df.reset_index(drop=True)
    reps_df = with_transfer_slots(reps_df)
    assignment = pd.DataFrame({
        "account_id": acc["account_id"], "region_id": acc["region_id"],
        "current_rep_id": acc["current_rep_id"],
        "new_rep_id": [reps_df["rep_id"].iloc[i] if i >= 0 else None for i in opt_owner],
    })
    return {"structure": structure, "table": table, "assignment": assignment}


def _assignment_lp(acc, reps_df, keep, hours, cost, elig, cap_hours):
    """Continuous assignment of accounts to the kept reps, with uncovered
    accounts costed at their lost gross margin. Returns objective (INR) and
    the value of one extra selling hour for each kept rep (from the duals of
    the capacity constraints)."""
    prob = pulp.LpProblem("assign_lp", pulp.LpMinimize)
    margin = acc["annual_revenue_inr"].values * A.GROSS_MARGIN
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", 0, 1) for i in keep for j in range(len(acc)) if elig[i, j]}
    u = {j: pulp.LpVariable(f"u_{j}", 0, 1) for j in range(len(acc))}
    prob += pulp.lpSum(cost[i, j] * v for (i, j), v in x.items()) + pulp.lpSum(margin[j] * u[j] for j in u)
    by_acc = {j: [u[j]] for j in u}
    by_rep = {i: [] for i in keep}
    for (i, j), v in x.items():
        by_acc[j].append(v)
        by_rep[i].append(hours[i, j] * v)
    for j, terms in by_acc.items():
        prob += pulp.lpSum(terms) == 1
    for i in keep:
        prob += pulp.lpSum(by_rep[i]) <= cap_hours, f"cap_{i}"
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    duals = {i: -(prob.constraints[f"cap_{i}"].pi or 0.0) for i in keep}
    return pulp.value(prob.objective), duals


def bottleneck_values(accounts_df, reps_df, structure="Geographic", kept_owner=None,
                      selling_hours=A.SELLING_HOURS_PER_REP):
    """Theory-of-Constraints view: where is capacity the binding constraint?

    For each region, reports
      * value_per_extra_hour_inr: the shadow price of rep capacity -- how much
        total cost (travel + expertise risk + margin on uncovered accounts)
        would fall with one more selling hour there. Read from the duals of
        a continuous assignment over the kept reps (shadow prices are not
        defined for the integer problem, so keep/release decisions are fixed
        first; standard practice).
      * value_of_one_more_rep_inr: cross-check without duals -- re-solve with
        one extra rep in that region (cost of that rep NOT netted off).
      * hours_short: workload left uncovered in that region.
    Run twice: on today's 56 reps, and on the redesigned team (kept_owner)."""
    acc = B.prepare_accounts(accounts_df)
    reps_df = reps_df.reset_index(drop=True)
    if kept_owner is not None:
        reps_df = with_transfer_slots(reps_df)
    skills, elig = B.design_structure(structure, acc, reps_df)
    hours, travel, risk, _ = B.pair_matrices(acc, reps_df, rep_skill=skills)
    cost = travel + risk
    if kept_owner is None:
        keep = [i for i in range(len(reps_df)) if not str(reps_df["rep_id"].iloc[i]).startswith("XFER")]
    else:
        keep = sorted(set(int(i) for i in kept_owner if i >= 0))
    cap = selling_hours * A.MAX_UTILISATION
    base_obj, duals = _assignment_lp(acc, reps_df, keep, hours, cost, elig, cap)

    rows = []
    for r in sorted(acc["region_id"].unique()):
        in_r = [i for i in keep if reps_df["region_id"].iloc[i] == r]
        # cross-check: clone the region's average rep as one extra rep
        extra = reps_df.iloc[[in_r[0]]].copy()
        extra["rep_id"] = f"EXTRA-{r}"
        extra["specialization"] = "Generalist"
        r2 = pd.concat([reps_df, extra], ignore_index=True)
        sk2, el2 = B.design_structure(structure, acc, r2)
        h2, t2, k2, _ = B.pair_matrices(acc, r2, rep_skill=sk2)
        obj2, _ = _assignment_lp(acc, r2, keep + [len(r2) - 1], h2, t2 + k2, el2, cap)
        need = acc.loc[acc["region_id"] == r, "base_hours"].sum() + \
            (acc.loc[acc["region_id"] == r, "visits"] * A.SAME_REGION_TRAVEL_HOURS).sum()
        rows.append({
            "region_id": r,
            "reps": len(in_r),
            "workload_hours": need,
            "capacity_hours": len(in_r) * cap,
            "hours_short": max(0.0, need - len(in_r) * cap),
            "value_per_extra_hour_inr": max(duals[i] for i in in_r) if in_r else None,
            "value_of_one_more_rep_inr": base_obj - obj2,
        })
    return pd.DataFrame(rows)


def capacity_what_if(accounts_path="data/generated/accounts.csv", reps_path="data/generated/reps.csv",
                     structure="Geographic", hours_grid=(750, 850, 990, 1100, 1200)):
    accounts_df, reps_df = pd.read_csv(accounts_path), pd.read_csv(reps_path)
    rows = []
    for h in hours_grid:
        s, _, _ = optimise(accounts_df, reps_df, structure, selling_hours=h, time_limit=30)
        rows.append({"selling_hours_per_rep": h, "reps_needed": s["reps_used"],
                     "payroll_inr_m": s["payroll_inr_m"], "total_cost_inr_m": s["total_cost_inr_m"],
                     "revenue_covered": s["revenue_covered"],
                     "regions_short_of_capacity": ",".join(s["regions_short_of_capacity"])})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    r = compare()
    print("Structure optimised:", r["structure"])
    cols = ["method", "reps_used", "payroll_inr_m", "travel_inr_m", "expertise_risk_inr_m",
            "uncovered_margin_inr_m", "total_cost_inr_m", "accounts_moved", "utilisation_min",
            "utilisation_max", "expert_coverage"]
    print(r["table"][cols].round(3).to_string(index=False))
    print(r["table"][["method", "solve_seconds", "solver_status", "regions_short_of_capacity",
                      "transfers_by_region", "existing_reps_freed"]].to_string(index=False))
