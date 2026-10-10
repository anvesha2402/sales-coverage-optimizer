"""
run_pipeline.py — runs the five modules as one chain and saves every result.

    A  Diagnostic Engine      -> is cost outrunning growth? (+ 200-history backtest)
    B  Coverage Simulator     -> which structure? (+ 100-dataset robustness, what-if grid)
    C  Territory Optimizer    -> optimises the structure B recommends
                                 (+ as-is / greedy baselines, capacity what-if)
    D  GTM Scorer             -> how to sell the new product; one rep freed by C
                                 is redeployed to run it
    $  Economics              -> before/after metrics, transition cost, payback,
                                 region-by-region changes for the rollout plan

Outputs land in data/results/ (committed, so the dashboard loads instantly).
Takes ~15-20 minutes, mostly the optimiser's capacity what-if.

    python run_pipeline.py            # full run
    python run_pipeline.py --quick    # skips robustness + capacity what-if
"""

import argparse
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from src import assumptions as A  # noqa: E402
from src import coverage_simulator as B  # noqa: E402
from src import diagnostics as DA  # noqa: E402
from src import economics as E  # noqa: E402
from src import gtm_scorer as D  # noqa: E402
from src import territory_optimizer as C  # noqa: E402

GEN = os.path.join(ROOT, "data", "generated")
OUT = os.path.join(ROOT, "data", "results")


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, float) and np.isnan(o):
        return None
    return o


def main(quick=False):
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    if not os.path.exists(os.path.join(GEN, "accounts.csv")):
        subprocess.run([sys.executable, os.path.join(ROOT, "data", "generate_synthetic_company.py")], check=True)
    acc_p, rep_p = os.path.join(GEN, "accounts.csv"), os.path.join(GEN, "reps.csv")
    accounts, reps = pd.read_csv(acc_p), pd.read_csv(rep_p)
    fin = pd.read_csv(os.path.join(GEN, "yearly_financials.csv"))
    summary = {}

    # ---- A ---------------------------------------------------------------
    print("A  diagnostics ...")
    a = DA.diagnose_from_df(fin)
    a["yoy_table"].to_csv(os.path.join(OUT, "a_yoy.csv"), index=False)
    bt_runs, bt = DA.backtest()
    bt_runs.to_csv(os.path.join(OUT, "a_backtest_runs.csv"), index=False)
    tradeoff = []
    for ratio in (1.10, 1.20, 1.30, 1.40):
        DA.WARNING_RATIO = ratio
        _, s = DA.backtest()
        tradeoff.append({"warning_ratio": ratio, **{k: s[k] for k in
                         ("detection_rate", "false_alarm_rate", "median_lead_years")}})
    DA.WARNING_RATIO = 1.20
    pd.DataFrame(tradeoff).to_csv(os.path.join(OUT, "a_threshold_tradeoff.csv"), index=False)
    summary["A"] = {k: v for k, v in a.items() if k != "yoy_table"}
    summary["A"]["backtest"] = bt

    # ---- B ---------------------------------------------------------------
    print("B  coverage structures ...")
    b = B.run_all(acc_p, rep_p)
    b.to_csv(os.path.join(OUT, "b_structures.csv"), index=False)
    structure = B.recommend(b)
    B.spectrum(accounts, reps).to_csv(os.path.join(OUT, "b_spectrum.csv"), index=False)
    grid = B.what_if_grid(accounts, reps, expertise_losses=(0.0, 0.05, 0.10, 0.25, 0.50, 0.75, 1.0))
    grid.to_csv(os.path.join(OUT, "b_what_if_grid.csv"), index=False)
    summary["B"] = {"recommended_structure": structure, "structures": b.to_dict("records")}
    if not quick:
        print("B  robustness (100 datasets) ...")
        runs, rob = B.robustness(100)
        runs.to_csv(os.path.join(OUT, "b_robustness_runs.csv"), index=False)
        rob.to_csv(os.path.join(OUT, "b_robustness_summary.csv"))
        summary["B"]["robustness"] = rob.reset_index().to_dict("records")

    # ---- C ---------------------------------------------------------------
    print(f"C  optimising '{structure}' ...")
    c = C.compare(acc_p, rep_p, structure)
    c["table"].to_csv(os.path.join(OUT, "c_compare.csv"), index=False)
    c["assignment"].to_csv(os.path.join(OUT, "c_assignment.csv"), index=False)
    hi_risk, _, _ = C.optimise(accounts, reps, structure, expertise_loss=0.25)
    summary["C"] = {"structure": structure, "table": c["table"].to_dict("records"),
                    "optimiser_at_25pct_expertise_loss": hi_risk}
    if not quick:
        print("C  capacity what-if ...")
        cap = C.capacity_what_if(acc_p, rep_p, structure)
        cap.to_csv(os.path.join(OUT, "c_capacity_what_if.csv"), index=False)
        summary["C"]["capacity_what_if"] = cap.to_dict("records")

    # ---- D ---------------------------------------------------------------
    print("D  new-product GTM ...")
    d = D.evaluate(accounts, avg_rep_cost_inr=reps["annual_cost_inr"].mean())
    d["options"].to_csv(os.path.join(OUT, "d_options.csv"), index=False)
    for case, cf in d["flows"].items():
        cf.to_csv(os.path.join(OUT, f"d_flows_{case}.csv"), index=False)
    summary["D"] = {k: d[k] for k in ("inputs", "fit", "flip_points", "recommendation", "best_by_case",
                                      "pod_break_even_win_rate")}
    redeployed = {"Dedicated pod": D.GTM_ASSUMPTIONS["pod_reps"],
                  "Channel partners": D.GTM_ASSUMPTIONS["partner_manager_reps"]}.get(d["recommendation"], 0)

    # ---- Economics -------------------------------------------------------
    print("$  economics ...")
    t = c["table"].set_index("method")
    as_is, opt = t.loc["As-is (today)"], t.loc["Optimiser"]
    ba, annual_saving = E.before_after(as_is, opt, fin, len(accounts))
    ba.T.to_csv(os.path.join(OUT, "e_before_after.csv"))
    trans_rows, pay_rows, curves = [], [], {}
    for case in ("low", "base", "high"):
        tc = E.transition_costs(opt, accounts, c["assignment"], reps, redeployed, case)
        trans_rows.append({"case": case, **tc["items_inr_m"], "total_inr_m": tc["total_inr_m"],
                           "reps_released": tc["reps_released"], "accounts_moved": tc["accounts_moved"]})
        for path in ("release now", "attrition"):
            p = E.payback(annual_saving, tc, tc["reps_released"], len(reps), path)
            curves[f"{case}|{path}"] = p.pop("cumulative")
            pay_rows.append({"case": case, **p})
    pd.DataFrame(trans_rows).to_csv(os.path.join(OUT, "e_transition_costs.csv"), index=False)
    pd.DataFrame(pay_rows).to_csv(os.path.join(OUT, "e_payback.csv"), index=False)
    pd.DataFrame({"month": np.arange(1, E.HORIZON_MONTHS + 1), **curves}).to_csv(
        os.path.join(OUT, "e_payback_curves.csv"), index=False)
    rc = E.region_changes(c["assignment"], reps, accounts)
    rc.to_csv(os.path.join(OUT, "e_region_changes.csv"))
    summary["E"] = {"annual_saving_inr_m": annual_saving, "before_after": ba.T.to_dict(),
                    "transition": trans_rows, "payback": pay_rows,
                    "reps_redeployed_to_new_product": redeployed, "region_changes": rc.to_dict("index")}

    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(_jsonable(summary), f, indent=2, default=str)
    print(f"done in {time.time() - t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    main(ap.parse_args().quick)
