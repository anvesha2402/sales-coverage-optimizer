"""
dashboard/app.py — Module E: Scenario Dashboard

Business question: Does the recommended structure hold up across a range of
plausible futures, or only under the exact conditions it was designed for?

One Streamlit app, four sections top to bottom (per build plan §7), built
around one core interaction: moving the sidebar sliders recomputes Modules
A, B and D live. Module C (the territory optimizer) solves a real MILP per
region and is deliberately NOT re-solved on every slider tick -- it answers
a different, static question ("given today's fixed rep pool, how should it
be assigned") and is cached once. Its naive-vs-optimized comparison is
static; everything else on the page is live.

Run locally:
    streamlit run dashboard/app.py
"""

import os
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import coverage_simulator, diagnostics, gtm_scorer, territory_optimizer

# ---------------------------------------------------------------------------
# Palette (dataviz skill: fixed categorical order, status colors reserved,
# single-hue sequential for magnitude, never a rainbow)
# ---------------------------------------------------------------------------
C_BLUE = "#2a78d6"
C_ORANGE = "#eb6834"
C_AQUA = "#1baf7a"
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"
STATUS_CRITICAL = "#d03b3b"
INK_SECONDARY = "#52514e"
GRID = "#e1e0d9"

REGION_CENTROIDS = {  # approximate state/city centroids for the territory map
    "R01": (28.7041, 77.1025, "Delhi NCR"),
    "R02": (29.0588, 76.0856, "Haryana Belt"),
    "R03": (19.0760, 72.8777, "Maharashtra West"),
    "R04": (22.2587, 71.1924, "Gujarat Industrial Corridor"),
    "R05": (12.9716, 77.5946, "Karnataka South"),
    "R06": (13.0827, 80.2707, "Tamil Nadu Coastal"),
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "generated")

st.set_page_config(page_title="Sales Coverage & GTM Structure Optimizer", layout="wide")


def ensure_data_generated():
    """
    data/generated/ is gitignored on purpose (it's regenerable synthetic
    data, not something to keep in version control) -- so a fresh deploy
    (e.g. Streamlit Community Cloud pulling straight from GitHub) won't
    have it yet. Generate it once, on first run, with the same seed used
    everywhere else in this project, so results match exactly.
    """
    if os.path.exists(os.path.join(DATA_DIR, "accounts.csv")):
        return
    import subprocess
    generator_path = os.path.join(os.path.dirname(__file__), "..", "data", "generate_synthetic_company.py")
    subprocess.run([sys.executable, generator_path], check=True)


ensure_data_generated()


@st.cache_data
def load_base_data():
    accounts_df = pd.read_csv(os.path.join(DATA_DIR, "accounts.csv"))
    reps_df = pd.read_csv(os.path.join(DATA_DIR, "reps.csv"))
    return accounts_df, reps_df


@st.cache_data
def run_territory_optimizer_cached():
    return territory_optimizer.run_all(
        accounts_path=os.path.join(DATA_DIR, "accounts.csv"),
        reps_path=os.path.join(DATA_DIR, "reps.csv"),
    )


@st.cache_data
def compute_gtm_base_inputs():
    return gtm_scorer.compute_dumb_waiter_inputs(
        accounts_path=os.path.join(DATA_DIR, "accounts.csv")
    )


accounts_df, reps_df = load_base_data()
territory_result = run_territory_optimizer_cached()
gtm_base_inputs = compute_gtm_base_inputs()

st.title("Sales Coverage & GTM Structure Optimizer")
st.caption(
    "Generalized from *Lakshmi Projects: Sales Structure Dilemma* (Ivey W15219) "
    "· all figures synthetic — see docs/case_reference.md"
)

# ---------------------------------------------------------------------------
# Sidebar — scenario controls (drive Modules A, B, D live)
# ---------------------------------------------------------------------------
st.sidebar.header("Scenario controls")
revenue_growth_mult = st.sidebar.slider(
    "Revenue growth (6-yr multiple)", 1.3, 3.5, 2.1, 0.1,
    help="How much revenue grows over the 6-year window",
)
headcount_growth_mult = st.sidebar.slider(
    "Sales headcount growth (6-yr multiple)", 1.5, 8.0, 5.4, 0.1,
    help="How much sales headcount grows over the same window",
)
specialist_share_pct = st.sidebar.slider(
    "Specialization mix", 0, 100, 30, 5,
    help="0% = pure Geographic · 100% = pure Product Specialist",
)
new_product_complexity_dist = st.sidebar.slider(
    "New-product technical-complexity distance", 0.0, 1.0,
    round(gtm_base_inputs["technical_complexity_distance"], 2), 0.01,
    help="How different the new product's typical account is from the existing motion",
)

st.sidebar.divider()
st.sidebar.caption(
    "Every KPI, chart, and recommendation below (except the territory map, "
    "which is a separate fixed-pool question) recomputes as these move."
)

# ---------------------------------------------------------------------------
# Live recompute — Module A & B
# ---------------------------------------------------------------------------
scenario_yf = diagnostics.scenario_yearly_financials(
    revenue_growth_multiple=revenue_growth_mult,
    headcount_growth_multiple=headcount_growth_mult,
)
diag = diagnostics.diagnose_from_df(scenario_yf)

rng = np.random.default_rng(42)
spectrum_result = coverage_simulator.simulate_spectrum(
    accounts_df, reps_df, rng, specialist_share_pct / 100
)

gtm_result = gtm_scorer.score_new_product_gtm(
    buyer_persona_distance=gtm_base_inputs["buyer_persona_distance"],
    technical_complexity_distance=new_product_complexity_dist,
    deal_cycle_diff=gtm_base_inputs["deal_cycle_diff"],
)

# ---------------------------------------------------------------------------
# Section 1 — KPI row
# ---------------------------------------------------------------------------
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Headcount / revenue growth ratio", f"{diag['cumulative_growth_ratio']}x")
final_sales_cost_pct = scenario_yf["sales_opex_inr_m"].iloc[-1] / scenario_yf["total_cost_inr_m"].iloc[-1]
k2.metric("Sales cost as % of total cost (final yr)", f"{final_sales_cost_pct:.0%}")
k3.metric("Cost-to-serve (optimized territory)", f"₹{territory_result['total_optimized_cost_inr_m']:.1f}M")
k4.metric("Coverage-gap rate (this mix)", f"{spectrum_result['coverage_gap_rate']:.1%}")
k5.metric(
    "Sustainability threshold year",
    str(diag["threshold_year"]) if diag["threshold_year"] else "Not breached",
    delta=f"Score {diag['sustainability_score']}/100",
    delta_color="off",
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2 — Coverage model comparison (Module B, live on specialization mix)
# ---------------------------------------------------------------------------
left, right = st.columns([3, 2])

with left:
    st.subheader("Coverage model comparison")
    st.caption(
        f"At **{specialist_share_pct}% specialist**: cost ₹{spectrum_result['cost_to_serve_inr_m']:.1f}M · "
        f"coverage gap {spectrum_result['coverage_gap_rate']:.1%} · "
        f"specialization depth {spectrum_result['specialization_depth']:.1%}"
    )
    @st.cache_data
    def compute_sweep():
        rows = []
        for s in range(0, 101, 5):
            r = np.random.default_rng(42)
            res = coverage_simulator.simulate_spectrum(accounts_df, reps_df, r, s / 100)
            rows.append({"share": s, "cost": res["cost_to_serve_inr_m"], "depth": res["specialization_depth"]})
        return pd.DataFrame(rows)

    sweep_df = compute_sweep()

    fig_b = go.Figure()
    fig_b.add_trace(go.Scatter(
        x=sweep_df["share"], y=sweep_df["cost"], mode="lines",
        name="Cost-to-serve (₹M)", line=dict(color=C_BLUE, width=2),
    ))
    fig_b.add_trace(go.Scatter(
        x=[specialist_share_pct], y=[spectrum_result["cost_to_serve_inr_m"]],
        mode="markers", marker=dict(size=14, color=C_ORANGE, line=dict(width=2, color="white")),
        name="Current setting",
    ))
    fig_b.update_layout(
        yaxis_title="Cost-to-serve (₹M)", xaxis_title="Specialist share (0% = Geographic, 100% = Product Specialist)",
        plot_bgcolor="white", legend=dict(orientation="h", y=-0.2),
        margin=dict(t=10, b=10),
    )
    fig_b.update_xaxes(gridcolor=GRID, ticksuffix="%")
    fig_b.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fig_b, use_container_width=True)
    st.caption(
        "The jaggedness here is real, not noise — it's the greedy heuristic's sensitivity to "
        "exactly which specific reps get activated at each specialist-share cut point, not a "
        "smooth underlying cost function. A true optimization sweep (extending Module C's LP "
        "to this parameter) would be the more rigorous version of this chart."
    )

with right:
    st.subheader("Diagnostic trend (Module A)")
    fig_a = go.Figure()
    fig_a.add_trace(go.Scatter(
        x=scenario_yf["year"], y=scenario_yf["net_income_inr_m"] / scenario_yf["revenue_inr_m"],
        mode="lines+markers", name="Net margin", line=dict(color=C_BLUE, width=2),
    ))
    fig_a.add_hline(y=diag["margin_threshold"], line_dash="dash", line_color=STATUS_CRITICAL,
                     annotation_text="Sustainability threshold")
    fig_a.update_layout(
        yaxis_title="Net margin", yaxis_tickformat=".0%", xaxis_title="Year",
        plot_bgcolor="white", showlegend=False, margin=dict(t=10, b=10),
    )
    fig_a.update_xaxes(gridcolor=GRID, dtick=1)
    fig_a.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fig_a, use_container_width=True)
    st.caption(
        "Regenerated without noise for a smooth live response to the sliders — at the default "
        "2.1x/5.4x setting this reads slightly cleaner than the Stage 2 checkpoint's noisy "
        "dataset (score ~18 here vs. 14 there); same threshold year (2023) either way."
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — Territory map (Module C, static/cached)
# ---------------------------------------------------------------------------
st.subheader("Territory map — optimized vs. naive equal-split")
st.caption(
    f"Optimized cost-to-serve ₹{territory_result['total_optimized_cost_inr_m']:.1f}M vs. naive "
    f"₹{territory_result['total_naive_cost_inr_m']:.1f}M — "
    f"**{territory_result['pct_cost_improvement']:.1%} lower** at equivalent (100%) coverage. "
    "This section answers a different question from the sliders above (how to assign today's "
    "fixed rep pool), so it doesn't move with them. Shown as a treemap (region → rep, sized by "
    "revenue) rather than a literal map: the dataset has no real geocoded addresses, and a Plotly "
    "geo map needs a live fetch to an external basemap CDN that isn't reliably available in every "
    "runtime — this view carries the same information without that dependency."
)

view = st.radio("View", ["Optimized", "Naive equal-split"], horizontal=True, label_visibility="collapsed")

def build_territory_view(assignment_df):
    df = assignment_df.merge(
        accounts_df[["account_id", "annual_revenue_inr", "complexity_score", "product_line"]],
        on="account_id",
    )
    region_name_map = {rid: name for rid, (_, _, name) in REGION_CENTROIDS.items()}
    df["region_name"] = df["region_id"].map(region_name_map)
    return df

if view == "Optimized":
    tdf = build_territory_view(territory_result["territory_map"])
    reps_used = tdf["rep_id"].nunique()
    st.caption(f"{reps_used} reps activated across all 6 regions to cover all 650 accounts.")
else:
    tdf = build_territory_view(territory_result["naive_territory_map"])
    reps_used = tdf["rep_id"].nunique()
    st.caption(f"{reps_used} reps activated (essentially the whole pool) for the same coverage.")

fig_map = px.treemap(
    tdf, path=[px.Constant("All regions"), "region_name", "rep_id"],
    values="annual_revenue_inr", color="complexity_score",
    color_continuous_scale=["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"],  # blue sequential ramp
    hover_data={"product_line": True},
)
fig_map.update_layout(margin=dict(t=10, b=10, l=0, r=0), coloraxis_colorbar_title="Avg. complexity")
st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 4 — GTM scorer (Module D, live on complexity-distance slider)
# ---------------------------------------------------------------------------
st.subheader("New-product GTM scorer — Dumb Waiter launch")
gcol1, gcol2 = st.columns([2, 3])

with gcol1:
    st.metric("GTM score", f"{gtm_result['score']:.2f}", help="≥ 0.50 recommends a dedicated pod")
    rec_color = STATUS_WARNING if gtm_result["recommendation"] == "Dedicated pod" else STATUS_GOOD
    st.markdown(
        f"<div style='padding:12px;border-radius:8px;background:{rec_color}22;"
        f"border:1px solid {rec_color};font-weight:600'>{gtm_result['recommendation']}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"Buyer-persona distance {gtm_base_inputs['buyer_persona_distance']:.2f} · "
        f"technical-complexity distance {new_product_complexity_dist:.2f} (slider) · "
        f"deal-cycle diff {gtm_base_inputs['deal_cycle_diff']:.2f} (assumed — see gtm_scorer.py)"
    )

with gcol2:
    monthly_gain = (gtm_base_inputs["avg_revenue_new_inr"] * 40) / 12
    be_months = gtm_scorer.breakeven_months(gtm_scorer.POD_SETUP_COST_INR, monthly_gain)
    months = list(range(0, 13))
    cum_gain = [monthly_gain * m for m in months]
    fig_d = go.Figure()
    fig_d.add_trace(go.Scatter(x=months, y=cum_gain, mode="lines", name="Cumulative revenue gain",
                                line=dict(color=C_BLUE, width=2)))
    fig_d.add_hline(y=gtm_scorer.POD_SETUP_COST_INR, line_dash="dash", line_color=STATUS_CRITICAL,
                     annotation_text="Pod setup cost")
    if be_months != float("inf"):
        fig_d.add_vline(x=be_months, line_dash="dot", line_color=INK_SECONDARY,
                         annotation_text=f"Breakeven: {be_months:.1f} mo")
    fig_d.update_layout(
        yaxis_title="₹", xaxis_title="Months since pod launch",
        plot_bgcolor="white", showlegend=False, margin=dict(t=10, b=10),
    )
    fig_d.update_xaxes(gridcolor=GRID)
    fig_d.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fig_d, use_container_width=True)

st.caption(
    "Note the tension: the weighted score currently favors routing through the existing sales "
    "force, while the breakeven chart shows a pod would still pay for itself quickly if built — "
    "two different questions (see docs/business_insights.md)."
)
