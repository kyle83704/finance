"""Unit tests for tax calculations."""

import unittest
from src.tax_calculator import TaxCalculator


class TestTaxCalculator(unittest.TestCase):
    """Test tax calculation functions."""
    
    def setUp(self):
        self.calculator = TaxCalculator(state_residence="ID")
    
    def test_federal_tax_single_2026(self):
        """Test federal tax for single filer."""
        # Test bracket: $50,000 should be in 22% bracket
        tax = self.calculator.calculate_federal_tax(50000, "single", 2026)
        # First $11,600 @ 10% = $1,160
        # Next $35,550 ($47,150 - $11,600) @ 12% = $4,266
        # Next $2,850 ($50,000 - $47,150) @ 22% = $627
        # Total = $1,160 + $4,266 + $627 = $6,053
        self.assertAlmostEqual(tax, 6053, delta=10)
    
    def test_federal_tax_mfj_2026(self):
        """Test federal tax for married filing jointly."""
        # $100,000 income
        tax = self.calculator.calculate_federal_tax(100000, "married_filing_jointly", 2026)
        # First $23,200 @ 10% = $2,320
        # Next $71,100 ($94,300 - $23,200) @ 12% = $8,532
        # Next $5,700 ($100,000 - $94,300) @ 22% = $1,254
        # Total = $2,320 + $8,532 + $1,254 = $12,106
        self.assertAlmostEqual(tax, 12106, delta=10)
    
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
        """Test standard deduction for single filer."""
        ded = self.calculator.get_standard_deduction("single", 2026)
        self.assertEqual(ded, 14600)
    
    def test_standard_deduction_mfj(self):
        """Test standard deduction for married filing jointly."""
        ded = self.calculator.get_standard_deduction("married_filing_jointly", 2026)
        self.assertEqual(ded, 29200)
    
    def test_marginal_rate_single(self):
        """Test marginal tax rate at various income levels."""
        # $50,000 should be in 22% federal bracket
        rate = self.calculator.calculate_marginal_rate(50000, "single", 2026)
        # 22% federal + 5% Idaho = 27%
        self.assertAlmostEqual(rate, 0.27, places=2)
    
    def test_irmaa_single_tier1(self):
        """Test IRMAA tier 1 (no adjustment)."""
        adj, tier = self.calculator.calculate_irmaa(50000, "single")
        self.assertEqual(adj, 0)
        self.assertEqual(tier, 1)
    
    def test_irmaa_single_tier2(self):
        """Test IRMAA tier 2."""
        adj, tier = self.calculator.calculate_irmaa(110000, "single")
        self.assertEqual(adj, 70)
        self.assertEqual(tier, 2)
    
    def test_irmaa_mfj_tier1(self):
        """Test IRMAA tier 1 for married couple."""
        adj, tier = self.calculator.calculate_irmaa(100000, "married_filing_jointly")
        self.assertEqual(adj, 0)
        self.assertEqual(tier, 1)
    
    def test_irmaa_mfj_tier2(self):
        """Test IRMAA tier 2 for married couple."""
        adj, tier = self.calculator.calculate_irmaa(200000, "married_filing_jointly")
        self.assertEqual(adj, 70)
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
        # $50,000 - $14,600 = $35,400
        self.assertEqual(taxable, 35400)
    
    def test_taxable_income_mfj_with_standard_ded(self):
        """Test taxable income calculation for MFJ."""
        taxable = self.calculator.calculate_taxable_income(
            gross_income=50000,
            filing_status="married_filing_jointly",
        )
        # $50,000 - $29,200 = $20,800
        self.assertEqual(taxable, 20800)
    
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
        # $40,000 + $50,000 - $14,600 = $75,400
        self.assertEqual(taxable, 75400)


if __name__ == '__main__':
    unittest.main()
