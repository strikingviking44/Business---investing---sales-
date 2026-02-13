"""Tests for the industrial real estate financial model."""

import pytest
from industrial_re.model import IndustrialProperty, ProForma, _compute_irr


# --- Fixtures ---

@pytest.fixture
def basic_property():
    """Simple property for predictable math."""
    return IndustrialProperty(
        name="Test Warehouse",
        property_type="warehouse",
        square_feet=100_000,
        purchase_price=10_000_000,
        closing_cost_pct=2.0,
        capex_at_close=0,
        ltv_pct=60,
        interest_rate_pct=6.0,
        amortization_years=25,
        loan_term_years=10,
        interest_only_years=0,
        rent_per_sf=8.00,
        rent_escalation_pct=3.0,
        vacancy_pct=5.0,
        credit_loss_pct=1.0,
        other_income=0,
        expense_reimbursement_pct=100.0,
        tax_per_sf=1.00,
        insurance_per_sf=0.30,
        maintenance_per_sf=0.50,
        management_pct=3.0,
        general_admin_per_sf=0.10,
        utilities_per_sf=0.10,
        opex_growth_pct=2.5,
        capex_reserve_per_sf=0.25,
        ti_reserve_per_sf=0.50,
        lc_reserve_per_sf=0.25,
        hold_years=10,
        exit_cap_rate_pct=7.0,
        selling_cost_pct=2.0,
    )


@pytest.fixture
def all_cash_property():
    """No debt for simpler return calculations."""
    return IndustrialProperty(
        name="All Cash Deal",
        property_type="warehouse",
        square_feet=50_000,
        purchase_price=5_000_000,
        closing_cost_pct=0,
        capex_at_close=0,
        ltv_pct=0,
        interest_rate_pct=0,
        rent_per_sf=10.00,
        rent_escalation_pct=0,
        vacancy_pct=0,
        credit_loss_pct=0,
        other_income=0,
        expense_reimbursement_pct=100.0,
        tax_per_sf=1.00,
        insurance_per_sf=0.50,
        maintenance_per_sf=0.50,
        management_pct=0,
        general_admin_per_sf=0,
        utilities_per_sf=0,
        opex_growth_pct=0,
        capex_reserve_per_sf=0,
        ti_reserve_per_sf=0,
        lc_reserve_per_sf=0,
        hold_years=5,
        exit_cap_rate_pct=8.0,
        selling_cost_pct=0,
    )


# --- Property Tests ---

class TestIndustrialProperty:
    def test_total_acquisition_cost(self, basic_property):
        # 10M + 2% closing = 10.2M
        assert basic_property.total_acquisition_cost == 10_200_000

    def test_loan_amount(self, basic_property):
        # 60% of 10M
        assert basic_property.loan_amount == 6_000_000

    def test_equity_required(self, basic_property):
        # 10.2M total - 6M loan = 4.2M
        assert basic_property.equity_required == 4_200_000

    def test_price_per_sf(self, basic_property):
        # 10M / 100K SF
        assert basic_property.price_per_sf == 100.0

    def test_all_cash_no_loan(self, all_cash_property):
        assert all_cash_property.loan_amount == 0
        assert all_cash_property.equity_required == 5_000_000


# --- Pro Forma Tests ---

class TestProForma:
    def test_year_count(self, basic_property):
        pf = ProForma(basic_property)
        assert len(pf.cashflows) == 10

    def test_year_1_base_rent(self, basic_property):
        pf = ProForma(basic_property)
        # $8/SF * 100K SF = $800K
        assert pf.year(1)["base_rent"] == 800_000.0

    def test_year_2_rent_escalation(self, basic_property):
        pf = ProForma(basic_property)
        # $800K * 1.03 = $824K
        assert pf.year(2)["base_rent"] == 824_000.0

    def test_vacancy_deduction(self, basic_property):
        pf = ProForma(basic_property)
        # 5% of $800K = $40K
        assert pf.year(1)["vacancy"] == 40_000.0

    def test_credit_loss_deduction(self, basic_property):
        pf = ProForma(basic_property)
        # 1% of $800K = $8K
        assert pf.year(1)["credit_loss"] == 8_000.0

    def test_egi_calculation(self, basic_property):
        pf = ProForma(basic_property)
        yr1 = pf.year(1)
        expected_egi = yr1["base_rent"] - yr1["vacancy"] - yr1["credit_loss"] + yr1["other_income"]
        assert yr1["effective_gross_income"] == expected_egi

    def test_noi_positive(self, basic_property):
        pf = ProForma(basic_property)
        assert pf.year(1)["noi"] > 0

    def test_noi_grows_over_time(self, basic_property):
        pf = ProForma(basic_property)
        # Rent grows at 3%, opex at 2.5%, so NOI should generally grow
        assert pf.year(5)["noi"] > pf.year(1)["noi"]

    def test_debt_service_constant(self, basic_property):
        pf = ProForma(basic_property)
        # No IO period, so debt service should be the same every year
        ds1 = pf.year(1)["debt_service"]
        ds5 = pf.year(5)["debt_service"]
        assert abs(ds1 - ds5) < 0.01

    def test_no_debt_service_all_cash(self, all_cash_property):
        pf = ProForma(all_cash_property)
        assert pf.year(1)["debt_service"] == 0

    def test_cf_after_debt_equals_cf_before_debt_when_all_cash(self, all_cash_property):
        pf = ProForma(all_cash_property)
        yr1 = pf.year(1)
        assert yr1["cf_after_debt"] == yr1["cf_before_debt"]


# --- NOI detail (all-cash, no escalation for easy math) ---

class TestSimpleNOI:
    def test_noi_all_cash_flat(self, all_cash_property):
        pf = ProForma(all_cash_property)
        yr1 = pf.year(1)
        # Revenue: $10/SF * 50K = $500K, no vacancy/credit loss
        assert yr1["base_rent"] == 500_000
        assert yr1["effective_gross_income"] == 500_000
        # Opex: (1.00 + 0.50 + 0.50) * 50K = $100K, management 0%
        assert yr1["total_opex"] == 100_000
        # Reimbursement: 100% of $100K = $100K
        assert yr1["expense_reimbursement"] == 100_000
        # NOI = EGI + reimbursement - opex = 500K + 100K - 100K = 500K
        assert yr1["noi"] == 500_000


# --- Return Metrics Tests ---

class TestReturnMetrics:
    def test_going_in_cap_rate(self, all_cash_property):
        pf = ProForma(all_cash_property)
        # NOI $500K / $5M = 10%
        assert pf.going_in_cap_rate() == 10.0

    def test_cash_on_cash_all_cash(self, all_cash_property):
        pf = ProForma(all_cash_property)
        # CFADS = NOI (no debt, no reserves) = $500K
        # Equity = $5M
        # CoC = 500K / 5M = 10%
        assert pf.cash_on_cash(1) == 10.0

    def test_yield_on_cost(self, all_cash_property):
        pf = ProForma(all_cash_property)
        # NOI $500K / $5M acq cost = 10%
        assert pf.yield_on_cost() == 10.0

    def test_dscr_no_debt(self, all_cash_property):
        pf = ProForma(all_cash_property)
        assert pf.dscr(1) == 0.0  # No debt service

    def test_dscr_with_debt(self, basic_property):
        pf = ProForma(basic_property)
        dscr = pf.dscr(1)
        assert dscr > 1.0  # Should cover debt service

    def test_equity_multiple_positive(self, basic_property):
        pf = ProForma(basic_property)
        em = pf.equity_multiple()
        assert em > 1.0  # Should return more than invested

    def test_levered_irr_exists(self, basic_property):
        pf = ProForma(basic_property)
        irr = pf.irr()
        assert irr is not None
        assert irr > 0

    def test_unlevered_irr_exists(self, basic_property):
        pf = ProForma(basic_property)
        irr = pf.unlevered_irr()
        assert irr is not None
        assert irr > 0

    def test_levered_irr_exceeds_unlevered(self, basic_property):
        """Positive leverage: levered IRR should beat unlevered."""
        pf = ProForma(basic_property)
        assert pf.irr() > pf.unlevered_irr()

    def test_rent_schedule_length(self, basic_property):
        pf = ProForma(basic_property)
        schedule = pf.rent_per_sf_schedule()
        assert len(schedule) == 10


# --- Disposition Tests ---

class TestDisposition:
    def test_disposition_keys(self, basic_property):
        pf = ProForma(basic_property)
        d = pf.disposition()
        assert "sale_price" in d
        assert "net_sale_proceeds" in d
        assert "loan_payoff" in d

    def test_disposition_all_cash_no_loan_payoff(self, all_cash_property):
        pf = ProForma(all_cash_property)
        d = pf.disposition()
        assert d["loan_payoff"] == 0

    def test_sale_price_formula(self, all_cash_property):
        pf = ProForma(all_cash_property)
        d = pf.disposition()
        # No escalation, so projected NOI = $500K, exit cap 8%
        # Sale price = 500K / 0.08 = $6.25M
        assert d["sale_price"] == 6_250_000.0

    def test_net_proceeds_all_cash(self, all_cash_property):
        pf = ProForma(all_cash_property)
        d = pf.disposition()
        # No selling costs (0%), no loan
        assert d["net_sale_proceeds"] == d["sale_price"]


# --- Interest-Only Period Tests ---

class TestInterestOnly:
    def test_io_debt_service_lower(self):
        prop = IndustrialProperty(
            square_feet=100_000,
            purchase_price=10_000_000,
            ltv_pct=60,
            interest_rate_pct=6.0,
            amortization_years=25,
            interest_only_years=3,
            rent_per_sf=8.0,
            tax_per_sf=1.0,
            insurance_per_sf=0.3,
            maintenance_per_sf=0.5,
            hold_years=5,
            exit_cap_rate_pct=7.0,
        )
        pf = ProForma(prop)
        # IO years should have lower debt service than amortizing years
        io_ds = pf.year(1)["debt_service"]
        amort_ds = pf.year(4)["debt_service"]
        assert io_ds < amort_ds


# --- Sensitivity Tests ---

class TestSensitivity:
    def test_sensitivity_grid_structure(self, basic_property):
        pf = ProForma(basic_property)
        grid = pf.sensitivity(
            vacancy_range=(5, 10),
            exit_cap_range=(6.0, 7.0),
        )
        assert 5 in grid
        assert 10 in grid
        assert 6.0 in grid[5]
        assert 7.0 in grid[5]

    def test_lower_exit_cap_better_irr(self, basic_property):
        pf = ProForma(basic_property)
        grid = pf.sensitivity(
            vacancy_range=(5,),
            exit_cap_range=(6.0, 8.0),
        )
        # Lower exit cap = higher sale price = better IRR
        assert grid[5][6.0] > grid[5][8.0]

    def test_sensitivity_restores_originals(self, basic_property):
        pf = ProForma(basic_property)
        original_vac = basic_property.vacancy_pct
        original_exit = basic_property.exit_cap_rate_pct
        pf.sensitivity(vacancy_range=(3, 10), exit_cap_range=(6.0, 8.0))
        assert basic_property.vacancy_pct == original_vac
        assert basic_property.exit_cap_rate_pct == original_exit


# --- Summary Tests ---

class TestSummary:
    def test_summary_has_all_keys(self, basic_property):
        pf = ProForma(basic_property)
        s = pf.summary()
        expected_keys = [
            "property", "type", "square_feet", "purchase_price",
            "price_per_sf", "total_acquisition_cost", "loan_amount",
            "equity_required", "year_1_noi", "going_in_cap_rate",
            "yield_on_cost", "year_1_cash_on_cash", "avg_cash_on_cash",
            "year_1_dscr", "levered_irr", "unlevered_irr",
            "equity_multiple", "exit_cap_rate", "projected_sale_price",
            "net_sale_proceeds", "hold_years",
        ]
        for key in expected_keys:
            assert key in s, f"Missing key: {key}"


# --- IRR Helper Tests ---

class TestIRRHelper:
    def test_known_irr(self):
        # Invest $100, get $110 back in 1 year => 10% IRR
        result = _compute_irr([-100, 110])
        assert abs(result - 10.0) < 0.1

    def test_multi_year_irr(self):
        # Invest $1000, get $200/yr for 6 years => ~5.5% IRR
        cfs = [-1000, 200, 200, 200, 200, 200, 200]
        result = _compute_irr(cfs)
        assert result is not None
        assert 5.0 < result < 6.0

    def test_negative_irr(self):
        # Invest $1000, get back only $800
        result = _compute_irr([-1000, 800])
        assert result is not None
        assert result < 0
