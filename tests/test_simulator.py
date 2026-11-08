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
        # Single filer, standard deduction $14,600
        # Current taxable = $40,000 - $14,600 = $25,400
        # First bracket limit is $11,600
        # So they're already in second bracket ($25,400 > $11,600)
        # Next limit is $47,150, so room = $47,150 - $25,400 = $21,750
        self.assertAlmostEqual(amount, 21750, delta=10)
    
    def test_calculate_max_before_irmaa_single(self):
        """Test maximum income before IRMAA triggers."""
        max_amount = self.simulator._calculate_max_before_irmaa(
            current_income=50000,
            filing_status="single",
        )
        # First IRMAA threshold for single = $97,000
        # Room = $97,000 - $50,000 = $47,000
        self.assertEqual(max_amount, 47000)
    
    def test_calculate_max_before_irmaa_at_threshold(self):
        """Test maximum when at IRMAA threshold."""
        max_amount = self.simulator._calculate_max_before_irmaa(
            current_income=97000,
            filing_status="single",
        )
        self.assertEqual(max_amount, 0)
    
    def test_calculate_max_before_irmaa_above_threshold(self):
        """Test maximum when already above threshold."""
        max_amount = self.simulator._calculate_max_before_irmaa(
            current_income=100000,
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


if __name__ == '__main__':
    unittest.main()
