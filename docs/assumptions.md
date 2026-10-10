# Assumptions register

Every number the models depend on that is **not** derived from the dataset.
None comes from real company data; each is a stated planning norm for an
Indian B2B capital-goods seller, with a range that the analysis is tested
across. In code, all of these live in `src/assumptions.py` (Modules B, C and
economics) or `GTM_ASSUMPTIONS` in `src/gtm_scorer.py` (Module D).

The column "Tested how" says where the range is actually run, so a reader
can see which conclusions depend on which guesses.

## Workload: how much rep time an account needs (Modules B, C)

Method: the standard workload build-up for sizing a sales force. Hours an
account needs per year = visits × (hours per visit + travel hours per visit)
+ admin hours. Reps needed = total hours ÷ usable selling hours per rep.

| Assumption | Base | Range | Rationale | Tested how |
|---|---|---|---|---|
| Visits per year by complexity 1→5 | 4, 6, 8, 10, 12 | — | Roughly quarterly for standard accounts, monthly for the most complex | Fixed |
| Visit multiplier by revenue tier (Key top 20% / Core / Small bottom 40%) | 1.5 / 1.0 / 0.6 | — | Account segmentation: big accounts get more contact, small ones partly by phone | Fixed |
| Hours per visit (meeting, prep, follow-up) | 3 | — | | Fixed |
| Admin hours per account per year | 12 | — | Quotes, collections, service coordination | Fixed |
| Selling hours per rep per year | 990 (225 days × 8 h × 55%) | 750–1,200 | 45% of time goes to internal work, reporting, training | Capacity what-if (Module C) re-solves the optimiser at 750 / 850 / 990 / 1,100 / 1,200 |
| Maximum utilisation | 90% | — | 10% slack for new leads and absence | Fixed |
| Minimum utilisation for a kept rep | 50% | — | Balance band: no rep is kept with a token book | Fixed |

## Travel (Modules B, C)

| Assumption | Base | Range | Rationale | Tested how |
|---|---|---|---|---|
| Same-region visit | 3 h, ₹1,500 | × 0.5–2.0 | Round trip within an industrial belt | Module B what-if grid |
| Nearby region (< 300 km, e.g. Delhi ↔ Haryana) | 6 h, ₹4/km each way | × 0.5–2.0 | Road day-trip | Module B what-if grid |
| Far region | 11 h, ₹4/km each way + ₹4,000 hotel | × 0.5–2.0 | Flight or overnight train; a day or more per visit | Module B what-if grid |

## Expertise risk (Modules B, C)

| Assumption | Base | Range | Rationale | Tested how |
|---|---|---|---|---|
| Margin lost per year on an account whose buying centre includes engineering, served by a rep without expertise in that product | 10% | 0–100% | The case documents the Haryana effect, not its size. Engineering is the role that asks technical questions. **This is the most judgement-heavy input in Module B.** | Module B what-if grid; Module C re-run at 25% |
| Gross margin | 40% | — | Matches the synthetic P&L (cost of sales 58–60% of revenue) | Fixed |

## Transition (economics)

| Assumption | Base | Range | Rationale | Tested how |
|---|---|---|---|---|
| Severance per released rep | 3 months' pay | 2–6 months | Notice plus ex-gratia, typical for Indian field sales staff | Low / base / high transition cases |
| Margin lost on an account that changes owner | 5% of its yearly margin, year 1 | 2–10% | Relationship handover cost | Low / base / high transition cases; also the optimiser's continuity charge |
| Relocation of a rep into a short region | ₹150,000 one-time | — | | Fixed |
| Retraining for a role change | ₹60,000 per rep | — | | Fixed |
| Voluntary attrition, field sales | 20% a year | — | Used for the hiring-freeze path | Fixed |

## New product (Module D)

Values are written low / base / high, where "low" is the pessimistic case
for that option.

| Assumption | Low / base / high | Rationale |
|---|---|---|
| Qualified Dumb Waiter leads a year | Calibrated: pilot accounts (33) ÷ existing base win rate (15%) ≈ 220 | Ties lead volume to the one observed fact, the pilot year |
| Existing force win rate | 10% / 15% / 20% | Generalists selling an unfamiliar product to an unfamiliar buyer |
| Rep hours per lead (existing force) | 10 / 8 / 6 | Time taken away from the core book, costed at salary per selling hour |
| Pod: reps, win rate | 3 reps; 18% / 25% / 32% | Focused, trained reps |
| Pod: lead uplift from focused prospecting | 1.0× / 1.2× / 1.4× | |
| Pod: ramp to full productivity | 4 / 3 / 2 months | |
| Pod: one-time cost (training, launch events, listings) | ₹1.6M / ₹1.2M / ₹0.9M | Reps are redeployed from those Module C frees, so 3 months' severance each is avoided |
| Channel partners: accounts a year | 24 / 48 / 72 | e.g. 8 lift dealers or installers × ~6 installs each |
| Channel partners: commission | 12% / 10% / 8% of revenue | |
| Channel partners: ramp | 9 / 6 / 4 months | |
| Channel partners: one-time (onboarding, demo units) | ₹1.0M / ₹0.8M / ₹0.6M | Plus one redeployed rep as partner manager |
| Service contract after year 1 | 8% of ticket a year | |

| Dealer credit days (trade term) | 60 / 45 / 30 days, financed at 12% a year | Cost of letting dealers pay later |
| Architect-specification programme (pull) | ₹0.8M / ₹0.6M / ₹0.4M a year; +0% / +15% / +25% partner accounts from month 6 / 4 / 3 | CPD sessions and specification listings |
| Minimum installs a year to keep a dealer engaged | 6 | Sets how many dealers the market can support |

Module D also reports the pod win rate at which the pod would overtake the
best alternative, so the recommendation can be checked against any view of
that one number.

### Service output demands (Module D)

Weights are what a Dumb Waiter buyer needs from a channel; scores (1–5)
are how well each route delivers. All are judgement calls. The model
reports how many single-point changes would flip the leader.

| Need | Weight | Existing force | Pod | Dealers |
|---|---|---|---|---|
| Local presence near the site | 20% | 3 | 2 | 5 |
| Fast delivery and installation | 25% | 2 | 3 | 4 |
| After-sales service on call | 25% | 3 | 3 | 4 |
| Single-unit orders, little paperwork | 10% | 2 | 3 | 5 |
| Technical specification support | 20% | 3 | 5 | 3 |

### Market sizing (Module D)

Built bottom-up in `data/market_sizing.csv`, which has a low / base / high
value and a source or "Assumption" label on every row.

Sourced figures:
- 2025 luxury housing launches: NCR above ₹2.5 Cr is ~55% of 61,775 units, and 21% across the top 7 cities (ANAROCK).
- 176 branded hotels opened in India in 2025 (HVS ANAROCK).
- Private hospitals adding 30,000+ beds over 4–5 years (ICRA).
- Dumb waiter prices on IndiaMART: ₹0.6–8.5 lakh, median ~₹2.5 lakh.

Everything else is an assumption: project sizes, adoption shares, units per site, the retrofit multiple, the reachable share, and multi-floor restaurant openings (no usable published figure was found).

Multiplying every pessimistic input together gives a reachable market below
what the existing force already sold in the pilot year (33). So the
reachable market is floored at observed pilot sales.

### Price check (EVC, Module D)

| Assumption | Base | Range |
|---|---|---|
| Helper wage saved, metro | ₹18,000 a month | — |
| Helper time saved per unit | 0.5 FTE | 0.3–0.75 |
| Life, discount rate | 10 years, 12% | — |
| Value of brand and service reliability vs. a local fabricator | ₹20,000 | — |
| Price scenario | +20% price, 10% fewer wins | Live slider −10% to +40% |

## Synthetic data choices (generator)

| Choice | Value | Why |
|---|---|---|
| Sales headcount 2019 → 2024 | 16 → 56 (3.5×) vs. revenue 2.1× | A stress scenario to test Module A. **The real case runs the other way** (reps ~1.4× vs. revenue ~2.1×) — see `case_reference.md` |
| P&L shape | Cost of sales 58→60%, other opex 13%, depreciation + interest 4%, tax 25% | Gives a starting net margin of ~12%, plausible for an equipment maker |
| Dumb Waiter buyers | Builders 55%, hotels/restaurants 30%, hospitals 15%; city-heavy regions; tickets ~⅓ of industrial; ~45-day cycle | As the case describes the product |
| Dumb Waiter accounts | ~5% of the book, all acquired in the launch year | Pilot customers won by the existing force |
| Current owners | Same-region rep, product-matched 70% of the time when one exists | An unplanned, historically grown assignment |
| Active accounts by year | Grows a little slower than revenue (exponent 0.9), 6% lost a year, ending at 650 | Feeds the revenue-per-rep decomposition |
| Buying centre | Industrial: plant head + procurement; engineering always at complexity ≥ 4 and 30% of the time at 3; finance on large orders. Dumb Waiter: project manager + architect (builders), owner/GM + F&B head (hotels), facility manager + procurement (hospitals) | As the case describes the buyers |
