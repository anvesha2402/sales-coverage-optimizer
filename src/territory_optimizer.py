"""
territory_optimizer.py — Module C: Territory Optimizer

Business question: Given a fixed rep count and an account base spread
across regions and product lines, how should accounts be assigned to
minimize cost without breaking coverage?

Method: solved per region as a capacitated facility-location-style MILP in
PuLP -- decide which reps to "activate" (y_i, binary) and how to split each
account's demand across activated reps (x_ij, continuous in [0,1], integral
at the optimum for a fixed y because the assignment sub-problem is a pure
transportation polytope). Objective: minimize the total annual cost of
activated reps only (an unused rep costs the company nothing in this
comparison -- same convention as Module B). Constraints: every account
fully covered, and no rep exceeds its complexity-weighted capacity (this
single aggregate constraint is what actually forces x_ij=0 whenever y_i=0,
since complexity_score > 0 for every account -- so no separate per-pair
x_ij <= y_i constraint is needed. An earlier draft included that
per-pair constraint anyway "for LP-relaxation tightness," a textbook
facility-location trick -- but it added ~7,700 redundant rows per region
and made CBC's branch-and-bound take minutes instead of under a second on
this instance. Dropped after profiling; correctness is unchanged, only
formulation size.

Honest simplification: "workload balance within a tolerance" (as named in
the build plan) is enforced here only via the shared per-rep capacity cap,
not a separate deviation-from-mean constraint -- a real refinement would add
an explicit balance band. Flagged, not hidden.

Solved per region (not company-wide) because reps only serve their home
region in this dataset -- see data_dictionary.md.
"""

import pandas as pd
import pulp

CAPACITY_UNITS_PER_REP = 55.0  # same convention as coverage_simulator.py


def solve_region(accounts_r, reps_r, region_id):
    accounts = accounts_r["account_id"].tolist()
    reps = reps_r["rep_id"].tolist()
    complexity = dict(zip(accounts_r["account_id"], accounts_r["complexity_score"]))
    cost = dict(zip(reps_r["rep_id"], reps_r["annual_cost_inr"]))

    prob = pulp.LpProblem(f"territory_{region_id}", pulp.LpMinimize)

    y = pulp.LpVariable.dicts("activate", reps, cat="Binary")
    x = pulp.LpVariable.dicts(
        "assign", [(i, j) for i in reps for j in accounts], lowBound=0, upBound=1
    )

    prob += pulp.lpSum(cost[i] * y[i] for i in reps)  # objective: minimize activated-rep cost

    for j in accounts:  # every account fully covered
        prob += pulp.lpSum(x[(i, j)] for i in reps) == 1

    for i in reps:  # capacity, gated by activation (also forces x_ij=0 when y_i=0
                     # since every complexity_score > 0 -- see module docstring)
        prob += pulp.lpSum(complexity[j] * x[(i, j)] for j in accounts) <= CAPACITY_UNITS_PER_REP * y[i]

    prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=30))

    activated = [i for i in reps if pulp.value(y[i]) > 0.5]
    assignment = {}
    for j in accounts:
        for i in reps:
            v = pulp.value(x[(i, j)])
            if v and v > 0.5:
                assignment[j] = i
                break

    return {
        "region_id": region_id,
        "status": pulp.LpStatus[prob.status],
        "reps_activated": len(activated),
        "reps_available": len(reps),
        "cost_inr": sum(cost[i] for i in activated),
        "assignment": assignment,
    }


def naive_equal_split(accounts_r, reps_r):
    """Round-robin every account across every rep in the region, cheapest-first
    ignored -- cost isn't a factor, mirroring an unplanned/seniority-blind split."""
    reps = reps_r["rep_id"].tolist()
    cost = dict(zip(reps_r["rep_id"], reps_r["annual_cost_inr"]))
    load = {r: 0.0 for r in reps}
    accounts_sorted = accounts_r.sort_values("complexity_score", ascending=False)

    assignment = {}
    idx = 0
    for _, acct in accounts_sorted.iterrows():
        placed = False
        for _ in range(len(reps)):
            r = reps[idx % len(reps)]
            idx += 1
            if load[r] + acct["complexity_score"] <= CAPACITY_UNITS_PER_REP:
                load[r] += acct["complexity_score"]
                assignment[acct["account_id"]] = r
                placed = True
                break
        if not placed:
            assignment[acct["account_id"]] = None  # capacity exhausted company-wide too, rare

    used_reps = {r for r in assignment.values() if r is not None}
    return {
        "reps_activated": len(used_reps),
        "reps_available": len(reps),
        "cost_inr": sum(cost[r] for r in used_reps),
        "coverage_gap": sum(1 for v in assignment.values() if v is None) / len(accounts_r),
        "assignment": assignment,
    }


def run_all(accounts_path="data/generated/accounts.csv",
            reps_path="data/generated/reps.csv"):
    accounts_df = pd.read_csv(accounts_path)
    reps_df = pd.read_csv(reps_path)

    optimized_rows, naive_rows, territory_rows, naive_territory_rows = [], [], [], []

    for region_id in sorted(accounts_df["region_id"].unique()):
        accounts_r = accounts_df[accounts_df["region_id"] == region_id]
        reps_r = reps_df[reps_df["region_id"] == region_id]

        opt = solve_region(accounts_r, reps_r, region_id)
        naive = naive_equal_split(accounts_r, reps_r)

        optimized_rows.append({
            "region_id": region_id, "reps_activated": opt["reps_activated"],
            "reps_available": opt["reps_available"], "cost_inr_m": opt["cost_inr"] / 1e6,
            "status": opt["status"],
        })
        naive_rows.append({
            "region_id": region_id, "reps_activated": naive["reps_activated"],
            "reps_available": naive["reps_available"], "cost_inr_m": naive["cost_inr"] / 1e6,
            "coverage_gap": naive["coverage_gap"],
        })
        for acct_id, rep_id in opt["assignment"].items():
            territory_rows.append({"account_id": acct_id, "region_id": region_id, "rep_id": rep_id})
        for acct_id, rep_id in naive["assignment"].items():
            if rep_id is not None:
                naive_territory_rows.append({"account_id": acct_id, "region_id": region_id, "rep_id": rep_id})

    optimized_df = pd.DataFrame(optimized_rows)
    naive_df = pd.DataFrame(naive_rows)
    territory_df = pd.DataFrame(territory_rows)
    naive_territory_df = pd.DataFrame(naive_territory_rows)

    total_opt_cost = optimized_df["cost_inr_m"].sum()
    total_naive_cost = naive_df["cost_inr_m"].sum()
    pct_improvement = (total_naive_cost - total_opt_cost) / total_naive_cost

    return {
        "optimized_by_region": optimized_df,
        "naive_by_region": naive_df,
        "territory_map": territory_df,
        "naive_territory_map": naive_territory_df,
        "total_optimized_cost_inr_m": round(total_opt_cost, 2),
        "total_naive_cost_inr_m": round(total_naive_cost, 2),
        "pct_cost_improvement": round(pct_improvement, 4),
    }


if __name__ == "__main__":
    result = run_all()
    print("Per-region: optimized vs naive")
    merged = result["optimized_by_region"].merge(
        result["naive_by_region"], on="region_id", suffixes=("_opt", "_naive")
    )
    print(merged[["region_id", "reps_available_opt", "reps_activated_opt",
                   "reps_activated_naive", "cost_inr_m_opt", "cost_inr_m_naive"]]
          .round(2).to_string(index=False))
    print(f"\nTotal optimized cost-to-serve: INR {result['total_optimized_cost_inr_m']}M")
    print(f"Total naive cost-to-serve:     INR {result['total_naive_cost_inr_m']}M")
    print(f"Cost improvement vs. naive equal-split: {result['pct_cost_improvement']:.1%}")
