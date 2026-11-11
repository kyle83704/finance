"""Unit tests for simulation engine."""

import unittest
from datetime import datetime
from src.models import ClientProfile, Account, IncomeStream, Expenses, ScenarioSettings
from src.simulator import ConversionSimulator
from src.tax_calculator import TaxCalculator


class TestConversionSimulator(unittest.TestCase):
    """Test simulation engine."""
    
    def setUp(self):
        self.client = ClientProfile(
            first_name="John",
            last_name="Doe",
            birth_year=1960,
            state_residence="ID",
            filing_status="single",
        )
        self.simulator = ConversionSimulator(self.client)
    
    def test_calculate_annual_income_single_stream(self):
        """Test annual income calculation."""
        income_streams = [
            IncomeStream(
                name="Social Security",
                income_type="Social Security",
                annual_amount=30000,
                start_age=67,
                end_age=100,
                growth_rate=0.02,
                tax_treatment="tax_free",
            )
        ]
        
        # Current client is 66 years old (2026 - 1960)
        # Age 67 next year (2027)
        income = self.simulator.calculate_annual_income(2027, income_streams)
        # $30,000 * 1.02 = $30,600
        self.assertAlmostEqual(income, 30600, delta=100)
    
    def test_calculate_annual_income_multiple_streams(self):
        """Test multiple income sources."""
        income_streams = [
            IncomeStream(
                name="SS",
                income_type="Social Security",
                annual_amount=30000,
                start_age=67,
                end_age=100,
            ),
            IncomeStream(
                name="Pension",
                income_type="Pension",
                annual_amount=20000,
                start_age=65,
                end_age=100,
            ),
        ]
        
        income = self.simulator.calculate_annual_income(2026, income_streams)
        # Both should be active (ages 66 and beyond)
        # SS starts at 67, so at 66 it's 0
        # Pension starts at 65, so at 66 it's $20,000
        self.assertEqual(income, 20000)
    
    def test_calculate_account_growth(self):
        """Test account balance calculation with growth."""
        balance = self.simulator.calculate_account_growth(
            balance=100000,
            growth_rate=0.07,
            years=1,
            annual_contribution=5000,
        )
        # ($100,000 + $5,000) * 1.07 = $112,350
        self.assertAlmostEqual(balance, 112350, delta=1)
    
    def test_calculate_account_growth_multiple_years(self):
        """Test growth over multiple years."""
        balance = self.simulator.calculate_account_growth(
            balance=100000,
            growth_rate=0.07,
            years=3,
            annual_contribution=0,
        )
        # $100,000 * 1.07^3 = $122,504.3
        self.assertAlmostEqual(balance, 122504, delta=10)
    
    def test_calculate_optimal_conversion_no_strategy(self):
        """Test optimal conversion with no specific strategy."""
        conversion = self.simulator._calculate_optimal_conversion(
            age=66,
            pretax_balance=500000,
            rmd_required=0,
            total_income=50000,
            annual_expenses=40000,
            scenario=ScenarioSettings(
                name="Test",
                start_year=2026,
                end_year=2055,
                target_objective="Maximize Net Worth",
            ),
            tax_year=2026,
        )
        # Should be 0 or small positive
        self.assertGreaterEqual(conversion, 0)
        self.assertLessEqual(conversion, 500000)
    
    def test_calculate_bracket_fill_amount_single(self):
        """Test calculating amount to fill current bracket."""
        amount = self.simulator._calculate_bracket_fill_amount(
            current_income=40000,
            scenario=ScenarioSettings(
                name="Test",
                start_year=2026,
                end_year=2055,
            ),
            tax_year=2026,
        )
        # Single filer, 2026 standard deduction $16,100
        # Current taxable = $40,000 - $16,100 = $23,900
        # The 12% bracket tops out at $50,400, so room = $26,500
        self.assertAlmostEqual(amount, 26500, delta=10)
    
    def test_calculate_max_before_irmaa_single(self):
        """Test maximum income before IRMAA triggers."""
        max_amount = self.simulator._calculate_max_before_irmaa(
            current_income=50000,
            filing_status="single",
        )
        # First 2026 IRMAA threshold for single = $109,000
        # Room = $109,000 - $50,000 = $59,000
        self.assertEqual(max_amount, 59000)
    
    def test_calculate_max_before_irmaa_at_threshold(self):
        """Test maximum when at IRMAA threshold."""
        max_amount = self.simulator._calculate_max_before_irmaa(
            current_income=109000,
            filing_status="single",
        )
        self.assertEqual(max_amount, 0)
    
    def test_calculate_max_before_irmaa_above_threshold(self):
        """Test maximum when already above threshold."""
        max_amount = self.simulator._calculate_max_before_irmaa(
            current_income=110000,
            filing_status="single",
        )
        self.assertEqual(max_amount, 0)
    
    def test_simulate_year_no_income(self):
        """Test year simulation with minimal setup."""
        accounts = {
            "IRA": Account(
                name="IRA",
                account_type="Traditional IRA",
                current_balance=200000,
                pretax_basis=200000,
                growth_rate=0.07,
            )
        }
        income_streams = []
        expenses = Expenses()
        
        scenario = ScenarioSettings(
            name="Test",
            start_year=2026,
            end_year=2055,
        )
        
        result = self.simulator.simulate_year(
            year=2026,
            age=66,
            accounts=accounts,
            income_streams=income_streams,
            expenses=expenses,
            scenario=scenario,
        )
        
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.age, 66)
        self.assertEqual(result.start_balance_pretax, 200000)
        self.assertGreaterEqual(result.recommended_conversion, 0)


class TestFullSimulation(unittest.TestCase):
    """Test complete simulation workflow."""
    
    def setUp(self):
        self.client = ClientProfile(
            first_name="Jane",
            last_name="Smith",
            birth_year=1960,
            state_residence="ID",
        )
        self.simulator = ConversionSimulator(self.client)
    
    def test_run_full_simulation(self):
        """Test full simulation run."""
        accounts = [
            Account(
                name="Traditional IRA",
                account_type="Traditional IRA",
                current_balance=300000,
                pretax_basis=300000,
                growth_rate=0.07,
            ),
            Account(
                name="Roth IRA",
                account_type="Roth IRA",
                current_balance=100000,
                growth_rate=0.07,
            ),
        ]
        
        income_streams = [
            IncomeStream(
                name="Social Security",
                income_type="Social Security",
                annual_amount=30000,
                start_age=67,
                end_age=100,
            )
        ]
        
        expenses = Expenses(housing=24000, utilities=3000, food=6000)
        
        scenario = ScenarioSettings(
            name="Test Scenario",
            start_year=2026,
            end_year=2030,
            target_objective="Maximize Roth Value",
        )
        
        strategy = self.simulator.run_full_simulation(
            scenario, accounts, income_streams, expenses
        )
        
        # Should have results for 5 years
        self.assertEqual(len(strategy.years), 5)
        
        # Check that values are reasonable
        self.assertGreater(strategy.final_net_worth, 0)
        self.assertGreater(strategy.final_roth_value, 0)


class TestScenarioIsolation(unittest.TestCase):
    """Accounts and scenario results must not leak between runs."""

    def setUp(self):
        current_year = datetime.now().year
        self.client = ClientProfile(
            first_name="Ada",
            last_name="Lovelace",
            birth_year=current_year - 60,
            state_residence="ID",
            filing_status="single",
        )
        self.simulator = ConversionSimulator(self.client)
        self.accounts = [
            Account(
                name="Traditional IRA",
                account_type="Traditional IRA",
                current_balance=100000,
                pretax_basis=100000,
                growth_rate=0.0,
            ),
            Account(
                name="Roth IRA",
                account_type="Roth IRA",
                current_balance=0.0,
                growth_rate=0.0,
            ),
        ]
        self.expenses = Expenses()

    def _scenario(self, name, target):
        year = datetime.now().year
        return ScenarioSettings(
            name=name,
            start_year=year,
            end_year=year,
            target_objective="Fixed Amount",
            annual_conversion_target=target,
            max_conversion_allowed=target,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )

    def test_input_accounts_are_not_mutated(self):
        strategy = self.simulator.run_full_simulation(
            self._scenario("Ten Thousand", 10000),
            self.accounts, [], self.expenses,
        )

        self.assertAlmostEqual(self.accounts[0].current_balance, 100000)
        self.assertAlmostEqual(strategy.years[0].start_balance_pretax, 100000)
        self.assertAlmostEqual(strategy.years[0].end_balance_pretax, 90000)
        self.assertAlmostEqual(strategy.years[0].end_balance_roth, 10000)

    def test_second_scenario_starts_from_original_balance(self):
        first = self.simulator.run_full_simulation(
            self._scenario("Small", 10000), self.accounts, [], self.expenses
        )
        second = self.simulator.run_full_simulation(
            self._scenario("Large", 50000), self.accounts, [], self.expenses
        )

        self.assertAlmostEqual(first.years[0].start_balance_pretax, 100000)
        self.assertAlmostEqual(second.years[0].start_balance_pretax, 100000)
        self.assertAlmostEqual(first.final_pretax_value, 90000)
        self.assertAlmostEqual(second.final_pretax_value, 50000)


class TestRMDHandling(unittest.TestCase):
    """RMDs are withdrawals, not voluntary Roth conversions."""

    def setUp(self):
        current_year = datetime.now().year
        self.client = ClientProfile(
            first_name="Grace",
            last_name="Hopper",
            birth_year=current_year - 73,
            state_residence="ID",
            filing_status="single",
        )
        self.simulator = ConversionSimulator(self.client)
        self.accounts = [
            Account(
                name="Traditional IRA",
                account_type="Traditional IRA",
                current_balance=530000,
                pretax_basis=530000,
                growth_rate=0.0,
            ),
            Account(
                name="Roth IRA",
                account_type="Roth IRA",
                current_balance=0.0,
                growth_rate=0.0,
            ),
            Account(
                name="Taxable Brokerage",
                account_type="Taxable Brokerage",
                current_balance=0.0,
                growth_rate=0.0,
            ),
        ]
        self.expenses = Expenses()

    def _scenario(self, target=0):
        year = datetime.now().year
        return ScenarioSettings(
            name="RMD Test",
            start_year=year,
            end_year=year,
            target_objective="Fixed Amount",
            annual_conversion_target=target,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )

    def test_rmd_is_withdrawn_and_not_counted_as_conversion(self):
        strategy = self.simulator.run_full_simulation(
            self._scenario(0), self.accounts, [], self.expenses
        )
        result = strategy.years[0]

        self.assertAlmostEqual(result.rmd_required, 530000 / 26.5, delta=1)
        self.assertEqual(result.recommended_conversion, 0.0)
        self.assertAlmostEqual(result.end_balance_pretax, 510000, delta=1)
        self.assertAlmostEqual(
            result.end_balance_taxable, 20000 - result.taxes_paid, delta=1
        )
        self.assertGreater(result.income_tax, 0)
        self.assertAlmostEqual(
            result.total_tax_paid,
            result.income_tax + result.conversion_tax + result.irmaa_impact,
        )
        self.assertAlmostEqual(
            result.beginning_assets + sum(e.amount for e in result.ledger),
            result.ending_assets,
        )
        self.assertIn("RMD", " ".join(result.notes))

    def test_conversion_capacity_is_calculated_after_the_rmd(self):
        strategy = self.simulator.run_full_simulation(
            self._scenario(1_000_000), self.accounts, [], self.expenses
        )
        result = strategy.years[0]

        self.assertAlmostEqual(result.rmd_required, 20000, delta=1)
        self.assertAlmostEqual(result.recommended_conversion, 510000, delta=1)
        self.assertAlmostEqual(result.end_balance_pretax, 0, delta=1)
        self.assertAlmostEqual(
            result.end_balance_roth,
            510000 - result.withholding_from_conversion,
            delta=1,
        )
        self.assertAlmostEqual(result.end_balance_taxable, 0, delta=1)
        self.assertGreater(result.conversion_tax, 0)
        self.assertGreater(result.total_tax_paid, result.income_tax)
        self.assertAlmostEqual(
            result.taxes_paid + result.taxes_unpaid, result.total_tax_paid,
            delta=1
        )

    def test_employer_401k_is_treated_as_pretax(self):
        accounts = [
            Account(
                name="Employer plan",
                account_type="Employer 401(k)",
                current_balance=530000,
                pretax_basis=530000,
                growth_rate=0.0,
            ),
            Account(
                name="Taxable Brokerage",
                account_type="Taxable Brokerage",
                current_balance=0.0,
                growth_rate=0.0,
            ),
        ]
        strategy = self.simulator.run_full_simulation(
            self._scenario(0), accounts, [], self.expenses
        )

        self.assertAlmostEqual(strategy.years[0].rmd_required, 20000, delta=1)
        self.assertAlmostEqual(strategy.final_pretax_value, 510000, delta=1)


class TestProRataBasis(unittest.TestCase):

    def test_non_deductible_basis_reduces_taxable_conversion(self):
        current_year = datetime.now().year
        client = ClientProfile(
            first_name="Dorothy",
            last_name="Vaughan",
            birth_year=current_year - 60,
            state_residence="ID",
            filing_status="single",
        )
        accounts = [
            Account(
                name="Traditional IRA",
                account_type="Traditional IRA",
                current_balance=100000,
                pretax_basis=50000,
                aftertax_basis=50000,
                growth_rate=0.0,
            ),
            Account(
                name="Roth IRA",
                account_type="Roth IRA",
                current_balance=0.0,
                growth_rate=0.0,
            ),
        ]
        scenario = ScenarioSettings(
            name="Pro rata",
            start_year=current_year,
            end_year=current_year,
            annual_conversion_target=10000,
            max_conversion_allowed=10000,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )
        income = [
            IncomeStream(
                name="Pension", income_type="Pension", annual_amount=50000,
                start_age=60, end_age=100, growth_rate=0.0,
            )
        ]
        result = ConversionSimulator(client).run_full_simulation(
            scenario, accounts, income, Expenses()
        ).years[0]

        self.assertAlmostEqual(result.recommended_conversion, 10000)
        # Half of the IRA is after-tax basis, so only $5,000 is taxable.
        expected = TaxCalculator("ID").calculate_roth_conversion_tax(
            conversion_amount=10000,
            pretax_iira_balance=50000,
            aftertax_ira_balance=50000,
            other_income=50000,
            filing_status="single",
            year=current_year,
        )
        self.assertAlmostEqual(
            result.conversion_tax, expected[1] + expected[2], delta=1
        )
        self.assertGreater(result.conversion_tax, 0)
        self.assertIn("non-taxable", " ".join(result.notes))


class TestAfterTaxMetric(unittest.TestCase):

    def test_after_tax_net_worth_subtracts_total_taxes_once(self):
        current_year = datetime.now().year
        client = ClientProfile(
            first_name="Katherine",
            last_name="Johnson",
            birth_year=current_year - 60,
            state_residence="ID",
            filing_status="single",
        )
        strategy = ConversionSimulator(client).run_full_simulation(
            ScenarioSettings(
                name="Test",
                start_year=current_year,
                end_year=current_year,
                annual_conversion_target=50000,
                max_conversion_allowed=50000,
                fill_tax_bracket=False,
                avoid_irmaa=False,
            ),
            [Account("IRA", "Traditional IRA", 100000, growth_rate=0.0)],
            [],
            Expenses(),
        )

        self.assertGreater(strategy.total_taxes_paid, 0)
        self.assertAlmostEqual(
            strategy.final_after_tax_net_worth,
            strategy.final_net_worth
            - strategy.total_taxes_unpaid
            - strategy.final_deferred_tax_liability,
        )
        self.assertGreater(strategy.final_deferred_tax_liability, 0)


class TestSecureRmdAge(unittest.TestCase):

    def test_1960_birth_year_waits_until_age_75(self):
        current_year = datetime.now().year
        client = ClientProfile(
            first_name="Eleanor",
            last_name="Roosevelt",
            birth_year=1960,
            state_residence="ID",
            filing_status="single",
        )
        simulator = ConversionSimulator(client)
        self.assertEqual(simulator.rmd_start_age, 75)

        accounts = [
            Account(
                name="Traditional IRA",
                account_type="Traditional IRA",
                current_balance=530000,
                pretax_basis=530000,
                growth_rate=0.0,
            ),
            Account(
                name="Roth IRA",
                account_type="Roth IRA",
                current_balance=0.0,
                growth_rate=0.0,
            ),
            Account(
                name="Taxable Brokerage",
                account_type="Taxable Brokerage",
                current_balance=0.0,
                growth_rate=0.0,
            ),
        ]
        scenario = ScenarioSettings(
            name="SECURE 2.0",
            start_year=current_year + 7,
            end_year=current_year + 9,
            annual_conversion_target=0,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )
        strategy = simulator.run_full_simulation(
            scenario, accounts, [], Expenses()
        )

        # Projection starts at age 73, but this birth year's RMD age is 75.
        self.assertEqual(strategy.years[0].age, 73)
        self.assertEqual(strategy.years[0].rmd_required, 0.0)
        self.assertGreater(strategy.years[-1].rmd_required, 0.0)


class TestSocialSecurityTaxation(unittest.TestCase):

    def test_social_security_is_taxed_by_provisional_income(self):
        current_year = datetime.now().year
        client = ClientProfile(
            first_name="Frances",
            last_name="Perkins",
            birth_year=current_year - 67,
            state_residence="ID",
            filing_status="single",
        )
        simulator = ConversionSimulator(client)
        income = [
            IncomeStream(
                name="Social Security",
                income_type="Social Security",
                annual_amount=30000,
                start_age=67,
                end_age=100,
                growth_rate=0.0,
                tax_treatment="tax_free",
            ),
            IncomeStream(
                name="Pension",
                income_type="Pension",
                annual_amount=20000,
                start_age=67,
                end_age=100,
                growth_rate=0.0,
            ),
        ]
        components = simulator.calculate_income_components(current_year, income)
        self.assertAlmostEqual(components["social_security"], 30000)
        self.assertAlmostEqual(components["ordinary"], 20000)

        scenario = ScenarioSettings(
            name="SS test",
            start_year=current_year,
            end_year=current_year,
            annual_conversion_target=0,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )
        strategy = simulator.run_full_simulation(
            scenario,
            [
                Account("IRA", "Traditional IRA", 100000, growth_rate=0.0),
                Account("Roth", "Roth IRA", 0.0, growth_rate=0.0),
                Account("Taxable", "Taxable Brokerage", 0.0, growth_rate=0.0),
            ],
            income,
            Expenses(),
        )
        result = strategy.years[0]

        # $20k other income + $15k half of SS = $35k provisional income.
        # The statutory single thresholds are $25k and $34k.
        self.assertAlmostEqual(result.taxable_social_security, 5350, delta=1)
        self.assertGreater(result.income_tax, 0)
        self.assertTrue(any("Social Security" in note for note in result.notes))


class TestIrmaaLookback(unittest.TestCase):

    def test_age_65_premium_uses_magi_from_two_years_earlier(self):
        current_year = datetime.now().year
        client = ClientProfile(
            first_name="Ida",
            last_name="Tarbell",
            birth_year=current_year - 63,
            state_residence="ID",
            filing_status="single",
        )
        simulator = ConversionSimulator(client)
        accounts = [
            Account(
                name="Traditional IRA",
                account_type="Traditional IRA",
                current_balance=150000,
                pretax_basis=150000,
                growth_rate=0.0,
            ),
            Account(
                name="Roth IRA",
                account_type="Roth IRA",
                current_balance=0.0,
                growth_rate=0.0,
            ),
            Account(
                name="Taxable Brokerage",
                account_type="Taxable Brokerage",
                current_balance=0.0,
                growth_rate=0.0,
            ),
        ]
        scenario = ScenarioSettings(
            name="IRMAA lookback",
            start_year=current_year,
            end_year=current_year + 2,
            annual_conversion_target=150000,
            max_conversion_allowed=150000,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )
        strategy = simulator.run_full_simulation(
            scenario, accounts, [], Expenses()
        )

        self.assertEqual(strategy.years[0].age, 63)
        self.assertEqual(strategy.years[2].age, 65)
        self.assertAlmostEqual(
            strategy.years[2].irmaa_magi,
            strategy.years[0].magi,
            delta=1,
        )
        self.assertGreater(strategy.years[2].irmaa_impact, 0)


if __name__ == '__main__':
    unittest.main()
