"""
app.py
======

Interactive demo of the MMS-I growth and impact model.

    streamlit run app.py

Every assumption is a control in the sidebar. Nothing is hard coded into the
results. Change a slider and the whole projection recalculates.
"""

from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from mms_growth_model import (Params, season_net, wealth_path, simulate,
                              promotion_ladder, external_needed_for_target, MILLION)
from financing import FinancePlan, wealth_path_financed, seasons_to_threshold

NAVY, AMBER, STEEL, MUT, GREY = "#102C4E", "#E8871E", "#2E6DA4", "#6B7C8E", "#C3D0DD"
FMT = FuncFormatter(lambda v, p: f"{v/1e6:.1f}M" if v >= 1e6 else (f"{v/1e3:,.0f}k" if v >= 1000 else f"{v:,.0f}"))

st.set_page_config(page_title="MMS-I Growth and Impact Model",
                   page_icon="🌽", layout="wide")


def style(ax, xlabel="", ylabel=""):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color="#E7EEF5")
    ax.set_xlabel(xlabel, color=NAVY, fontweight="bold")
    ax.set_ylabel(ylabel, color=NAVY, fontweight="bold")
    ax.tick_params(colors=MUT)
    return ax


# --------------------------------------------------------------------------- #
#  Sidebar
# --------------------------------------------------------------------------- #
st.sidebar.title("Assumptions")
st.sidebar.caption("Every number below can be changed. The whole model recalculates.")

with st.sidebar.expander("Machine economics", expanded=True):
    price = st.number_input("Machine price (ETB)", 100_000, 1_500_000, 400_000, 10_000)
    thru = st.slider("Throughput (quintals/hour)", 10.0, 70.0, 40.0, 1.0)
    days = st.slider("Operating days per season", 20, 80, 50, 1)
    hours = st.slider("Productive hours per day", 3.0, 10.0, 6.0, 0.5)
    fee = st.slider("Service fee (ETB/quintal)", 40.0, 120.0, 70.0, 1.0)

with st.sidebar.expander("Operators", expanded=True):
    n_ops = st.slider("Operators per machine", 4, 20, 10, 1)
    wage = st.slider("Operator wage (ETB/day)", 200.0, 900.0, 500.0, 25.0)

with st.sidebar.expander("Running costs"):
    fuel_lph = st.slider("Fuel use (litres/hour)", 0.8, 3.5, 1.65, 0.05)
    fuel_price = st.slider("Fuel price (ETB/litre)", 100.0, 400.0, 200.0, 5.0)
    maint = st.number_input("Maintenance, season 1 (ETB)", 0, 60_000, 8_000, 500)
    maint_g = st.slider("Maintenance escalation per year", 0.0, 0.8, 0.35, 0.05)

with st.sidebar.expander("Co-financing", expanded=True):
    st.caption("Placeholder terms. Replace with the lessor's quote.")
    equity_pct = st.slider("Youth equity (%)", 0, 30, 5, 1)
    partner_pct = st.slider("Partner fund, interest free (%)", 0, 100, 45, 5)
    lease_pct = 100 - equity_pct - partner_pct
    st.metric("Lease facility (%)", f"{lease_pct}%")
    lease_rate = st.slider("Lease rate (%)", 0.0, 30.0, 14.5, 0.5) / 100
    lease_tenor = st.slider("Lease tenor (seasons)", 1, 8, 3, 1)
    partner_tenor = st.slider("Partner fund tenor (seasons)", 1, 8, 2, 1)

with st.sidebar.expander("Promotion ladder", expanded=True):
    min_service = st.slider("Seasons served before eligible", 1, 5, 2, 1)
    promo_rate = st.slider("Share of eligible promoted per year (%)", 0, 40, 8, 1) / 100
    save_rate = st.slider("Share of wages an operator saves (%)", 0, 80, 30, 5) / 100

with st.sidebar.expander("Fleet and market"):
    seed = st.slider("Machines in the pilot", 1, 100, 10, 1)
    external = st.slider("Externally financed machines per year", 0, 250, 0, 1)
    coverage = st.slider("Coverage target (% of Amhara volume)", 5, 60, 40, 5) / 100
    horizon = st.slider("Projection horizon (years)", 5, 20, 10, 1)
    mfg_cap = st.number_input("Manufacturing capacity, year 1", 10, 500, 50, 10)
    mfg_growth = st.slider("Capacity growth per year", 0.0, 1.0, 0.45, 0.05)

if lease_pct < 0:
    st.sidebar.error("Equity plus partner fund cannot exceed 100%.")
    st.stop()

p = Params(
    machine_price=price, throughput_qt_hr=thru, hours_per_day=hours,
    days_per_season=days, service_fee=fee, operators_per_machine=n_ops,
    operator_wage_day=wage, fuel_l_per_hr=fuel_lph, fuel_price=fuel_price,
    maintenance_year1=float(maint), maintenance_growth=maint_g,
    min_service_seasons=min_service, promotion_rate=promo_rate,
    operator_savings_rate=save_rate, mfg_capacity_year1=int(mfg_cap),
    mfg_capacity_growth=mfg_growth, external_machines_per_year=int(external),
    horizon_years=int(horizon),
)
plan = FinancePlan(
    machine_price=price, youth_equity_share=equity_pct / 100,
    partner_fund_share=partner_pct / 100, lease_share=lease_pct / 100,
    lease_rate=lease_rate, lease_tenor_seasons=lease_tenor,
    partner_tenor_seasons=partner_tenor,
)

# --------------------------------------------------------------------------- #
#  Header
# --------------------------------------------------------------------------- #
st.title("MMS-I Growth and Impact Model")
st.caption("Youth owned maize shelling enterprises in the Amhara region of Ethiopia. "
           "Mezewir Industrial Solutions PLC.")

net1 = season_net(1, p)
c = st.columns(5)
c[0].metric("Volume per season", f"{p.volume_per_machine:,.0f} qt")
c[1].metric("Revenue per season", f"{p.revenue_per_season:,.0f} ETB")
c[2].metric("Operator wages", f"{p.wage_bill_per_machine:,.0f} ETB")
c[3].metric("Owner net, season 1", f"{net1:,.0f} ETB")
c[4].metric("Households served", f"{p.households_per_machine:,.0f}")

if net1 <= 0:
    st.error("At these assumptions the machine loses money. Adjust the sidebar.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Owner and financing", "The promotion ladder", "Fleet growth", "Data"])

# --------------------------------------------------------------------------- #
#  Tab 1: owner economics and financing
# --------------------------------------------------------------------------- #
with tab1:
    left, right = st.columns([1, 1])

    with left:
        st.subheader("How the machine is paid for")
        s = plan.summary()
        st.dataframe(pd.DataFrame({
            "Source": ["Youth equity", "Partner fund (interest free)", "Lease facility"],
            "ETB": [s["youth_equity"], s["partner_principal"], s["lease_principal"]],
        }).style.format({"ETB": "{:,.0f}"}), hide_index=True, width="stretch")

        m = st.columns(3)
        m[0].metric("Lease payment", f"{s['lease_payment_per_season']:,.0f}/season")
        m[1].metric("Total interest", f"{s['total_interest']:,.0f} ETB")
        m[2].metric("Cost of capital", f"{s['cost_of_capital_pct_of_price']:.1f}% of price")

        st.subheader("Repayment schedule")
        st.dataframe(plan.schedule_table(min(8, horizon)).style.format("{:,.0f}"),
                     hide_index=True, width="stretch")

    with right:
        st.subheader("What the owner accumulates")
        f = lambda age: season_net(age, p)
        unf = wealth_path(horizon, p)
        fin = wealth_path_financed(horizon, f, plan)
        yrs = np.arange(1, horizon + 1)

        fig, ax = plt.subplots(figsize=(7, 4.6))
        ax.plot(yrs, unf, marker="s", color=MUT, lw=2.0, ms=6,
                label="Face value repayment, no interest")
        ax.plot(yrs, fin, marker="o", color=AMBER, lw=2.8, ms=7,
                label="With the co-financing structure")
        ax.axhline(MILLION, color=NAVY, ls="--", lw=1.4, label="1,000,000 ETB")
        style(ax, "Season", "Cumulative cash held (ETB)")
        ax.yaxis.set_major_formatter(FMT)
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        st.pyplot(fig)

        sm = seasons_to_threshold(f, plan)
        su = next((i + 1 for i, v in enumerate(unf) if v >= MILLION), None)
        k = st.columns(2)
        k[0].metric("Millionaire season, financed", sm if sm else "beyond horizon")
        k[1].metric("Without financing cost", su if su else "beyond horizon")
        if sm and su and sm > su:
            st.info(f"Financing cost delays the milestone by {sm - su} season(s). "
                    f"Interest over the life of the facility is {s['total_interest']:,.0f} ETB.")

# --------------------------------------------------------------------------- #
#  Tab 2: promotion ladder
# --------------------------------------------------------------------------- #
with tab2:
    st.subheader("An operator should not stay an operator")
    st.write(f"A young person works {min_service} seasons as an operator, saving "
             f"{save_rate:.0%} of wages. The owner recommends them, credit is approved, "
             "and those savings become the equity on their own machine. The cost of "
             "that credit is charged against their income on the same terms set in the sidebar.")

    lad = promotion_ladder(p, promote_after=min_service, horizon=horizon, plan=plan)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(lad.year, lad.stay_operator_gross_etb, marker="s", color=MUT, lw=2.2, ms=7,
            label="Stays an operator (wages only)")
    ax.plot(lad.year, lad.promoted_total_etb, marker="o", color=AMBER, lw=3.0, ms=8,
            label=f"Promoted in season {min_service + 1}, cost of credit included")
    ax.axhline(MILLION, color=NAVY, ls="--", lw=1.4, label="1,000,000 ETB")
    ax.axvspan(0.5, min_service + 0.5, color=STEEL, alpha=0.08)
    style(ax, "Season", "Cumulative money held (ETB)")
    ax.yaxis.set_major_formatter(FMT)
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)

    last = lad.iloc[-1]
    k = st.columns(4)
    k[0].metric("Operator earns per season", f"{p.operator_earnings_per_season:,.0f} ETB")
    k[1].metric("Down payment saved", f"{p.operator_earnings_per_season * save_rate * min_service:,.0f} ETB")
    k[2].metric(f"Promoted, season {horizon}", f"{last.promoted_total_etb:,.0f} ETB")
    k[3].metric("Multiple vs staying",
                f"{last.promoted_total_etb / max(last.stay_operator_gross_etb, 1):.0f}x")

# --------------------------------------------------------------------------- #
#  Tab 3: fleet growth
# --------------------------------------------------------------------------- #
with tab3:
    target = p.machines_for_coverage(coverage)
    st.subheader(f"Reaching {coverage:.0%} of the Amhara harvest means {target:,} machines")

    df = simulate(p, seed_machines=seed, fleet_cap=target)
    yrs = df.year.values

    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.bar(yrs, df.machines, 0.6, color=GREY, edgecolor=NAVY, lw=0.6, label="Machine owners")
    ax.bar(yrs, df.millionaire_owners, 0.6, color=AMBER, edgecolor=NAVY, lw=0.6,
           label="Owners past 1,000,000 ETB")
    ax2 = ax.twinx()
    ax2.plot(yrs, df.operators_employed, marker="o", color=NAVY, lw=2.4, ms=7,
             label="Operators paid each season")
    ax2.set_ylabel("Operators paid each season", color=NAVY, fontweight="bold")
    ax2.grid(False)
    style(ax, "Year", "Owners and millionaire owners")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
    fig.tight_layout()
    st.pyplot(fig)

    r = df.iloc[-1]
    k = st.columns(5)
    k[0].metric("Machines", f"{r.machines:,.0f}")
    k[1].metric("Millionaire owners", f"{r.millionaire_owners:,.0f}")
    k[2].metric("Operators paid", f"{r.operators_employed:,.0f}")
    k[3].metric("Households served", f"{r.households_served:,.0f}")
    k[4].metric("Coverage", f"{r.coverage_pct:.1f}%")

    if r.machines < target * 0.99:
        need = external_needed_for_target(p, seed, coverage, horizon)
        if need >= 0:
            st.warning(
                f"The pilot does not reach {coverage:.0%} on the promotion ladder alone. "
                f"It needs about **{need} externally financed machines a year** to get "
                f"there by year {horizon}. Set the sidebar slider to {need} to see it.")
        else:
            st.warning("This target is out of reach within the manufacturing capacity set.")

# --------------------------------------------------------------------------- #
#  Tab 4: data
# --------------------------------------------------------------------------- #
with tab4:
    st.subheader("Year by year")
    st.dataframe(df.round(1), hide_index=True, width="stretch")
    st.download_button("Download this projection (CSV)",
                       df.to_csv(index=False), "mms_projection.csv", "text/csv")

    st.subheader("Promotion ladder")
    st.dataframe(lad.round(0), hide_index=True, width="stretch")
    st.download_button("Download the ladder (CSV)",
                       lad.to_csv(index=False), "mms_promotion_ladder.csv", "text/csv")

    with st.expander("What this model does not claim"):
        st.markdown("""
- **Birr, not dollars.** One million ETB is about 5,900 USD at 170 ETB/USD.
- **Constant 2026 prices.** No inflation is applied.
- **Lease terms are placeholders** until a lessor quotes them.
- **Households are counted per season**, never accumulated across years.
- **Operator positions are seasonal**, not year round employment.
- Rural unemployment in Ethiopia is about 3.6%. The measured problem is
  underemployment, around 27% of the rural employed. This programme converts
  underemployment into paid work and then into ownership. It does not reduce
  an unemployment rate.
        """)

st.caption("Sources in docs/ASSUMPTIONS.md. Model: mms_growth_model.py and financing.py. "
           "MIT licence.")
