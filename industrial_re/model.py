"""
Industrial Real Estate Financial Model

Supports warehouse, distribution, manufacturing, and flex/R&D properties.
Generates multi-year pro forma projections with full investment return analysis.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IndustrialProperty:
    """Core property assumptions and inputs."""

    # --- Property ---
    name: str = "Industrial Property"
    property_type: str = "warehouse"  # warehouse, distribution, manufacturing, flex
    address: str = ""
    square_feet: float = 0
    land_acres: float = 0
    year_built: int = 0
    clear_height_ft: float = 0
    dock_doors: int = 0
    drive_in_doors: int = 0
    office_pct: float = 0.0  # % of SF that is office finish
    parking_spaces: int = 0

    # --- Acquisition ---
    purchase_price: float = 0
    closing_cost_pct: float = 2.0  # % of purchase price
    capex_at_close: float = 0  # immediate renovation / TI

    # --- Financing ---
    ltv_pct: float = 65.0
    interest_rate_pct: float = 6.5
    amortization_years: int = 25
    loan_term_years: int = 10
    interest_only_years: int = 0

    # --- Revenue ---
    rent_per_sf: float = 0  # annual base rent / SF (NNN)
    rent_escalation_pct: float = 3.0  # annual bump
    vacancy_pct: float = 5.0
    credit_loss_pct: float = 1.0
    other_income: float = 0  # antenna, parking, storage, etc.
    other_income_growth_pct: float = 2.0

    # --- Reimbursements (NNN) ---
    expense_reimbursement_pct: float = 95.0  # % of opex recovered from tenants

    # --- Operating Expenses (per SF unless noted) ---
    tax_per_sf: float = 0
    insurance_per_sf: float = 0
    maintenance_per_sf: float = 0
    management_pct: float = 3.0  # % of EGI
    general_admin_per_sf: float = 0
    utilities_per_sf: float = 0  # landlord-paid portion
    opex_growth_pct: float = 2.5

    # --- Reserves ---
    capex_reserve_per_sf: float = 0.25
    ti_reserve_per_sf: float = 0.50
    lc_reserve_per_sf: float = 0.25

    # --- Disposition ---
    hold_years: int = 10
    exit_cap_rate_pct: float = 7.0
    selling_cost_pct: float = 2.0  # broker + legal at sale

    # --- Computed helpers ---
    @property
    def total_acquisition_cost(self) -> float:
        closing = self.purchase_price * self.closing_cost_pct / 100
        return self.purchase_price + closing + self.capex_at_close

    @property
    def loan_amount(self) -> float:
        return self.purchase_price * self.ltv_pct / 100

    @property
    def equity_required(self) -> float:
        return self.total_acquisition_cost - self.loan_amount

    @property
    def price_per_sf(self) -> float:
        return self.purchase_price / self.square_feet if self.square_feet else 0


class ProForma:
    """Multi-year pro forma engine."""

    def __init__(self, prop: IndustrialProperty):
        self.prop = prop
        self._years: int = prop.hold_years
        self._cf: list[dict] = []
        self._build()

    # ------------------------------------------------------------------
    # Build year-by-year projections
    # ------------------------------------------------------------------
    def _build(self):
        p = self.prop
        self._cf = []

        for yr in range(1, self._years + 1):
            row: dict = {"year": yr}

            # --- Revenue ---
            esc = (1 + p.rent_escalation_pct / 100) ** (yr - 1)
            base_rent = p.rent_per_sf * esc * p.square_feet
            row["base_rent"] = round(base_rent, 2)

            vacancy = base_rent * p.vacancy_pct / 100
            credit_loss = base_rent * p.credit_loss_pct / 100
            row["vacancy"] = round(vacancy, 2)
            row["credit_loss"] = round(credit_loss, 2)

            other = p.other_income * (1 + p.other_income_growth_pct / 100) ** (yr - 1)
            row["other_income"] = round(other, 2)

            egi = base_rent - vacancy - credit_loss + other
            row["effective_gross_income"] = round(egi, 2)

            # --- Operating Expenses ---
            opex_esc = (1 + p.opex_growth_pct / 100) ** (yr - 1)
            taxes = p.tax_per_sf * opex_esc * p.square_feet
            insurance = p.insurance_per_sf * opex_esc * p.square_feet
            maintenance = p.maintenance_per_sf * opex_esc * p.square_feet
            ga = p.general_admin_per_sf * opex_esc * p.square_feet
            utilities = p.utilities_per_sf * opex_esc * p.square_feet
            management = egi * p.management_pct / 100

            total_opex = taxes + insurance + maintenance + management + ga + utilities
            row["taxes"] = round(taxes, 2)
            row["insurance"] = round(insurance, 2)
            row["maintenance"] = round(maintenance, 2)
            row["management"] = round(management, 2)
            row["general_admin"] = round(ga, 2)
            row["utilities"] = round(utilities, 2)
            row["total_opex"] = round(total_opex, 2)

            # --- NNN Reimbursements ---
            reimbursable = taxes + insurance + maintenance + ga + utilities
            reimbursement = reimbursable * p.expense_reimbursement_pct / 100
            row["expense_reimbursement"] = round(reimbursement, 2)

            # --- NOI ---
            noi = egi + reimbursement - total_opex
            row["noi"] = round(noi, 2)

            # --- Reserves ---
            capex_res = p.capex_reserve_per_sf * p.square_feet * opex_esc
            ti_res = p.ti_reserve_per_sf * p.square_feet * opex_esc
            lc_res = p.lc_reserve_per_sf * p.square_feet * opex_esc
            total_reserves = capex_res + ti_res + lc_res
            row["capex_reserve"] = round(capex_res, 2)
            row["ti_reserve"] = round(ti_res, 2)
            row["lc_reserve"] = round(lc_res, 2)
            row["total_reserves"] = round(total_reserves, 2)

            # --- Cash Flow Before Debt ---
            cfbds = noi - total_reserves
            row["cf_before_debt"] = round(cfbds, 2)

            # --- Debt Service ---
            ds = self._annual_debt_service(yr)
            row["debt_service"] = round(ds, 2)

            # --- Cash Flow After Debt ---
            cfads = cfbds - ds
            row["cf_after_debt"] = round(cfads, 2)

            self._cf.append(row)

    # ------------------------------------------------------------------
    # Debt calculations
    # ------------------------------------------------------------------
    def _annual_debt_service(self, year: int) -> float:
        p = self.prop
        if p.loan_amount == 0:
            return 0.0
        r = p.interest_rate_pct / 100 / 12  # monthly rate
        if year <= p.interest_only_years:
            return p.loan_amount * r * 12
        n = p.amortization_years * 12
        if r == 0:
            monthly = p.loan_amount / n
        else:
            monthly = p.loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)
        return monthly * 12

    def _loan_balance_at_year(self, year: int) -> float:
        """Outstanding principal balance at end of given year."""
        p = self.prop
        if p.loan_amount == 0:
            return 0.0
        r = p.interest_rate_pct / 100 / 12
        n = p.amortization_years * 12

        if r == 0:
            monthly_pmt = p.loan_amount / n
        else:
            monthly_pmt = p.loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

        balance = p.loan_amount
        for m in range(1, year * 12 + 1):
            yr_of_month = (m - 1) // 12 + 1
            if yr_of_month <= p.interest_only_years:
                # IO period: no principal reduction
                continue
            interest = balance * r
            principal = monthly_pmt - interest
            balance -= principal
        return max(balance, 0)

    # ------------------------------------------------------------------
    # Disposition / reversion
    # ------------------------------------------------------------------
    def disposition(self) -> dict:
        p = self.prop
        final_noi = self._cf[-1]["noi"]
        # Project next year NOI for exit valuation
        next_yr_noi = final_noi * (1 + p.rent_escalation_pct / 100)
        sale_price = next_yr_noi / (p.exit_cap_rate_pct / 100) if p.exit_cap_rate_pct else 0
        selling_costs = sale_price * p.selling_cost_pct / 100
        loan_balance = self._loan_balance_at_year(p.hold_years)
        net_proceeds = sale_price - selling_costs - loan_balance
        return {
            "exit_year": p.hold_years,
            "projected_noi": round(next_yr_noi, 2),
            "exit_cap_rate_pct": p.exit_cap_rate_pct,
            "sale_price": round(sale_price, 2),
            "selling_costs": round(selling_costs, 2),
            "loan_payoff": round(loan_balance, 2),
            "net_sale_proceeds": round(net_proceeds, 2),
        }

    # ------------------------------------------------------------------
    # Return metrics
    # ------------------------------------------------------------------
    def going_in_cap_rate(self) -> float:
        """Year 1 NOI / Purchase Price."""
        if self.prop.purchase_price == 0:
            return 0.0
        return round(self._cf[0]["noi"] / self.prop.purchase_price * 100, 2)

    def cash_on_cash(self, year: int = 1) -> float:
        """Cash-on-cash return for a given year."""
        eq = self.prop.equity_required
        if eq == 0:
            return 0.0
        idx = min(year, len(self._cf)) - 1
        return round(self._cf[idx]["cf_after_debt"] / eq * 100, 2)

    def average_cash_on_cash(self) -> float:
        eq = self.prop.equity_required
        if eq == 0:
            return 0.0
        total = sum(r["cf_after_debt"] for r in self._cf)
        return round(total / len(self._cf) / eq * 100, 2)

    def dscr(self, year: int = 1) -> float:
        """Debt service coverage ratio for a given year."""
        idx = min(year, len(self._cf)) - 1
        ds = self._cf[idx]["debt_service"]
        if ds == 0:
            return 0.0
        return round(self._cf[idx]["noi"] / ds, 2)

    def equity_multiple(self) -> float:
        """Total cash returned / equity invested."""
        eq = self.prop.equity_required
        if eq == 0:
            return 0.0
        total_cf = sum(r["cf_after_debt"] for r in self._cf)
        disp = self.disposition()
        total_return = total_cf + disp["net_sale_proceeds"]
        return round(total_return / eq, 2)

    def irr(self) -> Optional[float]:
        """Levered IRR using Newton's method."""
        eq = self.prop.equity_required
        if eq == 0:
            return None
        disp = self.disposition()
        cashflows = [-eq]
        for i, r in enumerate(self._cf):
            cf = r["cf_after_debt"]
            if i == len(self._cf) - 1:
                cf += disp["net_sale_proceeds"]
            cashflows.append(cf)
        return _compute_irr(cashflows)

    def unlevered_irr(self) -> Optional[float]:
        """Unlevered (property-level) IRR."""
        acq = self.prop.total_acquisition_cost
        if acq == 0:
            return None
        disp = self.disposition()
        sale_gross = disp["sale_price"] - disp["selling_costs"]
        cashflows = [-acq]
        for i, r in enumerate(self._cf):
            cf = r["cf_before_debt"]
            if i == len(self._cf) - 1:
                cf += sale_gross
            cashflows.append(cf)
        return _compute_irr(cashflows)

    def yield_on_cost(self) -> float:
        """Stabilized NOI / total acquisition cost."""
        acq = self.prop.total_acquisition_cost
        if acq == 0:
            return 0.0
        return round(self._cf[0]["noi"] / acq * 100, 2)

    def rent_per_sf_schedule(self) -> list[dict]:
        """Show effective rent/SF each year."""
        return [
            {"year": r["year"], "rent_per_sf": round(r["base_rent"] / self.prop.square_feet, 2)}
            for r in self._cf
        ]

    # ------------------------------------------------------------------
    # Sensitivity analysis
    # ------------------------------------------------------------------
    def sensitivity(
        self,
        vacancy_range: tuple = (3, 5, 7, 10),
        exit_cap_range: tuple = (5.5, 6.0, 6.5, 7.0, 7.5, 8.0),
    ) -> dict:
        """Run sensitivity on vacancy and exit cap rate, returning IRR grid."""
        original_vacancy = self.prop.vacancy_pct
        original_exit = self.prop.exit_cap_rate_pct
        grid = {}
        for vac in vacancy_range:
            row = {}
            for ecap in exit_cap_range:
                self.prop.vacancy_pct = vac
                self.prop.exit_cap_rate_pct = ecap
                self._build()
                computed_irr = self.irr()
                row[ecap] = computed_irr
            grid[vac] = row
        # Restore originals
        self.prop.vacancy_pct = original_vacancy
        self.prop.exit_cap_rate_pct = original_exit
        self._build()
        return grid

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def cashflows(self) -> list[dict]:
        return list(self._cf)

    def year(self, n: int) -> dict:
        return self._cf[n - 1]

    def summary(self) -> dict:
        p = self.prop
        d = self.disposition()
        return {
            "property": p.name,
            "type": p.property_type,
            "square_feet": p.square_feet,
            "purchase_price": p.purchase_price,
            "price_per_sf": round(p.price_per_sf, 2),
            "total_acquisition_cost": round(p.total_acquisition_cost, 2),
            "loan_amount": round(p.loan_amount, 2),
            "equity_required": round(p.equity_required, 2),
            "year_1_noi": self._cf[0]["noi"],
            "going_in_cap_rate": self.going_in_cap_rate(),
            "yield_on_cost": self.yield_on_cost(),
            "year_1_cash_on_cash": self.cash_on_cash(1),
            "avg_cash_on_cash": self.average_cash_on_cash(),
            "year_1_dscr": self.dscr(1),
            "levered_irr": self.irr(),
            "unlevered_irr": self.unlevered_irr(),
            "equity_multiple": self.equity_multiple(),
            "exit_cap_rate": p.exit_cap_rate_pct,
            "projected_sale_price": d["sale_price"],
            "net_sale_proceeds": d["net_sale_proceeds"],
            "hold_years": p.hold_years,
        }


# ------------------------------------------------------------------
# IRR helper (Newton-Raphson)
# ------------------------------------------------------------------
def _compute_irr(cashflows: list[float], guess: float = 0.10, tol: float = 1e-8, max_iter: int = 200) -> Optional[float]:
    """Compute IRR via Newton's method. Returns percentage or None."""
    rate = guess
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** t for t, cf in enumerate(cashflows))
        dnpv = sum(-t * cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows))
        if abs(dnpv) < 1e-14:
            return None
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tol:
            return round(new_rate * 100, 2)
        rate = new_rate
    return round(rate * 100, 2)
