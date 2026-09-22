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
  failure, the dumb-waiter new-product dilemma, and the general shape of the
  headcount/revenue mismatch.

**What's synthetic (built for this project):**
- All specific company names, account names, individual rep records, exact
  regional and product-line splits, and the full 6-year `yearly_financials`
  series. No real company export exists for this problem, so a dataset was
  generated to reproduce the same *class* of pattern the case describes —
  headcount growing materially faster than revenue (the build plan targets
  a ~5.4x headcount / ~2.1x revenue multiple over the trajectory, echoing
  the case's actual 1.4x sales-rep growth against ~2.1x revenue growth
  2009→2013, scaled up so Module A has an unambiguous signal to catch) —
  disclosed openly here rather than presented as real company data.

**What I'd change with a real CRM/HRIS export:** actual account-level
revenue and account-rep assignment history (to validate the Territory
Optimizer's baseline against what was actually done), real compensation
bands by region (currently modeled, not sourced), and a longer financial
history to test the Diagnostic Engine's threshold-year claim out of sample.
