# Business Insights — Stage 2 Checkpoint

Filled in with real output from `src/`, run against the seed-42 synthetic
dataset. Not the build plan's illustrative language — this is what the code
actually returned.

---

## A. Diagnostic Engine

**Output:** Sustainability score **14/100**. Threshold year **2023** — the
first year net margin drops below 10% (it lands at 6.6%, then 1.0% by 2024).
Sales-cost-to-total-cost climbs every single year: 21% → 28% → 33% → 37% →
43% → 46%. Headcount grew 5.41x over six years against 2.10x revenue growth
— a cumulative growth ratio of 2.58x.

**Insight to derive:** 2023, not 2024. By the time revenue growth looks
fine on the surface (2024's YoY revenue growth is actually the *best* year
in the series, 19.5%), the margin has already been bleeding out for a year.
The ratio moved first, exactly as the hypothesis predicted.

**Decision it enables:** if this were real, the restructuring conversation
should have started in 2022 — the year the YoY growth_ratio last dipped near
parity (2.16x, still bad) before climbing further — not in 2023 when margin
compression was already visible to anyone reading the P&L directly. The
tool's value is in catching it a year earlier than the income statement
would.

**Business interpretation (VP-of-Sales voice):** *We didn't miss our
numbers because sales slowed down — revenue never stopped growing. We
missed them because every rupee of growth started costing more rupees of
headcount to produce, and that shift was visible in the ratio two years
before it showed up in the margin line. If we're still measuring health by
"is revenue up," we're reading last year's problem.*

---

## B. Coverage Model Simulator

**Output:**

| Structure | Reps used | Cost-to-serve | Coverage gap | Specialization depth |
|---|---|---|---|---|
| Product Specialist | 37 | INR 35.6M | 0.0% | 100% |
| Geographic | 38 | INR 38.2M | 0.0% | 0% (by definition) |
| Segmented Hybrid | 39 | INR 39.9M | 4.6% | 28.9% |

**Insight to derive:** the hybrid did **not** win this round — it cost more
than Product Specialist at every tested split. Swept `HYBRID_SPECIALIST_SHARE`
across 0.30 / 0.40 / 0.50 / 0.60 to check whether the first run was just a
badly-tuned knob:

| Specialist share | Cost | Coverage gap | Depth |
|---|---|---|---|
| 30% | 39.4M | 0.5% | 27.2% |
| 40% | 39.0M | 0.5% | 27.2% |
| 50% | 40.4M | 0.0% | 27.5% |
| 60% | 39.9M | 0.0% | 27.5% |

Cost never drops below Product Specialist's 35.6M at any share, and depth
plateaus around 27–28% regardless — this is a real result, not an artifact
of one bad setting. The plan's own hypothesis (segmented hybrid beats both
pure models) doesn't hold on this synthetic account base, at least not
under this eligibility/capacity design.

**Decision it enables:** as measured, pure Product Specialist is the
frontrunner — cheapest, zero coverage gap, full specialization depth. The
honest caveat that remains: the `specialization_depth` metric only credits
specialist-tier matches, so generalists correctly serving simple accounts
(their actual job) score zero "depth" they never needed — a metric-design
choice, not a data artifact, and one a reviewer could reasonably push back
on.

**Business interpretation (VP-of-Sales voice):** *We tested hybrid across a
range of specialist-to-generalist mixes, not just one guess, and pure
product specialization still came out cheaper and fully covered every time.
That's a real result on this data, not a fluke of one setting — though I'd
want to be upfront in any write-up that our "depth" score is measuring
something specific (specialist-tier matches only), not a complete picture
of service quality.*

---

## C. Territory Optimizer

**Output:** Optimized cost-to-serve **INR 38.21M** using 38 of 119 available
reps, vs. naive equal-split cost-to-serve **INR 131.3M** using effectively
the full pool (all reps get at least one account under round-robin) — a
**70.9% cost improvement**, with identical 100% coverage in both cases.
Per-region detail in `src/territory_optimizer.py` output; region R03
(Maharashtra West, highest complexity concentration) needed the most
activated reps (8 of 29 available).

**Insight to derive:** the naive baseline isn't a strawman by accident — it's
the plan's own definition (spread accounts round-robin across every rep,
cost-blind). What it exposes is that an *unplanned* territory split, even
one that's demographically "fair," ends up needing 3x the headcount the
account base actually requires. The 70.9% isn't "optimization found a
clever trick" — it's "nobody had counted how many reps this book of
business actually needs."

**Decision it enables:** a concrete target headcount by region (38 total,
down from a pool of 119) that the org could staff toward, not just a
structural principle. Note this assumes today's fixed 119-rep pool is a
sunk allocation being re-optimized, not a hiring plan from zero.

**Business interpretation (VP-of-Sales voice):** *If we assigned today's
book of business by what it actually needs, region by region, we'd need 38
reps, not 119. That's not a claim that we should fire 81 people tomorrow —
it's a number worth having before the next headcount conversation, because
right now nobody can say with any precision how much slack is in the
current split.*

---

## D. New-Product GTM Scorer

**Output:** for the Dumb Waiter launch — buyer-persona distance **0.10**,
technical-complexity distance **0.31**, deal-cycle diff **0.57** (assumed
40-day cycle vs. a 92-day weighted average for the existing three lines).
Weighted score **0.291** → **recommendation: existing sales force** (below
the 0.5 pod threshold). Separately, breakeven for a 3-rep dedicated pod:
**2.4 months**, given its assumed faster ramp.

**Insight to derive:** the formula and the breakeven math point in
different directions, and that's the real finding, not a contradiction to
resolve away. The formula says the Dumb Waiter isn't different enough from
the existing motion (technically or by buyer) to *justify* a pod. The
breakeven math says *if* a pod were built anyway, it would pay for itself
in under 3 months — because the deal cycle is so much shorter that even
small revenue gets captured fast. Those are two different questions:
"is this different enough to need a pod" vs. "would a pod pay off if built."

**Decision it enables:** as scored, route the Dumb Waiter through the
existing sales force rather than standing up a pod — but flag deal-cycle
diff as the input doing the most work in this score (0.57, the largest of
the three, and currently the least grounded in the dataset since it's an
assumption table, not derived from actual sales-cycle records). If that
assumption is wrong, the recommendation could flip.

**Business interpretation (VP-of-Sales voice):** *On paper this product
isn't different enough from what our reps already sell to justify a
separate team — the buyer looks similar, the technical gap is modest. The
one number pulling against that is how much faster this deal cycle should
be, and that's an assumption, not a measurement. I'd want one quarter of
real Dumb Waiter deal data before I'd bet the org design on this.*

---

## Open items before Stage 3

1. **Module B's hybrid disadvantage** may be an artifact of the
   `HYBRID_SPECIALIST_SHARE` and depth-metric definitions, not a real
   finding about hybrid structures — worth a parameter sweep.
2. **Module D's deal-cycle assumption** is the least-grounded input in the
   whole build (no deal-cycle field in the synthetic data) — stated plainly
   in code and here rather than dressed up as derived.
