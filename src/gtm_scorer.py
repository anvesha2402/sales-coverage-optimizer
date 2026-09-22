"""
gtm_scorer.py — Module D: New-Product GTM Scorer

Business question: When a new product targets a new buyer persona, should
it go through the existing sales force or a dedicated pod?

Method: a transparent weighted-scoring formula over three distances from
the existing motion (buyer-persona, technical-complexity, deal-cycle),
plus a breakeven-time comparison between a dedicated pod's setup cost and
its faster ramp. Chosen over a classifier (the plan's stated alternative)
because there is no historical launch-outcome data to train on here, and a
transparent formula is easier to defend and reuse for the next product than
a black box fit on a synthetic proxy.

Reusability: score_new_product_gtm() takes three 0-1 distance/difference
inputs directly, so it works for ANY new product -- not just the Dumb
Waiter. The Dumb Waiter-specific numbers below are one applied example,
built from accounts.csv plus a small, explicitly-stated assumption table
for deal-cycle length (not present in the synthetic dataset, since it's a
process attribute, not a customer attribute -- see ASSUMED_DEAL_CYCLE_DAYS).
"""

import pandas as pd

DEFAULT_WEIGHTS = {
    "buyer_persona_distance": 0.4,
    "technical_complexity_distance": 0.35,
    "deal_cycle_diff": 0.25,
}
POD_RECOMMENDATION_THRESHOLD = 0.5  # score above this -> dedicated pod

# Not in the synthetic dataset (deal cycle is a process attribute, not a
# customer attribute) -- stated explicitly as a business assumption, not
# fabricated data. Dumb Waiter assumed shorter and more transactional:
# lower price point, targeted at builders/real estate rather than the
# industrial turnkey sales cycle of the other three lines (per the case).
ASSUMED_DEAL_CYCLE_DAYS = {
    "Conveyor Systems": 95,
    "Elevator Systems": 80,
    "Bulk Material Handling": 105,
    "Dumb Waiter (New Product)": 40,
}

# One-time setup cost of standing up a dedicated pod (hiring + specialized
# training) -- also an explicit assumption, documented rather than derived,
# scaled off the same per-rep cost basis used elsewhere in this project.
POD_SETUP_COST_INR = 1_200_000 * 3  # 3 dedicated reps at ~1.2M fully-loaded


def score_new_product_gtm(
    buyer_persona_distance, technical_complexity_distance, deal_cycle_diff,
    weights=None,
):
    """
    All three inputs normalized to [0, 1] (0 = identical to existing motion,
    1 = maximally different). Returns a 0-1 score and a recommendation.
    """
    w = weights or DEFAULT_WEIGHTS
    score = (
        w["buyer_persona_distance"] * buyer_persona_distance
        + w["technical_complexity_distance"] * technical_complexity_distance
        + w["deal_cycle_diff"] * deal_cycle_diff
    )
    recommendation = "Dedicated pod" if score >= POD_RECOMMENDATION_THRESHOLD else "Existing sales force"
    return {
        "score": round(score, 3),
        "recommendation": recommendation,
        "inputs": {
            "buyer_persona_distance": round(buyer_persona_distance, 3),
            "technical_complexity_distance": round(technical_complexity_distance, 3),
            "deal_cycle_diff": round(deal_cycle_diff, 3),
        },
    }


def breakeven_months(pod_setup_cost_inr, monthly_revenue_gain_inr):
    """
    Months for a dedicated pod's faster ramp (extra monthly revenue capture
    vs. a generalist rollout) to pay back its one-time setup cost.
    """
    if monthly_revenue_gain_inr <= 0:
        return float("inf")
    return round(pod_setup_cost_inr / monthly_revenue_gain_inr, 1)


def compute_dumb_waiter_inputs(accounts_path="data/generated/accounts.csv"):
    """
    Derives the three distance inputs for the Dumb Waiter launch from the
    account base: how different is its typical account from the existing
    three product lines' typical account, on the dimensions the formula
    cares about.
    """
    df = pd.read_csv(accounts_path)
    new_product = "Dumb Waiter (New Product)"
    existing = df[df["product_line"] != new_product]
    new = df[df["product_line"] == new_product]

    # Technical-complexity distance: normalized gap in mean complexity_score (1-5 scale)
    complexity_gap = abs(new["complexity_score"].mean() - existing["complexity_score"].mean())
    technical_complexity_distance = min(1.0, complexity_gap / 4.0)  # scale 0-4 range -> 0-1

    # Buyer-persona distance: proxy from how differently the new product's
    # accounts are distributed across regions vs. the existing base (a
    # product selling to a genuinely different buyer tends to cluster
    # differently geographically/by account size than the core motion).
    region_dist_new = new["region_id"].value_counts(normalize=True)
    region_dist_existing = existing["region_id"].value_counts(normalize=True)
    all_regions = set(region_dist_new.index) | set(region_dist_existing.index)
    region_l1_distance = sum(
        abs(region_dist_new.get(r, 0) - region_dist_existing.get(r, 0)) for r in all_regions
    ) / 2  # total variation distance, naturally in [0, 1]

    avg_rev_new = new["annual_revenue_inr"].mean()
    avg_rev_existing = existing["annual_revenue_inr"].mean()
    revenue_l1_distance = min(1.0, abs(avg_rev_new - avg_rev_existing) / max(avg_rev_new, avg_rev_existing))

    buyer_persona_distance = 0.5 * region_l1_distance + 0.5 * revenue_l1_distance

    # Deal-cycle diff: normalized gap vs. the (revenue-weighted) average of
    # the other three lines' assumed cycle length.
    existing_cycle = sum(
        ASSUMED_DEAL_CYCLE_DAYS[pl] * (existing["product_line"] == pl).sum()
        for pl in ASSUMED_DEAL_CYCLE_DAYS if pl != new_product
    ) / len(existing)
    new_cycle = ASSUMED_DEAL_CYCLE_DAYS[new_product]
    deal_cycle_diff = min(1.0, abs(new_cycle - existing_cycle) / existing_cycle)

    return {
        "technical_complexity_distance": technical_complexity_distance,
        "buyer_persona_distance": buyer_persona_distance,
        "deal_cycle_diff": deal_cycle_diff,
        "n_new_product_accounts": len(new),
        "avg_revenue_new_inr": round(avg_rev_new, 0),
        "avg_revenue_existing_inr": round(avg_rev_existing, 0),
        "assumed_cycle_new_days": new_cycle,
        "assumed_cycle_existing_weighted_days": round(existing_cycle, 1),
    }


if __name__ == "__main__":
    inputs = compute_dumb_waiter_inputs()
    print("Derived inputs for the Dumb Waiter launch:")
    for k, v in inputs.items():
        print(f"  {k}: {v}")

    result = score_new_product_gtm(
        buyer_persona_distance=inputs["buyer_persona_distance"],
        technical_complexity_distance=inputs["technical_complexity_distance"],
        deal_cycle_diff=inputs["deal_cycle_diff"],
    )
    print(f"\nGTM score: {result['score']}  ->  {result['recommendation']}")

    # Breakeven: assume a dedicated pod ramps to full productivity ~2 months
    # faster than folding the product into the existing generalist motion
    # (per the case, generalists took time to build product-specific
    # credibility -- the Haryana complaint). Monthly revenue gain = 2 months
    # of average new-product account revenue captured earlier, spread
    # across the pod's target book.
    assumed_accounts_per_pod_year1 = 40
    monthly_gain = (inputs["avg_revenue_new_inr"] * assumed_accounts_per_pod_year1) / 12
    be_months = breakeven_months(POD_SETUP_COST_INR, monthly_gain)
    print(f"Dedicated-pod setup cost: INR {POD_SETUP_COST_INR:,.0f}")
    print(f"Assumed monthly revenue gain from faster ramp: INR {monthly_gain:,.0f}")
    print(f"Breakeven: {be_months} months")
