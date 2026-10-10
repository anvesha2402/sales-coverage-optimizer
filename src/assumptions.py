"""
assumptions.py — one place for every operating assumption in the project.

Earlier versions scattered unsourced constants across modules (e.g. "a rep
can carry 55 complexity points"). Every number the modules depend on now
lives here, with a base value and a low/high range, and is listed in plain
language in docs/assumptions.md. None of these come from real company data;
they are stated field-sales planning norms for an Indian B2B capital-goods
seller and should be replaced with CRM/HRIS data where it exists.

The workload model follows the standard "workload build-up" method for
sizing a sales force:
    hours an account needs per year = visits per year x (hours per visit
    + travel hours per visit) + yearly account admin hours
    reps needed = total hours needed / usable selling hours per rep
"""

import math

# ---------------------------------------------------------------------------
# Workload build-up: how much rep time each account needs
# ---------------------------------------------------------------------------
# Visits per year by technical complexity (1 = standard, 5 = multi-product,
# heavily customised). Most complex accounts get roughly a visit a month.
VISITS_PER_YEAR_BY_COMPLEXITY = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}

# Revenue tiering (account segmentation): the top 20% of accounts by revenue
# get 1.5x the visits; the bottom 40% get 0.6x (much of their contact can
# happen by phone / inside sales).
TIER_TOP_SHARE = 0.20
TIER_BOTTOM_SHARE = 0.40
TIER_VISIT_MULTIPLIER = {"Key": 1.5, "Core": 1.0, "Small": 0.6}

HOURS_PER_VISIT = 3.0             # meeting + preparation + follow-up
ACCOUNT_ADMIN_HOURS_PER_YEAR = 12  # quotes, collections, service coordination

# Rep capacity
WORKING_DAYS_PER_YEAR = 225
HOURS_PER_DAY = 8
FIELD_SELLING_SHARE = 0.55         # rest goes to internal meetings, reporting, training
SELLING_HOURS_PER_REP = WORKING_DAYS_PER_YEAR * HOURS_PER_DAY * FIELD_SELLING_SHARE  # 990 h
SELLING_HOURS_RANGE = (750, 1200)  # low / high for the what-if table
MAX_UTILISATION = 0.90             # keep 10% slack for new leads and absence
MIN_UTILISATION = 0.50             # balance band: a kept rep carries at least half a book

# ---------------------------------------------------------------------------
# Travel (the reason the real company went geographic in 2009)
# ---------------------------------------------------------------------------
SAME_REGION_TRAVEL_HOURS = 3.0     # round trip within an industrial belt
SAME_REGION_TRAVEL_COST_INR = 1_500
NEAR_REGION_KM = 300               # e.g. Delhi NCR <-> Haryana Belt: road day-trip
NEAR_REGION_TRAVEL_HOURS = 6.0
FAR_REGION_TRAVEL_HOURS = 11.0     # flight/overnight rail, effectively a day+ per visit
FARE_INR_PER_KM_ONE_WAY = 4.0      # blended rail/air fare
HOTEL_NIGHT_INR = 4_000
TRAVEL_COST_MULTIPLIER_RANGE = (0.5, 2.0)

REGION_CENTROIDS = {  # approximate centroids (lat, lon) for distance only
    "R01": (28.70, 77.10),   # Delhi NCR
    "R02": (29.06, 76.09),   # Haryana Belt
    "R03": (19.08, 72.88),   # Maharashtra West
    "R04": (22.26, 71.19),   # Gujarat Industrial Corridor
    "R05": (12.97, 77.59),   # Karnataka South
    "R06": (13.08, 80.27),   # Tamil Nadu Coastal
}

# ---------------------------------------------------------------------------
# Expertise risk (the Haryana lesson, priced in rupees)
# ---------------------------------------------------------------------------
# An account whose buying centre includes engineering, served by a rep
# without expertise in its product line, loses this share of its gross margin per year (lost deals,
# lost add-ons, escalations). The case documents the effect, not its size,
# so this is the single most judgement-heavy input in Module B; it is swept
# 0%-25% in the dashboard.
COMPLEX_ACCOUNT_THRESHOLD = 4
EXPERTISE_GAP_MARGIN_LOSS = 0.10
EXPERTISE_GAP_RANGE = (0.0, 0.25)

GROSS_MARGIN = 0.40                # 1 - cost of sales / revenue (see generator)

# ---------------------------------------------------------------------------
# Restructuring / transition costs
# ---------------------------------------------------------------------------
SEVERANCE_MONTHS_OF_PAY = 3
RETRAINING_COST_PER_REP_INR = 60_000          # role change (regional <-> specialist)
ACCOUNT_HANDOVER_REVENUE_LOSS = 0.05          # share of a moved account's margin lost in year 1
SALES_ATTRITION_PER_YEAR = 0.20               # voluntary exits, Indian field sales
SEVERANCE_COST_PER_REP_MONTHS_RANGE = (2, 6)
RELOCATION_COST_PER_REP_INR = 150_000       # moving a rep into a region short of capacity
TRANSFER_SLOTS_PER_REGION = 4


def haversine_km(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def travel_per_visit(rep_region, account_region, cost_multiplier=1.0):
    """(hours, INR) for one round-trip visit from a rep's home region."""
    if rep_region == account_region:
        return SAME_REGION_TRAVEL_HOURS, SAME_REGION_TRAVEL_COST_INR * cost_multiplier
    km = haversine_km(REGION_CENTROIDS[rep_region], REGION_CENTROIDS[account_region])
    if km < NEAR_REGION_KM:
        return NEAR_REGION_TRAVEL_HOURS, (2 * km * FARE_INR_PER_KM_ONE_WAY) * cost_multiplier
    return FAR_REGION_TRAVEL_HOURS, (2 * km * FARE_INR_PER_KM_ONE_WAY + HOTEL_NIGHT_INR) * cost_multiplier


def assign_tiers(accounts_df):
    """Key / Core / Small by revenue rank (segmentation step)."""
    ranks = accounts_df["annual_revenue_inr"].rank(pct=True, method="first")
    return ranks.apply(
        lambda p: "Key" if p > 1 - TIER_TOP_SHARE else ("Small" if p <= TIER_BOTTOM_SHARE else "Core")
    )


def visits_per_year(complexity, tier):
    return VISITS_PER_YEAR_BY_COMPLEXITY[int(complexity)] * TIER_VISIT_MULTIPLIER[tier]
