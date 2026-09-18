"""
mms_growth_model.py
===================

Growth and impact model for the Mezewir MMS-I maize sheller programme.

The model answers four questions:

  1. If N machines are financed, how many owners pass 1,000,000 ETB, and when?
  2. How many operators are paid, for how many days, and how much do they earn?
  3. How does the fleet grow when good operators are promoted into ownership?
  4. What share of the regional maize harvest does the fleet cover?

The distinguishing feature is the **promotion ladder**. An operator is not
meant to stay an operator. After a minimum period of service, on the
recommendation of the machine owner, an operator becomes eligible for credit
and can acquire a machine of their own. Those new owners hire ten operators
each, and the cycle repeats. Growth therefore comes from inside the programme
rather than only from outside financing.

Author: Dr. Fitsum Feyissa, Mezewir Industrial Solutions PLC / FitEx Industrial
Licence: MIT
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List

import numpy as np
import pandas as pd

from financing import FinancePlan, wealth_path_financed

ETB_PER_USD = 170.0
MILLION = 1_000_000.0


# --------------------------------------------------------------------------- #
#  Parameters
# --------------------------------------------------------------------------- #
@dataclass
class Params:
    """All model assumptions in one place. Every default is sourced in README.md."""

    # --- machine economics (Mezewir financial model) ---
    machine_price: float = 400_000.0     # ETB
    throughput_qt_hr: float = 40.0       # quintals per hour, base case
    hours_per_day: float = 6.0
    days_per_season: int = 50
    service_fee: float = 70.0            # ETB per quintal
    operators_per_machine: int = 10
    operator_wage_day: float = 500.0     # ETB per worker per working day
    fuel_l_per_hr: float = 1.65
    fuel_price: float = 200.0            # ETB per litre
    maintenance_year1: float = 8_000.0   # oil and belt allowance
    maintenance_growth: float = 0.35     # real escalation per year of machine age

    # --- repayment ---
    annual_repayment: float = 200_000.0  # ETB per season until the machine is cleared
    max_repay_share: float = 0.60        # never take more than this share of a season

    # --- promotion ladder (operator becomes owner) ---
    min_service_seasons: int = 2         # seasons before an operator is eligible
    promotion_rate: float = 0.08         # share of eligible operators promoted per year
    operator_savings_rate: float = 0.30  # share of wages an operator saves toward a machine

    # --- supply and demand constraints ---
    mfg_capacity_year1: int = 50         # machines Mezewir can build in year 1
    mfg_capacity_growth: float = 0.45    # annual growth in manufacturing capacity
    external_machines_per_year: int = 0  # extra units financed by Wonfel or a bank

    # --- market reference (CSA 2021/22 Meher, Amhara) ---
    region_volume_qt: float = 26_000_000.0
    qt_per_household: float = 11_070_933.0 / 623_797.0   # CSA West Gojam maize row

    # --- social multiplier ---
    people_per_earner: int = 5           # minimum people supported by each earner

    # --- run control ---
    horizon_years: int = 10

    # ---- derived ----
    @property
    def volume_per_machine(self) -> float:
        return self.throughput_qt_hr * self.hours_per_day * self.days_per_season

    @property
    def revenue_per_season(self) -> float:
        return self.volume_per_machine * self.service_fee

    @property
    def wage_bill_per_machine(self) -> float:
        return self.operators_per_machine * self.operator_wage_day * self.days_per_season

    @property
    def fuel_per_season(self) -> float:
        return self.fuel_l_per_hr * self.hours_per_day * self.days_per_season * self.fuel_price

    @property
    def households_per_machine(self) -> float:
        return self.volume_per_machine / self.qt_per_household

    @property
    def operator_earnings_per_season(self) -> float:
        return self.operator_wage_day * self.days_per_season

    def machines_for_coverage(self, share: float) -> int:
        """Machines needed to shell `share` of the regional volume."""
        return int(round(self.region_volume_qt * share / self.volume_per_machine))


# --------------------------------------------------------------------------- #
#  Owner economics
# --------------------------------------------------------------------------- #
def season_net(age: int, p: Params) -> float:
    """Owner net income in the machine's `age`-th season (age starts at 1)."""
    maintenance = p.maintenance_year1 * (1 + p.maintenance_growth) ** (age - 1)
    return p.revenue_per_season - p.wage_bill_per_machine - p.fuel_per_season - maintenance


def wealth_path(horizon: int, p: Params, down_payment: float = 0.0) -> List[float]:
    """
    Cumulative cash an owner holds, season by season, after repaying the machine.

    `down_payment` is money the owner brings in (an operator's savings), which
    reduces the debt and therefore shortens the repayment period.
    """
    owed = max(p.machine_price - down_payment, 0.0)
    cum, out = 0.0, []
    for age in range(1, horizon + 1):
        net = season_net(age, p)
        pay = min(p.annual_repayment, p.max_repay_share * max(net, 0.0), owed)
        owed -= pay
        cum += net - pay
        out.append(cum)
    return out


def seasons_to_million(p: Params, down_payment: float = 0.0) -> int | None:
    """How many seasons before this owner passes 1,000,000 ETB."""
    for i, w in enumerate(wealth_path(40, p, down_payment), start=1):
        if w >= MILLION:
            return i
    return None


# --------------------------------------------------------------------------- #
#  Simulation
# --------------------------------------------------------------------------- #
def simulate(p: Params, seed_machines: int, coverage_share: float | None = None,
             fleet_cap: int | None = None) -> pd.DataFrame:
    """
    Run the fleet forward with the operator promotion ladder switched on.

    Parameters
    ----------
    seed_machines   : machines financed in year 1 (the pilot)
    coverage_share  : stop growing at this share of the regional harvest
    fleet_cap       : hard machine ceiling, overrides coverage_share

    Returns one row per year.
    """
    if fleet_cap is None:
        fleet_cap = p.machines_for_coverage(coverage_share) if coverage_share else 10**9

    # owner cohorts: {start_year: {"count": n, "down": down_payment}}
    owners: Dict[int, Dict[str, float]] = {1: {"count": float(seed_machines), "down": 0.0}}
    # operator cohorts by hire year -> count
    operators: Dict[int, float] = {}

    rows = []
    for year in range(1, p.horizon_years + 1):
        fleet = sum(c["count"] for c in owners.values())

        # ---- staff the fleet ----
        needed = fleet * p.operators_per_machine
        employed = sum(operators.values())
        if needed > employed:
            operators[year] = operators.get(year, 0.0) + (needed - employed)
        employed = sum(operators.values())

        # ---- who is eligible for promotion ----
        eligible = sum(n for hire_yr, n in operators.items()
                       if year - hire_yr >= p.min_service_seasons)
        promoted = eligible * p.promotion_rate

        # ---- growth is limited by capacity and by the market ceiling ----
        capacity = p.mfg_capacity_year1 * (1 + p.mfg_capacity_growth) ** (year - 1)
        room = max(fleet_cap - fleet, 0.0)
        new_from_promotion = min(promoted, capacity, room)
        room -= new_from_promotion
        capacity -= new_from_promotion
        new_from_external = min(p.external_machines_per_year, capacity, room)

        # an operator's savings become the down payment on their own machine
        seasons_served = p.min_service_seasons
        down = (p.operator_earnings_per_season * p.operator_savings_rate * seasons_served)

        # ---- millionaires among current owners ----
        millionaires = 0.0
        owner_wealth_total = 0.0
        for start, coh in owners.items():
            age = year - start + 1
            if age < 1:
                continue
            path = wealth_path(age, p, coh["down"])
            w = path[age - 1]
            owner_wealth_total += w * coh["count"]
            if w >= MILLION:
                millionaires += coh["count"]

        # ---- operator earnings ----
        operator_wages = fleet * p.wage_bill_per_machine
        operator_days = fleet * p.operators_per_machine * p.days_per_season

        rows.append({
            "year": year,
            "machines": fleet,
            "owners": fleet,
            "millionaire_owners": millionaires,
            "millionaire_share_pct": 100 * millionaires / fleet if fleet else 0.0,
            "operators_employed": employed,
            "operators_promoted": new_from_promotion,
            "new_machines_external": new_from_external,
            "paid_operator_days": operator_days,
            "operator_wage_bill_etb": operator_wages,
            "operator_earnings_each_etb": p.operator_earnings_per_season,
            "households_served": fleet * p.households_per_machine,
            "people_supported": (fleet + employed) * p.people_per_earner,
            "owner_wealth_total_etb": owner_wealth_total,
            "coverage_pct": 100 * fleet * p.volume_per_machine / p.region_volume_qt,
        })

        # ---- roll forward ----
        if new_from_promotion > 0:
            # promoted operators leave the pool, oldest cohorts first
            to_remove = new_from_promotion
            for hire_yr in sorted(operators):
                if to_remove <= 0:
                    break
                take = min(operators[hire_yr], to_remove)
                operators[hire_yr] -= take
                to_remove -= take
            owners.setdefault(year + 1, {"count": 0.0, "down": down})
            owners[year + 1]["count"] += new_from_promotion
        if new_from_external > 0:
            owners.setdefault(year + 1, {"count": 0.0, "down": 0.0})
            # blend: external units carry no down payment
            owners[year + 1]["count"] += new_from_external

    df = pd.DataFrame(rows)
    df["cumulative_operator_days"] = df["paid_operator_days"].cumsum()
    return df


# --------------------------------------------------------------------------- #
#  Scenarios
# --------------------------------------------------------------------------- #
def run_scenarios(p: Params) -> Dict[str, pd.DataFrame]:
    """The three cases Wonfel asked about."""
    return {
        "pilot_10":     simulate(p, seed_machines=10, fleet_cap=10**9),
        "coverage_20":  simulate(p, seed_machines=10, coverage_share=0.20),
        "coverage_40":  simulate(p, seed_machines=10, coverage_share=0.40),
    }


def summarise(df: pd.DataFrame, p: Params, at_year: int = 7) -> Dict[str, float]:
    r = df[df.year == at_year].iloc[0]
    return {
        "year": at_year,
        "machines": round(r.machines),
        "millionaire_owners": round(r.millionaire_owners),
        "millionaire_share_pct": round(r.millionaire_share_pct, 1),
        "operators_employed": round(r.operators_employed),
        "operators_promoted_to_owner_that_year": round(r.operators_promoted),
        "operator_wage_bill_etb": round(r.operator_wage_bill_etb),
        "paid_operator_days": round(r.paid_operator_days),
        "cumulative_operator_days": round(r.cumulative_operator_days),
        "households_served": round(r.households_served),
        "people_supported": round(r.people_supported),
        "coverage_pct": round(r.coverage_pct, 2),
    }


# --------------------------------------------------------------------------- #
#  Solver: how much outside financing does a coverage target need?
# --------------------------------------------------------------------------- #
def external_needed_for_target(p: Params, seed_machines: int, coverage_share: float,
                               by_year: int, hi: int = 400) -> int:
    """
    Promotion alone grows the fleet slowly at first. This finds the smallest
    number of externally financed machines per year (Wonfel fund plus bank
    facility) that reaches `coverage_share` of the regional harvest by `by_year`.

    Returns machines per year, or -1 if the target is unreachable within the
    manufacturing capacity assumed in `p`.
    """
    target = p.machines_for_coverage(coverage_share)
    lo, best = 0, -1
    while lo <= hi:
        mid = (lo + hi) // 2
        q = Params(**{**asdict(p), "external_machines_per_year": mid})
        df = simulate(q, seed_machines=seed_machines, fleet_cap=target)
        reached = df.loc[df.year == by_year, "machines"].iloc[0] >= target - 0.5
        if reached:
            best, hi = mid, mid - 1
        else:
            lo = mid + 1
    return best


def scenario_table(p: Params, seed_machines: int = 10) -> pd.DataFrame:
    """Compare organic growth against the two coverage targets Wonfel asked about."""
    rows = []
    cases = [
        ("Pilot only, promotion ladder", None, 0),
        ("Reach 20% of Amhara by year 7", 0.20, None),
        ("Reach 40% of Amhara by year 7", 0.40, None),
        ("Reach 40% of Amhara by year 10", 0.40, None),
    ]
    for label, cov, ext in cases:
        by = 10 if "year 10" in label else 7
        if cov is None:
            q, cap = p, 10**9
        else:
            ext = external_needed_for_target(p, seed_machines, cov, by)
            q = Params(**{**asdict(p), "external_machines_per_year": max(ext, 0)})
            cap = p.machines_for_coverage(cov)
        df = simulate(q, seed_machines=seed_machines, fleet_cap=cap)
        s7, s10 = summarise(df, q, 7), summarise(df, q, 10)
        rows.append({
            "scenario": label,
            "externally financed per year": ext if ext is not None else 0,
            "machines yr7": s7["machines"], "machines yr10": s10["machines"],
            "millionaires yr7": s7["millionaire_owners"],
            "millionaires yr10": s10["millionaire_owners"],
            "operators yr7": s7["operators_employed"],
            "operators yr10": s10["operators_employed"],
            "households yr10": s10["households_served"],
            "coverage yr10 %": s10["coverage_pct"],
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
#  The promotion ladder, from the operator's point of view
# --------------------------------------------------------------------------- #
def promotion_ladder(p: Params, promote_after: int = 2, horizon: int = 10,
                     plan: "FinancePlan | None" = None) -> pd.DataFrame:
    """
    Compare two futures for the same young person.

    Path A: stays an operator for the whole period, earning a wage each season.
    Path B: serves `promote_after` seasons, is recommended by the owner, receives
            credit, and runs a machine of their own from then on.

    Pass a `FinancePlan` to charge the real cost of that credit. Leave it as
    None to see the path with no financing cost.

    The savings accumulated as an operator become the down payment, which
    shortens the repayment period on their machine.
    """
    wage = p.operator_earnings_per_season
    saved = wage * p.operator_savings_rate * promote_after

    if plan is None:
        # no financing cost: the machine is repaid at face value
        owner_curve = wealth_path(horizon, p, down_payment=saved)
    else:
        # The operator's savings become the equity on their own machine. The
        # remaining principal is split between the partner fund and the lease
        # in the same proportion as the programme-level plan, so the ladder and
        # the co-financing section use one consistent set of assumptions.
        eq = min(saved / p.machine_price, 1.0)
        rest = 1.0 - eq
        denom = plan.partner_fund_share + plan.lease_share
        pf = rest * (plan.partner_fund_share / denom) if denom else 0.0
        personal = FinancePlan(
            machine_price=p.machine_price,
            youth_equity_share=eq, partner_fund_share=pf, lease_share=rest - pf,
            lease_rate=plan.lease_rate,
            lease_tenor_seasons=plan.lease_tenor_seasons,
            partner_tenor_seasons=plan.partner_tenor_seasons,
            grace_seasons=plan.grace_seasons,
        )
        owner_curve = wealth_path_financed(
            horizon, lambda age: season_net(age, p), personal)

    rows = []
    for year in range(1, horizon + 1):
        stay = wage * year                       # gross lifetime wages as an operator
        stay_saved = wage * p.operator_savings_rate * year
        if year <= promote_after:
            promoted = wage * year
            promoted_saved = wage * p.operator_savings_rate * year
            status = "operator"
        else:
            age = year - promote_after           # seasons as an owner
            promoted = wage * promote_after + owner_curve[age - 1]
            promoted_saved = promoted
            status = f"owner, season {age}"
        rows.append({
            "year": year,
            "path_B_status": status,
            "stay_operator_gross_etb": stay,
            "stay_operator_saved_etb": stay_saved,
            "promoted_total_etb": promoted,
            "promoted_total_usd": promoted / ETB_PER_USD,
            "advantage_etb": promoted - stay,
            "millionaire": promoted >= MILLION,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="MMS-I fleet growth and impact model")
    ap.add_argument("--seed", type=int, default=10, help="machines in the pilot")
    ap.add_argument("--coverage", type=float, default=None,
                    help="target share of regional harvest, e.g. 0.40")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--promotion-rate", type=float, default=0.08)
    ap.add_argument("--out", type=str, default=None, help="write results to this CSV")
    a = ap.parse_args()

    p = Params(horizon_years=a.years, promotion_rate=a.promotion_rate)
    df = simulate(p, seed_machines=a.seed, coverage_share=a.coverage)

    pd.set_option("display.width", 200, "display.max_columns", 50)
    print(df.round(1).to_string(index=False))
    print()
    print(json.dumps(summarise(df, p, at_year=min(7, a.years)), indent=2))
    if a.out:
        df.to_csv(a.out, index=False)
        print(f"\nwritten to {a.out}")


if __name__ == "__main__":
    main()
