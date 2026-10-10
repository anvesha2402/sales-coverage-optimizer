"""
dashboard/app.py — Module E: Scenario Dashboard

Business question: Does the recommendation hold across plausible futures,
and which assumptions would change it?

Reads the chained results written by run_pipeline.py (data/results/) and
re-runs the fast parts live:
  * Module A re-computes from the two growth sliders
  * Module B re-runs all three structures from the travel-cost and
    expertise-loss sliders (the two most judgement-heavy inputs)
  * Module D re-runs the fit score and the 24-month option economics
The optimiser (Module C), the 100-dataset robustness test and the
200-history backtest take minutes, so they are shown from the pipeline run.

Run locally:
    python run_pipeline.py        # once, ~15-20 min (results are committed)
    streamlit run dashboard/app.py
"""

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from src import coverage_simulator as B  # noqa: E402
from src import diagnostics as DA  # noqa: E402
from src import gtm_scorer as D  # noqa: E402

# Palette: fixed categorical order, status colours reserved for state only
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#8a5cd1"
STATUS_GOOD, STATUS_WARNING, STATUS_CRITICAL = "#0ca30c", "#fab219", "#d03b3b"
INK2, GRID = "#52514e", "#e1e0d9"
GEN = os.path.join(ROOT, "data", "generated")
RES = os.path.join(ROOT, "data", "results")

st.set_page_config(page_title="Sales Coverage & GTM Structure Optimizer", layout="wide")


def style(fig, ytitle="", xtitle="", height=340):
    fig.update_layout(plot_bgcolor="white", height=height, margin=dict(t=10, b=10, l=10, r=10),
                      yaxis_title=ytitle, xaxis_title=xtitle, legend=dict(orientation="h", y=-0.25),
                      hovermode="x unified")
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
if not os.path.exists(os.path.join(GEN, "accounts.csv")):
    subprocess.run([sys.executable, os.path.join(ROOT, "data", "generate_synthetic_company.py")], check=True)
if not os.path.exists(os.path.join(RES, "summary.json")):
    st.error("Results not found. Run `python run_pipeline.py` once (about 15–20 minutes), then reload.")
    st.stop()


@st.cache_data
def load():
    r = lambda f: pd.read_csv(os.path.join(RES, f))  # noqa: E731
    with open(os.path.join(RES, "summary.json")) as f:
        summary = json.load(f)
    return {
        "accounts": pd.read_csv(os.path.join(GEN, "accounts.csv")),
        "reps": pd.read_csv(os.path.join(GEN, "reps.csv")),
        "summary": summary,
        "tradeoff": r("a_threshold_tradeoff.csv"),
        "robust": r("b_robustness_summary.csv"),
        "grid": r("b_what_if_grid.csv"),
        "spectrum": r("b_spectrum.csv"),
        "compare": r("c_compare.csv"),
        "capacity": r("c_capacity_what_if.csv"),
        "regions": r("e_region_changes.csv"),
        "before_after": r("e_before_after.csv"),
        "transition": r("e_transition_costs.csv"),
        "payback": r("e_payback.csv"),
        "curves": r("e_payback_curves.csv"),
        "decomp": r("a_decomposition.csv"),
        "lev_whatif": r("a_leverage_what_if.csv"),
        "bottleneck": r("c_bottleneck.csv"),
        "sod": r("d_service_outputs.csv"),
    }


data = load()
S = data["summary"]
accounts, reps = data["accounts"], data["reps"]
avg_rep_cost = reps["annual_cost_inr"].mean()


@st.cache_data
def live_structures(travel_mult, expertise_loss):
    acc = B.prepare_accounts(accounts)
    return pd.DataFrame([B.simulate(s, accounts, reps, travel_multiplier=travel_mult,
                                    expertise_loss=expertise_loss, acc=acc) for s in B.STRUCTURES])


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("What-if controls")
st.sidebar.caption("Module A — growth")
rev_mult = st.sidebar.slider("Revenue growth over 6 years (×)", 1.3, 3.5, 2.1, 0.1)
hc_mult = st.sidebar.slider("Sales headcount growth over 6 years (×)", 1.0, 6.0, 3.5, 0.1)
st.sidebar.caption("Module B — the two judgement-heavy inputs")
travel_mult = st.sidebar.select_slider("Travel cost (× base)", [0.5, 0.75, 1.0, 1.5, 2.0], 1.0)
expertise_loss = st.sidebar.slider("Margin lost when an engineering-led account gets a non-expert rep",
                                   0.0, 1.0, 0.10, 0.05, format="%.2f")
st.sidebar.caption("Module D — new product")
gi = S["D"]["inputs"]
buyer_d = st.sidebar.slider("Buyer distance", 0.0, 1.0, round(gi["buyer_distance"], 2), 0.01)
cx_d = st.sidebar.slider("Technical-complexity distance", 0.0, 1.0, round(gi["complexity_distance"], 2), 0.01)
cyc_d = st.sidebar.slider("Deal-cycle distance", 0.0, 1.0, round(gi["deal_cycle_distance"], 2), 0.01)
pod_wr = st.sidebar.slider("Pod win rate", 0.10, 0.50, 0.25, 0.01)
partner_n = st.sidebar.slider("Channel-partner accounts a year", 12, 96, 48, 6)
price_chg = st.sidebar.slider("Dumb Waiter price change (%)", -10, 40, 0, 5,
                              help="Competitor median is about ₹2.5 lakh vs ₹1.66 lakh today. Assumes 10% fewer wins "
                                   "for any price rise.")

# ---------------------------------------------------------------------------
# Header + KPI row
# ---------------------------------------------------------------------------
st.title("Sales Coverage & GTM Structure Optimizer")
st.caption("Generalized from *Lakshmi Projects: Sales Structure Dilemma* (Ivey W15219). All data synthetic; "
           "the headcount trend is a stress scenario, not the case's real pattern — see docs/case_reference.md. "
           "Every assumption and its range: docs/assumptions.md.")

A_ = S["A"]
opt = next(r for r in S["C"]["table"] if r["method"] == "Optimiser")
base_pay = next(p for p in S["E"]["payback"] if p["case"] == "base" and p["path"] == "release now")
k = st.columns(5)
k[0].metric("Early warning → margin breach", f"{A_['warning_year']} → {A_['breach_year']}",
            f"{A_['lead_years']} years' notice", delta_color="off")
k[1].metric("Recommended structure", S["B"]["recommended_structure"])
k[2].metric("Sales reps: today → needed", f"56 → {opt['reps_used']}",
            f"{int(opt['transfers_in'])} relocated into Haryana", delta_color="off")
k[3].metric("Cost to serve saved a year", f"₹{S['E']['annual_saving_inr_m']:.1f}M",
            f"payback month {base_pay['payback_month']}", delta_color="off")
route = S["D"]["recommendation"]
k[4].metric("New product route", route.replace("Channel partners", "Partners").replace("Existing sales force", "Existing reps"),
            "lift dealers / installers" if route == "Channel partners" else None, delta_color="off")
st.caption("How the pieces connect: A flags the problem → B picks the structure → C optimises that structure and "
           "frees reps → D redeploys one of them to run the new product's route → the economics section prices "
           "the change and its payback.")
st.divider()

# ---------------------------------------------------------------------------
# Module A
# ---------------------------------------------------------------------------
st.subheader("A · Is sales cost outrunning growth?")
yf = DA.scenario_yearly_financials(rev_mult, hc_mult, final_avg_rep_cost_inr_m=avg_rep_cost / 1e6)
diag = DA.diagnose_from_df(yf)
yoy = diag["yoy_table"]
la, ra = st.columns([1, 1])
with la:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=yoy["year"], y=yoy["net_margin"], mode="lines+markers", name="Net margin",
                             line=dict(color=C1, width=2), marker=dict(size=8)))
    fig.add_hline(y=diag["breach_line"], line_dash="dash", line_color=STATUS_CRITICAL,
                  annotation_text="Breach line (half of base-year margin)")
    if diag["warning_year"]:
        fig.add_vline(x=diag["warning_year"], line_dash="dot", line_color=INK2, annotation_text="Early warning")
    style(fig, "Net margin").update_yaxes(tickformat=".0%")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")
with ra:
    st.markdown(f"**This scenario:** warning **{diag['warning_year'] or 'none'}**, margin breach "
                f"**{diag['breach_year'] or 'none'}**, sustainability score **{diag['sustainability_score']}/100**. "
                f"Had headcount grown in step with revenue, the team would be **{diag['in_step_headcount']:.0f}** reps.")
    bt = A_["backtest"]
    st.markdown(f"**Is the warning any good?** On 200 generated histories it was not tuned on, it caught "
                f"**{bt['detection_rate']:.0%}** of margin breaches, a median **{bt['median_lead_years']:.0f} years** "
                f"early, with a **{bt['false_alarm_rate']:.0%}** false-alarm rate. Watching revenue growth instead "
                f"caught {bt['revenue_watch_detection_rate']:.0%}.")
    t = data["tradeoff"].rename(columns={"warning_ratio": "Warn when headcount runs ahead by",
                                         "detection_rate": "Breaches caught", "false_alarm_rate": "False alarms",
                                         "median_lead_years": "Median years' notice"})
    t["Warn when headcount runs ahead by"] = (t["Warn when headcount runs ahead by"] - 1).map("{:.0%}".format)
    st.dataframe(t.style.format({"Breaches caught": "{:.0%}", "False alarms": "{:.0%}"}),
                 hide_index=True, width="stretch")
st.markdown("**Why did revenue per rep fall, and why did margin fall so fast?**")
la2, ra2 = st.columns(2)
with la2:
    dc = data["decomp"]
    fig = go.Figure()
    for col, name, c in [("accounts_per_rep", "Accounts per rep", C1),
                         ("revenue_per_account_inr_k", "Revenue per account", C2),
                         ("revenue_per_rep_inr_m", "Revenue per rep", C3)]:
        fig.add_trace(go.Scatter(x=dc["year"], y=dc[col] / dc[col].iloc[0] * 100, mode="lines+markers", name=name,
                                 line=dict(color=c, width=2), marker=dict(size=8)))
    style(fig, "Index, 2019 = 100").update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")
    ds = S["A"]["decomposition"]
    st.caption(f"Revenue per rep fell {abs(ds['revenue_per_rep_change']):.0%}: each rep covers "
               f"{abs(ds['accounts_per_rep_change']):.0%} fewer accounts, while revenue per account rose "
               f"{ds['revenue_per_account_change']:.0%}. The customers didn't weaken; coverage thinned. "
               "Win rate and repeat-order terms need deal-level data the dataset doesn't have.")
with ra2:
    fig = go.Figure(go.Scatter(x=yoy["year"], y=yoy["operating_leverage"], mode="lines+markers", name="Operating leverage",
                               line=dict(color=C1, width=2), marker=dict(size=8)))
    style(fig, "% profit change per 1% revenue change").update_xaxes(dtick=1)
    st.plotly_chart(fig, width="stretch")
    lw = data["lev_whatif"]
    last = yoy.dropna(subset=["operating_leverage"]).iloc[-1]
    st.caption(f"The whole sales cost scales with headcount, not revenue, so it acts as a fixed cost. In "
               f"{int(last['year'])} a 10% revenue dip would cut operating profit by "
               f"{abs(last['profit_change_if_revenue_falls_10pct']):.0%} (this scenario). Paying 20% / 40% of rep pay as "
               f"commission would bring leverage down from {lw['operating_leverage'].iloc[0]:.1f} to "
               f"{lw['operating_leverage'].iloc[1]:.1f} / {lw['operating_leverage'].iloc[2]:.1f} (dataset).")
st.divider()

# ---------------------------------------------------------------------------
# Module B
# ---------------------------------------------------------------------------
st.subheader("B · Which structure covers the book at the lowest total cost?")
bdf = live_structures(travel_mult, expertise_loss)
lb, rb = st.columns([3, 2])
with lb:
    fig = go.Figure()
    for col, name, c in [("payroll_inr_m", "Payroll", C1), ("travel_inr_m", "Travel", C2),
                         ("expertise_risk_inr_m", "Expertise risk", C3),
                         ("uncovered_margin_inr_m", "Margin on uncovered accounts", C4)]:
        fig.add_trace(go.Bar(x=bdf["structure"], y=bdf[col], name=name, marker_color=c,
                             marker_line=dict(color="white", width=2)))
    fig.update_layout(barmode="stack", hovermode="closest")
    st.plotly_chart(style(fig, "₹M a year"), width="stretch")
with rb:
    best = B.recommend(bdf)
    st.markdown(f"**At these settings: {best}.** Total cost (₹M): " +
                " · ".join(f"{s} {c:.1f}" for s, c in zip(bdf["structure"], bdf["total_cost_inr_m"])))
    st.caption("Within 1% counts as a tie; ties go to the simpler structure to run. The Hybrid's specialist "
               "overlay rarely earns its keep: regional reps already include product specialists, so matching "
               "expertise inside each region gets most of the benefit without the travel.")
rob = data["robust"]
st.markdown("**Across 100 different generated account bases (base settings):**")
st.dataframe(pd.DataFrame({
        "Structure": rob["structure"],
    "Avg total cost ₹M": rob["cost_mean"].round(1),
    "10th–90th percentile ₹M": [f"{a:.1f}–{b:.1f}" for a, b in zip(rob["cost_p10"], rob["cost_p90"])],
    "Cheapest outright": rob["outright_win_share"].map("{:.0%}".format),
    "Tied for cheapest (within 1%)": rob["tied_best_share"].map("{:.0%}".format),
    "Avg reps needed": rob["reps_mean"].round(1),
    "Engineering-led accounts with expert": rob["expert_share_mean"].map("{:.0%}".format),
}), hide_index=True, width="stretch")
with st.expander("Which structure wins as travel cost and expertise loss move"):
    g = data["grid"].pivot(index="expertise_loss", columns="travel_multiplier", values="winner")
    g.index = [f"{v:.0%} margin lost" for v in g.index]
    g.columns = [f"travel ×{c}" for c in g.columns]
    st.dataframe(g, width="stretch")
st.divider()

# ---------------------------------------------------------------------------
# Module C
# ---------------------------------------------------------------------------
st.subheader(f"C · Optimised territories ({S['C']['structure']} structure)")
cmp_ = data["compare"]
show = pd.DataFrame({
    "Method": cmp_["method"], "Reps": cmp_["reps_used"],
    "Total cost ₹M": cmp_["total_cost_inr_m"].round(1),
    "Payroll ₹M": cmp_["payroll_inr_m"].round(1),
    "Accounts changing owner": cmp_["accounts_moved"],
    "Rep load range": [f"{a:.0%}–{b:.0%}" for a, b in zip(cmp_["utilisation_min"], cmp_["utilisation_max"])],
    "Engineering-led accounts with expert": cmp_["expert_coverage"].map("{:.0%}".format),
})
st.dataframe(show, hide_index=True, width="stretch")
st.caption("As-is = today's owners, every rep paid. Greedy = the simple fill-the-cheapest-rep-first rule. "
           "The optimiser's edge over greedy is modest on cost; its real gain is moving far fewer accounts. "
           "Today one Haryana rep carries over twice their selling hours while other regions have spare reps.")
lc, rc = st.columns(2)
with lc:
    cap = data["capacity"]
    fig = go.Figure(go.Scatter(x=cap["selling_hours_per_rep"], y=cap["reps_needed"], mode="lines+markers",
                               line=dict(color=C1, width=2), marker=dict(size=8), name="Reps needed"))
    fig.add_hline(y=56, line_dash="dash", line_color=INK2, annotation_text="Reps today: 56")
    st.markdown("**Headcount depends on one assumption above all: selling hours per rep**")
    st.plotly_chart(style(fig, "Reps needed", "Selling hours per rep per year"), width="stretch")
with rc:
    reg = data["regions"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=reg["region"], y=reg["reps_today"], name="Today", marker_color=C1,
                         marker_line=dict(color="white", width=2)))
    fig.add_trace(go.Bar(x=reg["region"], y=reg["reps_needed"], name="Needed", marker_color=C2,
                         marker_line=dict(color="white", width=2)))
    fig.update_layout(barmode="group", hovermode="closest")
    st.markdown("**Reps by region: today vs. needed**")
    st.plotly_chart(style(fig, "Reps"), width="stretch")
bn = data["bottleneck"]
lb2, rb2 = st.columns([3, 2])
with lb2:
    fig = go.Figure()
    for when, c in [("Today", C1), ("After redesign", C2)]:
        sub = bn[bn["when"] == when]
        fig.add_trace(go.Bar(x=sub["region_id"].map(dict(zip(reg["region_id"], reg["region"]))),
                             y=sub["value_per_extra_hour_inr"].clip(lower=0), name=when, marker_color=c,
                             marker_line=dict(color="white", width=2)))
    fig.update_layout(barmode="group", hovermode="closest")
    st.markdown("**Where capacity is the constraint: value of one more selling hour (₹)**")
    st.plotly_chart(style(fig, "₹ per extra selling hour"), width="stretch")
with rb2:
    t = bn[(bn["when"] == "Today") & (bn["hours_short"] > 0)]
    if len(t):
        row = t.iloc[0]
        name = dict(zip(reg["region_id"], reg["region"]))[row["region_id"]]
        st.markdown(f"**Theory of Constraints view.** Today only **{name}** is constrained: "
                    f"{row['hours_short']:,.0f} hours short, and an extra hour there is worth "
                    f"₹{row['value_per_extra_hour_inr']:,.0f}. Every other region has slack (value ₹0). "
                    "The redesign relocates reps into it, which relieves the constraint.")
        st.caption(f"Caveat: one more rep there recovers about ₹{row['value_of_one_more_rep_inr'] / 1e5:.1f} lakh "
                   "of margin a year, less than a rep costs. Relocating is justified by the policy of covering "
                   "every account; the alternative is serving the region's smallest accounts by phone.")
st.divider()

# ---------------------------------------------------------------------------
# Module D
# ---------------------------------------------------------------------------
st.subheader("D · How should the Dumb Waiter be sold?")
fit = D.fit_score(buyer_d, cx_d, cyc_d)
inputs = dict(gi)
pf = 1 + price_chg / 100
cf, won, capped = D.option_cashflows(inputs, "base", avg_rep_cost,
                                     overrides={"pod_win_rate": pod_wr, "partner_accounts_per_year": partner_n},
                                     price_factor=pf, win_factor=0.9 if price_chg > 0 else 1.0)
ld, rd = st.columns([2, 3])
with ld:
    poor = fit["score"] >= D.FIT_THRESHOLD
    colr = STATUS_WARNING if poor else STATUS_GOOD
    st.metric("Fit score (≥ 0.50 = poor fit for the existing motion)", f"{fit['score']:.2f}")
    st.markdown(f"<div style='padding:10px;border-radius:8px;border:1px solid {colr};background:{colr}22;"
                f"font-weight:600'>{'⚠ ' if poor else '✓ '}{fit['verdict']}</div>", unsafe_allow_html=True)
    st.caption("The fit score says whether to take the product out of the generalists' bag. "
               "The economics on the right say where to put it.")
    totals = {o: cf[o].sum() / 1e6 for o in D.OPTIONS}
    best_d = max(totals, key=totals.get)
    st.markdown(f"**Best 24-month contribution at these settings: {best_d}.** " +
                " · ".join(f"{o} ₹{v:.1f}M ({won[o]:.0f} accounts)" for o, v in totals.items()))
    bbc = S["D"]["best_by_case"]
    st.caption(f"Pipeline result: {S['D']['recommendation']} in the base case. Pessimistic case: {bbc['low']}; "
               f"optimistic case: {bbc['high']}. The pod needs a {S['D']['pod_break_even_win_rate']:.0%} win rate "
               f"(25% assumed) to beat the best alternative."
               if S['D']['pod_break_even_win_rate'] else
               f"Pipeline result: {S['D']['recommendation']} in the base case. Pessimistic case: {bbc['low']}; "
               f"optimistic case: {bbc['high']}. No pod win rate beats partners at today's price: the reachable "
               f"market (~{S['D']['market_check']['som_units']:.0f} units a year) caps the pod's extra capacity.")
with rd:
    fig = go.Figure()
    for o, c in [("Existing sales force", C1), ("Dedicated pod", C2), ("Channel partners", C3),
                 ("Partners + architect programme", C4)]:
        fig.add_trace(go.Scatter(x=cf["month"], y=cf[o].cumsum() / 1e6, mode="lines", name=o, line=dict(color=c, width=2)))
    fig.add_hline(y=0, line_color=INK2)
    st.plotly_chart(style(fig, "Cumulative contribution after own costs, ₹M", "Month"), width="stretch")
bcn, bcc = gi["buying_centre_new"], gi["buying_centre_core"]
st.caption("**Buying centre** (share of orders where each role takes part) — Dumb Waiter: "
           + ", ".join(f"{k} {v:.0%}" for k, v in list(bcn.items())[:5])
           + ". Industrial lines: " + ", ".join(f"{k} {v:.0%}" for k, v in bcc.items())
           + f". Overlap is small, so buyer distance = {gi['buyer_distance']:.2f}.")
l3, m3, r3 = st.columns([5, 3, 3])
with l3:
    sod = data["sod"]
    so = S["D"]["service_outputs"]
    st.markdown("**What Dumb Waiter buyers need from a channel (service outputs, scored 1–5)**")
    show_sod = sod.rename(columns={"need": "Need", "weight": "Weight", "Existing sales force": "Existing",
                                   "Dedicated pod": "Pod", "Channel partners": "Dealers"})
    show_sod["Weight"] = show_sod["Weight"].map("{:.0%}".format)
    st.dataframe(show_sod, hide_index=True, width="stretch")
    st.caption("Weighted: " + " · ".join(f"{k} {v:.2f}" for k, v in so["totals"].items())
               + f". Changing any single score by one point flips the leader in {so['single_score_changes_that_flip_leader']} cases.")
with m3:
    mc = S["D"]["market_check"]
    mk = S["D"]["market"]["base"]
    fig = go.Figure(go.Bar(
        x=["TAM", "SOM (reachable)", "Partners (assumed)", "Pilot (actual)"],
        y=[mk["tam_units"], mk["som_units"], mc["assumed_partner_accounts_a_year"], gi["n_pilot_accounts"]],
        marker_color=[C1, C1, C2, C2], marker_line=dict(color="white", width=2)))
    fig.update_layout(hovermode="closest")
    st.markdown("**Market size, units a year (base case)**")
    st.plotly_chart(style(fig, "Units a year", height=300), width="stretch")
    st.caption(f"Built bottom-up from housing, hotel and hospital data (data/market_sizing.csv). "
               f"The market supports about {mc['dealers_supportable']:.0f} dealers at 6 installs each, so ~8 dealers "
               "is selective distribution, not intensive.")
with r3:
    ev = S["D"]["evc"]["base"]
    ps = S["D"]["price_scenario_contribution_24m_inr_m"]
    st.markdown("**Price check (economic value to the customer)**")
    st.markdown(f"Our price ₹{ev['current_price_inr'] / 1e5:.2f} lakh vs. competitor median "
                f"₹{ev['competitor_price_inr'] / 1e5:.1f} lakh → EVC ≈ ₹{ev['evc_inr'] / 1e5:.1f} lakh, "
                f"headroom ≈ ₹{ev['headroom_inr'] / 1e5:.1f} lakh. A hotel or hospital recovers the price in "
                f"~{ev['payback_years_for_buyer']:.1f} years of saved helper wages.")
    st.markdown("**At +20% price (10% fewer wins), 24-month contribution ₹M:** "
                + " · ".join(f"{k} {v:.1f}" for k, v in ps.items()))
    st.caption("Use the price slider to see it live.")
st.divider()

# ---------------------------------------------------------------------------
# Economics
# ---------------------------------------------------------------------------
st.subheader("$ · What the redesign saves, what the change costs, and when it pays back")
le, re_ = st.columns([2, 3])
with le:
    ba = data["before_after"].set_index(data["before_after"].columns[0])
    ba.index.name = "Metric"

    def fmt(metric, v):
        if "%" in metric or metric == "Net margin" or "product expert" in metric:
            return f"{float(v):.1%}"
        if metric in ("Sales reps", "Rep utilisation range"):
            return str(v)
        return f"{float(v):,.1f}"
    st.dataframe(pd.DataFrame({c: [fmt(m, v) for m, v in ba[c].items()] for c in ba.columns}, index=ba.index),
                 width="stretch")
    tr = data["transition"].set_index("case")
    st.markdown(f"**One-time cost of the change (base):** ₹{tr.loc['base', 'total_inr_m']:.1f}M "
                f"(low ₹{tr.loc['low', 'total_inr_m']:.1f}M, high ₹{tr.loc['high', 'total_inr_m']:.1f}M) — "
                f"{int(tr.loc['base', 'reps_released'])} reps released, "
                f"{int(tr.loc['base', 'accounts_moved'])} accounts changing owner.")
with re_:
    cv = data["curves"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cv["month"], y=cv["base|release now"], name="Release surplus reps now",
                             line=dict(color=C1, width=2)))
    fig.add_trace(go.Scatter(x=cv["month"], y=cv["base|attrition"], name="Hiring freeze, let attrition do it",
                             line=dict(color=C2, width=2)))
    fig.add_hline(y=0, line_color=INK2)
    st.plotly_chart(style(fig, "Cumulative net benefit, ₹M", "Month"), width="stretch")
pb = data["payback"]
st.dataframe(pd.DataFrame({
    "Case": pb["case"], "Path": pb["path"], "One-off cost ₹M": pb["one_off_cost_inr_m"].round(1),
    "Payback month": pb["payback_month"], "Net benefit by month 24, ₹M": pb["net_benefit_24m_inr_m"].round(1),
    "Months to target headcount": pb["months_to_target_headcount"],
}), hide_index=True, width="stretch")
st.caption("Phasing, owners and the KPIs to watch after rollout: docs/rollout_plan.md.")
