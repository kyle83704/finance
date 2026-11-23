"""Unit tests for tax calculations."""

import unittest
from src.tax_calculator import TaxCalculator


class TestTaxCalculator(unittest.TestCase):
    """Test tax calculation functions."""
    
    def setUp(self):
        self.calculator = TaxCalculator(state_residence="ID")
    
    def test_federal_tax_single_2026(self):
        """Test federal tax for single filer using 2026 IRS brackets."""
        tax = self.calculator.calculate_federal_tax(50000, "single", 2026)
        # First $12,400 @ 10% = $1,240
        # Next $37,600 ($50,000 - $12,400) @ 12% = $4,512
        # Total = $5,752
        self.assertAlmostEqual(tax, 5752, delta=10)
    
    def test_federal_tax_mfj_2026(self):
        """Test federal tax for married filing jointly."""
        tax = self.calculator.calculate_federal_tax(100000, "married_filing_jointly", 2026)
        # First $24,800 @ 10% = $2,480
        # Next $75,200 ($100,000 - $24,800) @ 12% = $9,024
        # Total = $11,504
        self.assertAlmostEqual(tax, 11504, delta=10)
    
    def test_state_tax_idaho(self):
        """Test Idaho state tax (5%)."""
        tax = self.calculator.calculate_state_tax(50000)
        self.assertAlmostEqual(tax, 2500, delta=1)
    
    def test_total_tax(self):
        """Test combined federal + state tax."""
        total = self.calculator.calculate_total_tax(50000, "single", 2026)
        federal = self.calculator.calculate_federal_tax(50000, "single", 2026)
        state = self.calculator.calculate_state_tax(50000)
        self.assertAlmostEqual(total, federal + state, delta=1)
    
    def test_standard_deduction_single(self):
        """Test 2026 standard deduction for a single filer."""
        ded = self.calculator.get_standard_deduction("single", 2026)
        self.assertEqual(ded, 16100)
    
    def test_standard_deduction_mfj(self):
        """Test 2026 standard deduction for married filing jointly."""
        ded = self.calculator.get_standard_deduction("married_filing_jointly", 2026)
        self.assertEqual(ded, 32200)
    
    def test_marginal_rate_single(self):
        """Test marginal tax rate at various income levels."""
        # $50,000 is still in the 12% 2026 federal bracket.
        rate = self.calculator.calculate_marginal_rate(50000, "single", 2026)
        # 12% federal + 5% Idaho = 17%
        self.assertAlmostEqual(rate, 0.17, places=2)
    
    def test_irmaa_single_tier1(self):
        """Test IRMAA tier 1 (no adjustment)."""
        adj, tier = self.calculator.calculate_irmaa(50000, "single")
        self.assertEqual(adj, 0)
        self.assertEqual(tier, 1)
    
    def test_irmaa_single_tier2(self):
        """Test IRMAA tier 2, including Part B and Part D."""
        adj, tier = self.calculator.calculate_irmaa(110000, "single")
        self.assertAlmostEqual(adj, 95.70)
        self.assertEqual(tier, 2)
    
    def test_irmaa_mfj_tier1(self):
        """Test IRMAA tier 1 for married couple."""
        adj, tier = self.calculator.calculate_irmaa(100000, "married_filing_jointly")
        self.assertEqual(adj, 0)
        self.assertEqual(tier, 1)
    
    def test_irmaa_mfj_tier2(self):
        """Test IRMAA tier 2 for married couple."""
        adj, tier = self.calculator.calculate_irmaa(220000, "married_filing_jointly")
        self.assertAlmostEqual(adj, 95.70)
        self.assertEqual(tier, 2)
    
    def test_rmd_age_73(self):
        """Test RMD calculation at age 73."""
        balance = 500000
        rmd = self.calculator.calculate_rmd(balance, 73)
        # Divisor at 73 is 26.5
        expected = balance / 26.5
        self.assertAlmostEqual(rmd, expected, places=0)
    
    def test_rmd_age_80(self):
        """Test RMD calculation at age 80."""
        balance = 500000
        rmd = self.calculator.calculate_rmd(balance, 80)
        # Divisor at 80 is 20.2
        expected = balance / 20.2
        self.assertAlmostEqual(rmd, expected, places=0)

    def test_rmd_uses_current_uniform_lifetime_divisors_at_advanced_ages(self):
        cases = {86: 15.2, 100: 6.4, 101: 6.0, 120: 2.0, 121: 2.0}
        for age, divisor in cases.items():
            with self.subTest(age=age):
                self.assertAlmostEqual(
                    self.calculator.calculate_rmd(100_000, age),
                    100_000 / divisor,
                    places=2,
                )
    
    def test_rmd_before_age_73(self):
        """Test RMD before age 73 (should be 0)."""
        rmd = self.calculator.calculate_rmd(500000, 72)
        self.assertEqual(rmd, 0.0)
    
    def test_pro_rata_ratio_50_50(self):
        """Test pro-rata calculation with 50/50 split."""
        pretax_ratio, aftertax_ratio = self.calculator.calculate_pro_rata_ratio(50000, 50000)
        self.assertAlmostEqual(pretax_ratio, 0.5, places=2)
        self.assertAlmostEqual(aftertax_ratio, 0.5, places=2)
    
    def test_pro_rata_ratio_100_0(self):
        """Test pro-rata calculation with all pre-tax."""
        pretax_ratio, aftertax_ratio = self.calculator.calculate_pro_rata_ratio(100000, 0)
        self.assertEqual(pretax_ratio, 1.0)
        self.assertEqual(aftertax_ratio, 0.0)
    
    def test_roth_conversion_tax_simple(self):
        """Test tax on Roth conversion without pro-rata."""
        taxable_conv, fed_tax, state_tax = self.calculator.calculate_roth_conversion_tax(
            conversion_amount=50000,
            pretax_iira_balance=200000,
            aftertax_ira_balance=0,
            other_income=50000,
            filing_status="single",
            year=2026,
        )
        # Should be fully taxable (all pre-tax)
        self.assertEqual(taxable_conv, 50000)
        # Tax should be approximately marginal rate × conversion
        self.assertGreater(fed_tax, 0)
        self.assertGreater(state_tax, 0)


class TestTaxableIncomeCalculation(unittest.TestCase):
    """Test taxable income calculations."""
    
    def setUp(self):
        self.calculator = TaxCalculator()
    
    def test_taxable_income_single_with_standard_ded(self):
        """Test taxable income calculation for single filer."""
        taxable = self.calculator.calculate_taxable_income(
            gross_income=50000,
            filing_status="single",
        )
        # $50,000 - $16,100 = $33,900
        self.assertEqual(taxable, 33900)
    
    def test_taxable_income_mfj_with_standard_ded(self):
        """Test taxable income calculation for MFJ."""
        taxable = self.calculator.calculate_taxable_income(
            gross_income=50000,
            filing_status="married_filing_jointly",
        )
        # $50,000 - $32,200 = $17,800
        self.assertEqual(taxable, 17800)
    
    def test_taxable_income_below_standard_ded(self):
        """Test that taxable income doesn't go negative."""
        taxable = self.calculator.calculate_taxable_income(
            gross_income=5000,
            filing_status="single",
        )
        self.assertEqual(taxable, 0)
    
    def test_taxable_income_with_conversion(self):
        """Test taxable income including Roth conversion."""
        taxable = self.calculator.calculate_taxable_income(
            gross_income=40000,
            roth_conversion=50000,
            filing_status="single",
        )
        # $40,000 + $50,000 - $16,100 = $73,900
        self.assertEqual(taxable, 73900)


class TestIncrementalConversionTax(unittest.TestCase):
    """Conversion tax must be the extra tax caused by the conversion."""

    def setUp(self):
        self.calculator = TaxCalculator(state_residence="ID")

    def test_conversion_tax_equals_difference_in_total_tax(self):
        conversion = 50000
        other_income = 50000
        taxable_conv, federal, state = self.calculator.calculate_roth_conversion_tax(
            conversion_amount=conversion,
            pretax_iira_balance=200000,
            aftertax_ira_balance=0,
            other_income=other_income,
            filing_status="single",
            year=2026,
        )

        baseline = self.calculator.calculate_taxable_income(
            other_income, filing_status="single"
        )
        with_conversion = self.calculator.calculate_taxable_income(
            other_income + conversion, filing_status="single"
        )
        expected_federal = (
            self.calculator.calculate_federal_tax(with_conversion, "single")
            - self.calculator.calculate_federal_tax(baseline, "single")
        )
        expected_state = (
            self.calculator.calculate_state_tax(with_conversion)
            - self.calculator.calculate_state_tax(baseline)
        )

        self.assertEqual(taxable_conv, conversion)
        self.assertAlmostEqual(federal, expected_federal, places=2)
        self.assertAlmostEqual(state, expected_state, places=2)

    def test_standard_deduction_shelters_a_small_conversion(self):
        taxable_conv, federal, state = self.calculator.calculate_roth_conversion_tax(
            conversion_amount=10000,
            pretax_iira_balance=200000,
            aftertax_ira_balance=0,
            other_income=0,
            filing_status="single",
            year=2026,
        )

        self.assertEqual(taxable_conv, 10000)
        self.assertEqual(federal, 0.0)
        self.assertEqual(state, 0.0)

    def test_income_tax_helper_uses_the_standard_deduction(self):
        self.assertEqual(
            self.calculator.calculate_income_tax(5000, "single"), 0.0
        )
        self.assertGreater(
            self.calculator.calculate_income_tax(50000, "single"), 0.0
        )


class TestProTaxRules(unittest.TestCase):
    """Regression coverage for the professional tax rules."""

    def setUp(self):
        self.calculator = TaxCalculator(state_residence="ID")

    def test_standard_deduction_includes_age_65_add_on(self):
        self.assertEqual(
            self.calculator.get_standard_deduction(
                "single", 2026, age=65
            ),
            18150,
        )
        self.assertEqual(
            self.calculator.get_standard_deduction(
                "married_filing_jointly", 2026, age=67, spouse_age=66
            ),
            35500,
        )
        self.assertEqual(
            self.calculator.get_standard_deduction(
                "married_filing_jointly", 2026, age=67, spouse_age=60
            ),
            33850,
        )

    def test_future_year_parameters_are_indexed(self):
        brackets = self.calculator.get_federal_brackets("single", 2027)
        self.assertGreater(brackets[1][1], 50400)
        self.assertGreater(
            self.calculator.get_standard_deduction("single", 2027), 16100
        )
        self.assertGreater(
            self.calculator.get_irmaa_brackets("single", 2027)[1][0],
            109000,
        )

    def test_social_security_provisional_income_taxability(self):
        self.assertAlmostEqual(
            self.calculator.calculate_taxable_social_security(
                30000, 20000, "married_filing_jointly"
            ),
            1500,
            delta=1,
        )
        self.assertAlmostEqual(
            self.calculator.calculate_taxable_social_security(
                20000, 30000, "single"
            ),
            9600,
            delta=1,
        )
        self.assertEqual(
            self.calculator.calculate_taxable_social_security(
                20000, 10000, "single"
            ),
            0,
        )

    def test_irmaa_2026_tier_boundaries(self):
        cases = [
            (109000, 0.0, 1),
            (109001, 95.70, 2),
            (137000, 95.70, 2),
            (137001, 240.40, 3),
            (499999, 529.60, 5),
            (500000, 578.00, 6),
        ]
        for magi, expected, expected_tier in cases:
            adjustment, tier = self.calculator.calculate_irmaa(
                magi, "single", 2026
            )
            self.assertAlmostEqual(adjustment, expected, places=2)
            self.assertEqual(tier, expected_tier)

    def test_qualified_dividends_get_preferential_rates(self):
        ordinary_only = self.calculator.calculate_income_tax(
            50000, "single", 2026
        )
        with_qualified = self.calculator.calculate_income_tax(
            50000, "single", 2026, qualified_income=10000
        )
        self.assertAlmostEqual(with_qualified, 4315, delta=1)
        self.assertGreater(ordinary_only, with_qualified)

    def test_secure_2_rmd_start_ages(self):
        cases = {
            1950: 72,
            1951: 73,
            1959: 73,
            1960: 75,
            1965: 75,
        }
        for birth_year, expected in cases.items():
            self.assertEqual(
                TaxCalculator.rmd_start_age_for_birth_year(birth_year),
                expected,
            )


if __name__ == '__main__':
    unittest.main()
