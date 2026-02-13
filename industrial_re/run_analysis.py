#!/usr/bin/env python3
"""
Run sample industrial real estate analyses.

Usage:
    python -m industrial_re.run_analysis
"""

from industrial_re.model import IndustrialProperty, ProForma


def fmt(val, prefix="$", suffix="", decimals=0):
    if val is None:
        return "N/A"
    if prefix == "$":
        return f"${val:,.{decimals}f}{suffix}"
    return f"{val:,.{decimals}f}{suffix}"


def print_header(title):
    width = 70
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_summary(pf: ProForma):
    s = pf.summary()

    print_header(f"INVESTMENT SUMMARY: {s['property']}")

    print(f"\n  Property Type:          {s['type'].title()}")
    print(f"  Square Feet:            {s['square_feet']:,.0f} SF")
    print(f"  Purchase Price:         {fmt(s['purchase_price'])}")
    print(f"  Price / SF:             {fmt(s['price_per_sf'], decimals=2)}")
    print(f"  Total Acquisition Cost: {fmt(s['total_acquisition_cost'])}")
    print(f"  Loan Amount:            {fmt(s['loan_amount'])}")
    print(f"  Equity Required:        {fmt(s['equity_required'])}")

    print(f"\n  --- Returns ---")
    print(f"  Going-In Cap Rate:      {fmt(s['going_in_cap_rate'], prefix='', suffix='%', decimals=2)}")
    print(f"  Yield on Cost:          {fmt(s['yield_on_cost'], prefix='', suffix='%', decimals=2)}")
    print(f"  Year 1 Cash-on-Cash:    {fmt(s['year_1_cash_on_cash'], prefix='', suffix='%', decimals=2)}")
    print(f"  Avg Cash-on-Cash:       {fmt(s['avg_cash_on_cash'], prefix='', suffix='%', decimals=2)}")
    print(f"  Year 1 DSCR:            {fmt(s['year_1_dscr'], prefix='', suffix='x', decimals=2)}")
    print(f"  Levered IRR:            {fmt(s['levered_irr'], prefix='', suffix='%', decimals=2)}")
    print(f"  Unlevered IRR:          {fmt(s['unlevered_irr'], prefix='', suffix='%', decimals=2)}")
    print(f"  Equity Multiple:        {fmt(s['equity_multiple'], prefix='', suffix='x', decimals=2)}")

    print(f"\n  --- Disposition (Year {s['hold_years']}) ---")
    print(f"  Exit Cap Rate:          {fmt(s['exit_cap_rate'], prefix='', suffix='%', decimals=1)}")
    print(f"  Projected Sale Price:   {fmt(s['projected_sale_price'])}")
    print(f"  Net Sale Proceeds:      {fmt(s['net_sale_proceeds'])}")


def print_proforma(pf: ProForma):
    cf = pf.cashflows
    p = pf.prop

    print(f"\n  {'Year':>4}  {'Base Rent':>12}  {'EGI':>12}  {'NOI':>12}  {'Debt Svc':>12}  {'CFADS':>12}  {'CoC%':>7}  {'DSCR':>6}")
    print(f"  {'----':>4}  {'--------':>12}  {'---':>12}  {'---':>12}  {'--------':>12}  {'-----':>12}  {'----':>7}  {'----':>6}")

    for r in cf:
        yr = r["year"]
        coc = pf.cash_on_cash(yr)
        dscr = pf.dscr(yr)
        print(
            f"  {yr:>4}  "
            f"${r['base_rent']:>11,.0f}  "
            f"${r['effective_gross_income']:>11,.0f}  "
            f"${r['noi']:>11,.0f}  "
            f"${r['debt_service']:>11,.0f}  "
            f"${r['cf_after_debt']:>11,.0f}  "
            f"{coc:>6.2f}%  "
            f"{dscr:>5.2f}x"
        )


def print_sensitivity(pf: ProForma):
    grid = pf.sensitivity()
    exit_caps = sorted(next(iter(grid.values())).keys())

    print(f"\n  IRR Sensitivity: Vacancy % (rows) vs Exit Cap % (cols)\n")
    header = f"  {'Vac%':>6}"
    for ec in exit_caps:
        header += f"  {ec:>7.1f}%"
    print(header)
    print(f"  {'------':>6}" + "  --------" * len(exit_caps))

    for vac in sorted(grid.keys()):
        row = f"  {vac:>5.0f}%"
        for ec in exit_caps:
            irr_val = grid[vac][ec]
            if irr_val is not None:
                row += f"  {irr_val:>7.2f}%"
            else:
                row += f"  {'N/A':>8}"
        print(row)


# ======================================================================
# Sample Properties
# ======================================================================

def sample_warehouse():
    """50,000 SF Class A warehouse in Dallas-Fort Worth."""
    return IndustrialProperty(
        name="DFW Logistics Center",
        property_type="warehouse",
        address="1200 Industrial Blvd, Dallas, TX",
        square_feet=50_000,
        land_acres=3.5,
        year_built=2019,
        clear_height_ft=32,
        dock_doors=8,
        drive_in_doors=2,
        office_pct=5.0,
        parking_spaces=40,
        # Acquisition
        purchase_price=5_500_000,
        closing_cost_pct=2.0,
        capex_at_close=50_000,
        # Financing
        ltv_pct=65,
        interest_rate_pct=6.25,
        amortization_years=25,
        loan_term_years=10,
        interest_only_years=0,
        # Revenue
        rent_per_sf=8.50,
        rent_escalation_pct=3.0,
        vacancy_pct=5.0,
        credit_loss_pct=1.0,
        other_income=12_000,
        other_income_growth_pct=2.0,
        expense_reimbursement_pct=95.0,
        # Opex
        tax_per_sf=1.10,
        insurance_per_sf=0.35,
        maintenance_per_sf=0.50,
        management_pct=3.0,
        general_admin_per_sf=0.10,
        utilities_per_sf=0.15,
        opex_growth_pct=2.5,
        # Reserves
        capex_reserve_per_sf=0.25,
        ti_reserve_per_sf=0.50,
        lc_reserve_per_sf=0.25,
        # Exit
        hold_years=10,
        exit_cap_rate_pct=6.75,
        selling_cost_pct=2.0,
    )


def sample_distribution():
    """120,000 SF distribution center in Atlanta."""
    return IndustrialProperty(
        name="Atlanta Distribution Hub",
        property_type="distribution",
        address="450 Logistics Pkwy, Atlanta, GA",
        square_feet=120_000,
        land_acres=8.0,
        year_built=2021,
        clear_height_ft=36,
        dock_doors=20,
        drive_in_doors=4,
        office_pct=3.0,
        parking_spaces=80,
        # Acquisition
        purchase_price=14_400_000,
        closing_cost_pct=1.5,
        capex_at_close=100_000,
        # Financing
        ltv_pct=60,
        interest_rate_pct=6.0,
        amortization_years=25,
        loan_term_years=10,
        interest_only_years=2,
        # Revenue
        rent_per_sf=7.25,
        rent_escalation_pct=3.0,
        vacancy_pct=3.0,
        credit_loss_pct=0.5,
        other_income=24_000,
        other_income_growth_pct=2.0,
        expense_reimbursement_pct=98.0,
        # Opex
        tax_per_sf=0.95,
        insurance_per_sf=0.30,
        maintenance_per_sf=0.40,
        management_pct=2.5,
        general_admin_per_sf=0.08,
        utilities_per_sf=0.10,
        opex_growth_pct=2.5,
        # Reserves
        capex_reserve_per_sf=0.20,
        ti_reserve_per_sf=0.40,
        lc_reserve_per_sf=0.20,
        # Exit
        hold_years=7,
        exit_cap_rate_pct=6.25,
        selling_cost_pct=1.5,
    )


def sample_manufacturing():
    """75,000 SF manufacturing facility in Indianapolis."""
    return IndustrialProperty(
        name="Indy Manufacturing Plant",
        property_type="manufacturing",
        address="800 Factory Rd, Indianapolis, IN",
        square_feet=75_000,
        land_acres=5.0,
        year_built=2005,
        clear_height_ft=24,
        dock_doors=6,
        drive_in_doors=3,
        office_pct=10.0,
        parking_spaces=60,
        # Acquisition
        purchase_price=6_000_000,
        closing_cost_pct=2.5,
        capex_at_close=200_000,
        # Financing
        ltv_pct=60,
        interest_rate_pct=6.75,
        amortization_years=20,
        loan_term_years=10,
        interest_only_years=0,
        # Revenue
        rent_per_sf=6.00,
        rent_escalation_pct=2.5,
        vacancy_pct=7.0,
        credit_loss_pct=1.5,
        other_income=8_000,
        other_income_growth_pct=2.0,
        expense_reimbursement_pct=90.0,
        # Opex
        tax_per_sf=1.00,
        insurance_per_sf=0.45,
        maintenance_per_sf=0.75,
        management_pct=4.0,
        general_admin_per_sf=0.15,
        utilities_per_sf=0.30,
        opex_growth_pct=3.0,
        # Reserves
        capex_reserve_per_sf=0.35,
        ti_reserve_per_sf=0.75,
        lc_reserve_per_sf=0.30,
        # Exit
        hold_years=10,
        exit_cap_rate_pct=7.50,
        selling_cost_pct=2.5,
    )


def main():
    properties = [sample_warehouse(), sample_distribution(), sample_manufacturing()]

    for prop in properties:
        pf = ProForma(prop)

        print_summary(pf)
        print(f"\n  --- {prop.hold_years}-Year Pro Forma ---")
        print_proforma(pf)
        print(f"\n  --- Sensitivity Analysis ---")
        print_sensitivity(pf)
        print()


if __name__ == "__main__":
    main()
