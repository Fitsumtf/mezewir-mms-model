"""
financing.py
============

Co-financing structure for an MMS-I machine.

Three sources pay Mezewir in full at delivery, and the youth owner repays two
of them out of the harvest:

    youth equity      small down payment, often savings from seasons worked
                      as an operator. No repayment.
    partner fund      an interest free contribution from a development
                      partner such as Wonfel Aid, repaid over a short term.
    lease facility    a capital goods lease or bank facility, carrying
                      interest, repaid over a longer term.

IMPORTANT
---------
The default lease rate and tenor below are **illustrative placeholders**. They
are not quoted terms. Replace them with the indicative terms from the lessor
before this model is used for any commitment. Every default is exposed as a
parameter so that a single edit updates the whole projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass
class FinancePlan:
    """How one machine is paid for, and how the owner repays it."""

    machine_price: float = 400_000.0

    # --- shares of the machine price. must sum to 1.0 ---
    youth_equity_share: float = 0.05     # 20,000 ETB, roughly an operator's savings
    partner_fund_share: float = 0.45     # 180,000 ETB from the partner fund
    lease_share: float = 0.50            # 200,000 ETB on a lease facility

    # --- terms. PLACEHOLDERS until the lessor quotes ---
    lease_rate: float = 0.145            # nominal annual rate
    lease_tenor_seasons: int = 3
    partner_tenor_seasons: int = 2       # interest free
    grace_seasons: int = 0               # seasons before the first payment falls due

    def __post_init__(self) -> None:
        total = self.youth_equity_share + self.partner_fund_share + self.lease_share
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"financing shares must sum to 1.0, got {total:.4f}")

    # ---- principal amounts ----
    @property
    def youth_equity(self) -> float:
        return self.machine_price * self.youth_equity_share

    @property
    def partner_principal(self) -> float:
        return self.machine_price * self.partner_fund_share

    @property
    def lease_principal(self) -> float:
        return self.machine_price * self.lease_share

    # ---- schedules ----
    @property
    def lease_payment(self) -> float:
        """Level annuity payment on the lease facility."""
        P, r, n = self.lease_principal, self.lease_rate, self.lease_tenor_seasons
        if P == 0 or n == 0:
            return 0.0
        if r == 0:
            return P / n
        return P * r / (1 - (1 + r) ** -n)

    @property
    def partner_payment(self) -> float:
        if self.partner_tenor_seasons == 0:
            return 0.0
        return self.partner_principal / self.partner_tenor_seasons

    @property
    def total_interest(self) -> float:
        return self.lease_payment * self.lease_tenor_seasons - self.lease_principal

    @property
    def total_repaid(self) -> float:
        return self.lease_payment * self.lease_tenor_seasons + self.partner_principal

    def debt_service(self, horizon: int) -> List[float]:
        """What the owner pays out in each season, season 1 to `horizon`."""
        out = []
        for season in range(1, horizon + 1):
            s = season - self.grace_seasons
            pay = 0.0
            if 1 <= s <= self.lease_tenor_seasons:
                pay += self.lease_payment
            if 1 <= s <= self.partner_tenor_seasons:
                pay += self.partner_payment
            out.append(pay)
        return out

    def schedule_table(self, horizon: int = 6) -> pd.DataFrame:
        """A readable repayment schedule, for the proposal and for the lessor."""
        rows = []
        lease_bal, partner_bal = self.lease_principal, self.partner_principal
        for season in range(1, horizon + 1):
            s = season - self.grace_seasons
            lease_pay = self.lease_payment if 1 <= s <= self.lease_tenor_seasons else 0.0
            interest = lease_bal * self.lease_rate if lease_pay else 0.0
            principal = lease_pay - interest
            lease_bal = max(lease_bal - principal, 0.0)

            partner_pay = self.partner_payment if 1 <= s <= self.partner_tenor_seasons else 0.0
            partner_bal = max(partner_bal - partner_pay, 0.0)

            rows.append({
                "season": season,
                "lease_payment": lease_pay,
                "of_which_interest": interest,
                "lease_balance": lease_bal,
                "partner_payment": partner_pay,
                "partner_balance": partner_bal,
                "total_paid": lease_pay + partner_pay,
            })
        return pd.DataFrame(rows)

    def summary(self) -> dict:
        return {
            "machine_price": self.machine_price,
            "youth_equity": self.youth_equity,
            "partner_principal": self.partner_principal,
            "lease_principal": self.lease_principal,
            "lease_payment_per_season": self.lease_payment,
            "partner_payment_per_season": self.partner_payment,
            "total_interest": self.total_interest,
            "total_repaid_by_owner": self.total_repaid,
            "cost_of_capital_pct_of_price": 100 * self.total_interest / self.machine_price,
        }


# --------------------------------------------------------------------------- #
#  Owner wealth with financing applied
# --------------------------------------------------------------------------- #
def wealth_path_financed(horizon: int, season_net_fn, plan: FinancePlan) -> List[float]:
    """
    Cumulative cash the owner holds when debt service is deducted.

    `season_net_fn(age)` returns the owner's operating income in season `age`,
    before any financing cost.
    """
    service = plan.debt_service(horizon)
    cum, out = 0.0, []
    for age in range(1, horizon + 1):
        cum += season_net_fn(age) - service[age - 1]
        out.append(cum)
    return out


def seasons_to_threshold(season_net_fn, plan: FinancePlan,
                         threshold: float = 1_000_000.0, cap: int = 40) -> int | None:
    for i, w in enumerate(wealth_path_financed(cap, season_net_fn, plan), start=1):
        if w >= threshold:
            return i
    return None
