"""
coverage_simulator.py — Module B: Coverage Model Simulator

Business question: Which structure -- product-specialist, geographic, or
segmented hybrid -- actually minimizes cost while holding coverage and
specialization depth?

Method: simulate each structure as an eligibility rule (which reps are
allowed to serve which accounts) + a greedy capacity-constrained assignment
(hardest accounts first, cheapest eligible rep). This is deliberately
simpler than Module C's real optimizer -- it exists to compare structures
against each other, not to find the single best assignment (that's C's job,
run once the structure is chosen).

Three structures:
  - product_specialist: reps are assigned one product-line specialty
    (proportional to the account base's product mix); eligibility ignores
    region entirely.
  - geographic: reps serve only their home region, but any product line --
    this reproduces the case's actual 2009 failure mode (Haryana reps who
    couldn't answer cross-product technical questions).
  - hybrid: reps split into region-owned generalists (serve low/medium
    complexity accounts in their home region, any product) + pooled
    specialists (serve high-complexity accounts, matched by product line,
    across any region) -- the "segmented hybrid" the case gestures at but
    never actually built.

Outputs per structure: cost-to-serve (only reps actually used are paid for),
coverage-gap rate (% of accounts no eligible rep had capacity for), and
specialization depth (% of served accounts whose assigned rep's specialty
matches the account's product line).
"""

import numpy as np
import pandas as pd

CAPACITY_UNITS_PER_REP = 55.0  # a rep can carry this many "complexity points"
HYBRID_COMPLEXITY_SPLIT = 4     # complexity_score >= this -> pooled specialist tier
HYBRID_SPECIALIST_SHARE = 0.30  # fraction of the rep pool reserved as pooled specialists


def _greedy_assign(accounts_df, eligible_reps_fn, rep_specialty_fn, reps_df):
    """
    Greedy capacity-constrained assignment shared by all three structures.
    eligible_reps_fn(account_row) -> list of rep_ids allowed to serve it
    rep_specialty_fn(rep_id, account_row) -> True if it's a specialization-depth match
    Returns: assignments (dict account_id->rep_id or None), remaining_capacity (dict)
    """
    remaining_capacity = {r: CAPACITY_UNITS_PER_REP for r in reps_df["rep_id"]}
    cost_by_rep = dict(zip(reps_df["rep_id"], reps_df["annual_cost_inr"]))

    accounts_sorted = accounts_df.sort_values("complexity_score", ascending=False)
    assignments = {}
    depth_matches = {}

    for _, acct in accounts_sorted.iterrows():
        candidates = eligible_reps_fn(acct)
        candidates = [r for r in candidates if remaining_capacity.get(r, 0) >= acct["complexity_score"]]
        if not candidates:
            assignments[acct["account_id"]] = None
            continue
        # cheapest eligible rep with room wins the account
        chosen = min(candidates, key=lambda r: cost_by_rep[r])
        remaining_capacity[chosen] -= acct["complexity_score"]
        assignments[acct["account_id"]] = chosen
        depth_matches[acct["account_id"]] = rep_specialty_fn(chosen, acct)

    return assignments, depth_matches, remaining_capacity


def _summarize(structure_name, accounts_df, assignments, depth_matches, reps_df):
    n_accounts = len(accounts_df)
    served = {k: v for k, v in assignments.items() if v is not None}
    n_served = len(served)
    coverage_gap_rate = 1 - (n_served / n_accounts)

    used_reps = set(served.values())
    cost_by_rep = dict(zip(reps_df["rep_id"], reps_df["annual_cost_inr"]))
    cost_to_serve_inr = sum(cost_by_rep[r] for r in used_reps)

    depth_hits = sum(1 for v in depth_matches.values() if v)
    specialization_depth = depth_hits / n_served if n_served else 0.0

    return {
        "structure": structure_name,
        "reps_used": len(used_reps),
        "cost_to_serve_inr_m": round(cost_to_serve_inr / 1_000_000, 2),
        "coverage_gap_rate": round(coverage_gap_rate, 3),
        "specialization_depth": round(specialization_depth, 3),
        "accounts_served": n_served,
        "accounts_total": n_accounts,
    }


def simulate_product_specialist(accounts_df, reps_df, rng):
    product_lines = accounts_df["product_line"].unique().tolist()
    weights = accounts_df["product_line"].value_counts(normalize=True).reindex(product_lines).values
    rep_ids = reps_df["rep_id"].tolist()
    rep_specialty = dict(zip(rep_ids, rng.choice(product_lines, size=len(rep_ids), p=weights)))

    def eligible(acct):
        return [r for r in rep_ids if rep_specialty[r] == acct["product_line"]]

    def is_depth_match(rep_id, acct):
        return rep_specialty[rep_id] == acct["product_line"]

    assignments, depth, _ = _greedy_assign(accounts_df, eligible, is_depth_match, reps_df)
    return _summarize("Product Specialist", accounts_df, assignments, depth, reps_df)


def simulate_geographic(accounts_df, reps_df):
    rep_region = dict(zip(reps_df["rep_id"], reps_df["region_id"]))
    reps_by_region = reps_df.groupby("region_id")["rep_id"].apply(list).to_dict()

    def eligible(acct):
        return reps_by_region.get(acct["region_id"], [])

    def is_depth_match(rep_id, acct):
        # Geographic reps have no enforced product specialty -- a rep only
        # "matches" if their (fixed, pre-existing) specialization field
        # happens to line up, same low-probability event that sank the
        # case's Haryana rollout.
        return False  # conservatively: pure-geo reps are treated as generalists, no depth credit

    assignments, depth, _ = _greedy_assign(accounts_df, eligible, is_depth_match, reps_df)
    return _summarize("Geographic", accounts_df, assignments, depth, reps_df)


def simulate_hybrid(accounts_df, reps_df, rng):
    rep_ids = reps_df["rep_id"].tolist()
    rng.shuffle(rep_ids)
    n_specialists = int(len(rep_ids) * HYBRID_SPECIALIST_SHARE)
    specialist_ids = set(rep_ids[:n_specialists])
    generalist_ids = set(rep_ids[n_specialists:])

    product_lines = accounts_df["product_line"].unique().tolist()
    weights = accounts_df["product_line"].value_counts(normalize=True).reindex(product_lines).values
    specialist_specialty = dict(
        zip(specialist_ids, rng.choice(product_lines, size=len(specialist_ids), p=weights))
    )
    rep_region = dict(zip(reps_df["rep_id"], reps_df["region_id"]))
    generalists_by_region = (
        reps_df[reps_df["rep_id"].isin(generalist_ids)]
        .groupby("region_id")["rep_id"].apply(list).to_dict()
    )

    def eligible(acct):
        if acct["complexity_score"] >= HYBRID_COMPLEXITY_SPLIT:
            return [r for r in specialist_ids if specialist_specialty[r] == acct["product_line"]]
        return generalists_by_region.get(acct["region_id"], [])

    def is_depth_match(rep_id, acct):
        if rep_id in specialist_ids:
            return specialist_specialty[rep_id] == acct["product_line"]
        return False

    assignments, depth, _ = _greedy_assign(accounts_df, eligible, is_depth_match, reps_df)
    return _summarize("Segmented Hybrid", accounts_df, assignments, depth, reps_df)


def simulate_spectrum(accounts_df, reps_df, rng, specialist_share):
    """
    A continuous Geographic <-> Product Specialist dial, for the live
    Scenario Dashboard slider -- NOT a replacement for the three discrete
    structures above (those are the Stage 2 checkpoint result, unchanged).

    Eligibility is a union, not a gate: an account can be served by (a) a
    pooled specialist whose specialty matches its product line, from any
    region, or (b) a region generalist in its home region, for any product
    line. At specialist_share=0, every rep is a generalist -> this reduces
    exactly to the Geographic structure (0% depth by construction). At
    specialist_share=1, every rep is a specialist -> reduces to the Product
    Specialist structure. Because eligibility is a union rather than a
    complexity-gated split (unlike the fixed Hybrid structure above), no
    account is ever stranded partway through the dial -- coverage gap stays
    at or near 0% across the whole range, and what moves is cost and depth.
    """
    rep_ids = reps_df["rep_id"].tolist()
    shuffled = rep_ids.copy()
    rng.shuffle(shuffled)
    n_specialists = int(round(len(shuffled) * specialist_share))
    specialist_ids = set(shuffled[:n_specialists])
    generalist_ids = set(shuffled[n_specialists:])

    product_lines = accounts_df["product_line"].unique().tolist()
    weights = accounts_df["product_line"].value_counts(normalize=True).reindex(product_lines).values
    specialist_specialty = (
        dict(zip(specialist_ids, rng.choice(product_lines, size=len(specialist_ids), p=weights)))
        if specialist_ids else {}
    )
    generalists_by_region = (
        reps_df[reps_df["rep_id"].isin(generalist_ids)]
        .groupby("region_id")["rep_id"].apply(list).to_dict()
    )

    def eligible(acct):
        specialist_matches = [r for r in specialist_ids if specialist_specialty[r] == acct["product_line"]]
        generalist_matches = generalists_by_region.get(acct["region_id"], [])
        return specialist_matches + generalist_matches

    def is_depth_match(rep_id, acct):
        return rep_id in specialist_ids and specialist_specialty[rep_id] == acct["product_line"]

    assignments, depth, _ = _greedy_assign(accounts_df, eligible, is_depth_match, reps_df)
    result = _summarize(f"Spectrum ({specialist_share:.0%} specialist)", accounts_df, assignments, depth, reps_df)
    result["specialist_share"] = specialist_share
    return result


def run_all(accounts_path="data/generated/accounts.csv",
            reps_path="data/generated/reps.csv", seed=42):
    accounts_df = pd.read_csv(accounts_path)
    reps_df = pd.read_csv(reps_path)
    rng = np.random.default_rng(seed)

    results = [
        simulate_product_specialist(accounts_df, reps_df, rng),
        simulate_geographic(accounts_df, reps_df),
        simulate_hybrid(accounts_df, reps_df, rng),
    ]
    return pd.DataFrame(results)


if __name__ == "__main__":
    df = run_all()
    print(df.to_string(index=False))
