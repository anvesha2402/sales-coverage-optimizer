# Case reference

**Source:** *Lakshmi Projects: Sales Structure Dilemma* (W15219), Sandeep
Puri, Mehmet A. Begen, Akshay Nangia, Arjit Rawal and Mayank Rawat, Richard
Ivey School of Business Foundation, 2015.

Lakshmi Projects is a Delhi-based bulk-material-handling-equipment (BMHE)
manufacturer (conveyor and elevator systems) that grew from 5 employees in
1997 to ~100 by 2013, operating in 16 Indian states. Its sales force grew
from 2 reps (1997) → 8 (2002) → 28 (2008) → 40 (2013), while total field
force (sales + after-sales + quality) reached 58. Net revenue rose from
INR170M (2009) to INR363M (2013). In 2009 the company moved to a pure
geographic structure to cut travel burden; the case documents this causing a
coverage failure in Haryana (its highest-client region) where reps could not
answer product-specific technical questions across the full portfolio. By
2014 the company faced a new dilemma: how to sell a newly designed product
(the "dumb waiter," launching October 2014) — through the existing
generalist sales force or a dedicated pod.

**What's real (from the case):**
- The industry and company narrative, the 2009 geographic-restructuring
  failure in Haryana, and the dumb-waiter new-product dilemma (a smaller,
  simpler product aimed at builders and real estate rather than industrial
  plants).

**What the case does *not* show:** a sales force growing faster than
revenue. In the case, sales reps grew about 1.4x (28 → 40, 2008–2013)
while revenue grew about 2.1x (INR 170M → 363M, 2009–2013). Headcount grew
*slower* than revenue. The case's tension is structural (geography vs.
product expertise, and how to sell a new product), not cost sustainability.

**What's synthetic (built for this project):**
- All company names, account names, individual rep records, regional and
  product-line splits, the current account-to-rep assignment, and the full
  6-year `yearly_financials` series.
- The headcount trajectory in `yearly_financials` (16 → 56 sales reps,
  3.5x, against 2.1x revenue) is a **stress scenario invented to test the
  Diagnostic Engine**. It is not drawn from, or scaled from, the case — the
  case's real pattern runs the other way. Module A is therefore also tested
  against 200 generated histories, half of them healthy, so its warning is
  judged on how often it is right and wrong, not on catching a pattern that
  was planted (see `docs/business_insights.md`, Module A).
- Every operating assumption (visit frequency, travel time and cost, rep
  selling hours, win rates, severance) is listed with its range in
  `docs/assumptions.md`.

**What I'd change with a real CRM/HRIS export:** actual account-level
revenue and account-rep assignment history (to validate the Territory
Optimizer's as-is baseline against what was really done), visit logs to
replace the assumed visit frequencies, real compensation bands by region,
real Dumb Waiter lead and win-rate data, and a longer financial history to
test the Diagnostic Engine out of sample.
