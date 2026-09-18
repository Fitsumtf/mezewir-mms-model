"""
make_charts.py
Figures for the MMS-I growth model. Run after mms_growth_model.py is importable.
"""
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Patch

from mms_growth_model import Params, simulate, scenario_table, promotion_ladder, \
                             external_needed_for_target, MILLION
from financing import FinancePlan
from dataclasses import asdict

HERE = Path(__file__).resolve().parent
OUT = str(HERE.parent / "figures") + "/"
os.makedirs(OUT, exist_ok=True)
NAVY, AMBER, STEEL, MUT, GREY, GREEN = "#102C4E", "#E8871E", "#2E6DA4", "#6B7C8E", "#C3D0DD", "#4E7226"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 12,
    "axes.edgecolor": "#B9C7D6", "axes.labelcolor": NAVY, "text.color": NAVY,
    "axes.labelsize": 12.5, "axes.labelweight": "bold",
    "xtick.color": MUT, "ytick.color": MUT,
    "axes.grid": True, "grid.color": "#E7EEF5",
    "legend.frameon": True, "legend.edgecolor": "#B9C7D6", "legend.fontsize": 11.5,
    "figure.dpi": 200, "savefig.dpi": 200,
})
FMT = FuncFormatter(lambda v, p: f"{v/1e6:.1f}M" if v >= 1e6 else (f"{v/1e3:,.0f}k" if v >= 1000 else f"{v:,.0f}"))


def frame(title, sub, left=0.105):
    fig, ax = plt.subplots(figsize=(12.8, 7.0))
    fig.subplots_adjust(top=0.79, bottom=0.175, left=left, right=0.955)
    fig.text(left, 0.945, title, fontsize=20, fontweight="bold", color=NAVY, va="top")
    fig.text(left, 0.873, sub, fontsize=12, color=MUT, va="top")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return fig, ax


def save(fig, name, foot, left=0.105):
    fig.text(left, 0.028, foot, fontsize=11.5, color=NAVY, fontweight="bold")
    fig.savefig(OUT + name, facecolor="white")
    plt.close(fig)
    print("  ", name)


p = Params()
plan = FinancePlan()          # placeholder lease terms, see financing.py
yrs = np.arange(1, 11)

# ---------- G1: the promotion ladder ----------
lad = promotion_ladder(p, plan=plan)
fig, ax = frame("An operator should not stay an operator",
                "Two futures for the same young person. Path B serves two seasons, is recommended by the owner, then receives credit for a machine.")
ax.plot(lad.year, lad.stay_operator_gross_etb, marker="s", color=MUT, lw=2.4, ms=8,
        label="Path A: stays an operator (wages only)")
ax.plot(lad.year, lad.promoted_total_etb, marker="o", color=AMBER, lw=3.2, ms=9,
        label="Path B: promoted to owner in season 3, credit costed")
ax.axhline(MILLION, color=NAVY, ls="--", lw=1.6, label="1,000,000 ETB threshold")
ax.axvspan(0.5, 2.5, color=STEEL, alpha=0.09)
ax.text(1.5, 3.15e6, "serving as\nan operator", ha="center", fontsize=11, color=STEEL, fontweight="bold")
ax.annotate("recommended,\nfinanced, owns a machine", xy=(3, lad.promoted_total_etb.iloc[2]),
            xytext=(3.6, 1.35e6), fontsize=11.5, color=AMBER, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=AMBER, lw=1.8))
ax.set_xlabel("Season")
ax.set_ylabel("Cumulative money held (ETB)")
ax.set_xticks(yrs)
ax.yaxis.set_major_formatter(FMT)
ax.legend(loc="upper left")
save(fig, "G1_promotion_ladder.png",
     f"By season 7 the promoted operator holds {lad.promoted_total_etb.iloc[6]:,.0f} ETB against "
     f"{lad.stay_operator_gross_etb.iloc[6]:,.0f} ETB for the one who stayed.\n"
     f"That is about {lad.promoted_total_etb.iloc[6]/lad.stay_operator_gross_etb.iloc[6]:.0f} times more, "
     "and they own a 400,000 ETB machine outright.")

# ---------- G2: fleet growth under three financing levels ----------
fig, ax = frame("A pilot of 10 machines cannot reach 40% on its own",
                "Growth from promotion alone, compared with promotion plus outside financing from Wonfel and a bank.")
cases = [("Promotion ladder only", 0, MUT, "s"),
         ("Plus 37 machines a year (20% by year 7)", 37, STEEL, "^"),
         ("Plus 101 machines a year (40% by year 7)", 101, AMBER, "o")]
for label, ext, col, mk in cases:
    q = Params(**{**asdict(p), "external_machines_per_year": ext})
    cap = 10**9 if ext == 0 else p.machines_for_coverage(0.20 if ext == 37 else 0.40)
    df = simulate(q, seed_machines=10, fleet_cap=cap)
    ax.plot(df.year, df.machines, marker=mk, color=col, lw=2.8, ms=8, label=label)
ax.axhline(433, color=STEEL, ls=":", lw=1.5, label="433 machines = 20% of Amhara")
ax.axhline(867, color=AMBER, ls=":", lw=1.5, label="867 machines = 40% of Amhara")
ax.set_xlabel("Year")
ax.set_ylabel("Machines in the field")
ax.set_xticks(yrs)
ax.legend(loc="upper left")
save(fig, "G2_fleet_growth_paths.png",
     "Starting from 10 machines, promotion alone reaches 120 machines and 5.5% coverage by year 10.")

# ---------- G3: millionaires and operators at 40% coverage ----------
ext40 = external_needed_for_target(p, 10, 0.40, 7)
q = Params(**{**asdict(p), "external_machines_per_year": ext40})
df40 = simulate(q, seed_machines=10, fleet_cap=p.machines_for_coverage(0.40))
fig, ax = frame("At 40% coverage: owners, millionaires and paid operators",
                f"Pilot of 10 machines plus {ext40} externally financed machines a year, with the promotion ladder running throughout.", left=0.10)
ax.bar(df40.year, df40.machines, 0.62, color=GREY, edgecolor=NAVY, lw=0.7, label="Machine owners")
ax.bar(df40.year, df40.millionaire_owners, 0.62, color=AMBER, edgecolor=NAVY, lw=0.7,
       label="Owners past 1,000,000 ETB")
ax2 = ax.twinx(); ax2.grid(False); ax2.spines["top"].set_visible(False)
ax2.plot(df40.year, df40.operators_employed, marker="o", color=NAVY, lw=2.8, ms=8,
         label="Operators paid each season (right axis)")
ax2.set_ylabel("Operators paid each season")
ax2.yaxis.set_major_formatter(FMT)
ax2.tick_params(axis="y", colors=NAVY)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left")
ax.set_xlabel("Year"); ax.set_ylabel("Owners and millionaire owners"); ax.set_xticks(yrs)
r7 = df40[df40.year == 7].iloc[0]; r10 = df40[df40.year == 10].iloc[0]
save(fig, "G3_coverage40_outcomes.png",
     f"Year 7: {r7.machines:,.0f} owners, {r7.millionaire_owners:,.0f} of them past one million birr, "
     f"{r7.operators_employed:,.0f} operators paid. Year 10: {r10.millionaire_owners:,.0f} millionaires.")

# ---------- G4: where the money goes each season at 40% ----------
fig, ax = frame("Where the money goes each season at 40% coverage",
                "Operator wages compared with owner income, at full fleet. Both are new money in the rural economy.")
wages = df40.operator_wage_bill_etb
owner_income = df40.machines * 483_000
ax.stackplot(df40.year, wages, owner_income,
             colors=[AMBER, STEEL], alpha=0.88,
             labels=["Paid to operators as wages", "Retained by owners as income"])
ax.set_xlabel("Year"); ax.set_ylabel("ETB flowing to rural households each season")
ax.set_xticks(yrs); ax.yaxis.set_major_formatter(FMT)
ax.legend(loc="upper left")
save(fig, "G4_money_flow.png",
     f"At full fleet: {wages.iloc[-1]:,.0f} ETB a season in operator wages and "
     f"{owner_income.iloc[-1]:,.0f} ETB retained by owners.")

print("charts done")
