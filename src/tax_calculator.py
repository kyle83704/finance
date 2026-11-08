"""Tax calculations for Roth conversion simulator."""

from src.constants import (
    FEDERAL_TAX_BRACKETS_2026, STANDARD_DEDUCTION_2026, 
    STATE_TAX_RATES, IRMAA_BRACKETS_2026, RMD_AGE_MULTIPLIERS, RMD_START_AGE
)
from typing import Tuple, Dict


class TaxCalculator:
    """Calculates federal and state income taxes, IRMAA, RMDs, etc."""
    
    def __init__(self, state_residence: str = "ID"):
        self.state = state_residence
        self.state_tax_rate = STATE_TAX_RATES.get(state_residence, 0.0)
    
    def calculate_federal_tax(self, taxable_income: float, filing_status: str, year: int = 2026) -> float:
        """Calculate federal income tax based on taxable income."""
        if taxable_income <= 0:
            return 0.0
        
        # Use 2026 brackets (can be parameterized for other years)
        brackets = FEDERAL_TAX_BRACKETS_2026.get(filing_status, [])
        if not brackets:
            return 0.0
        
        tax = 0.0
        for i, (lower, upper, rate) in enumerate(brackets):
            if taxable_income <= lower:
                break
            
            bracket_top = min(taxable_income, upper)
            if bracket_top > lower:
                tax += (bracket_top - lower) * rate
        
        return tax
    
    def calculate_state_tax(self, taxable_income: float) -> float:
        """Calculate state income tax."""
        return max(0, taxable_income) * self.state_tax_rate
    
    def calculate_total_tax(self, taxable_income: float, filing_status: str, year: int = 2026) -> float:
        """Calculate combined federal + state income tax."""
        federal = self.calculate_federal_tax(taxable_income, filing_status, year)
        state = self.calculate_state_tax(taxable_income)
        return federal + state
    
    def calculate_marginal_rate(self, taxable_income: float, filing_status: str, year: int = 2026) -> float:
        """Calculate marginal tax rate (federal + state)."""
        brackets = FEDERAL_TAX_BRACKETS_2026.get(filing_status, [])
        federal_marginal = 0.0
        
        for lower, upper, rate in brackets:
            if lower <= taxable_income < upper:
                federal_marginal = rate
                break
        
        return federal_marginal + self.state_tax_rate
    
    def get_standard_deduction(self, filing_status: str, year: int = 2026) -> float:
        """Get standard deduction for the year."""
        return STANDARD_DEDUCTION_2026.get(filing_status, 0)
    
    def calculate_taxable_income(
        self, 
        gross_income: float, 
        traditional_ira_withdrawal: float = 0.0,
        roth_conversion: float = 0.0,
        filing_status: str = "married_filing_jointly"
    ) -> float:
        """
        Calculate taxable income after standard deduction.
        
        Note: Roth conversion is included in gross income for tax purposes.
        """
        agi = gross_income + roth_conversion
        standard_deduction = self.get_standard_deduction(filing_status)
        taxable = max(0, agi - standard_deduction)
        return taxable
    
    def calculate_irmaa(
        self, 
        magi: float, 
        filing_status: str = "married_filing_jointly"
    ) -> Tuple[float, int]:
        """
        Calculate Income-Related Monthly Adjustment Amount (IRMAA) for Medicare.
        
        Returns:
            Tuple of (monthly_adjustment, tier_level)
        """
        brackets = IRMAA_BRACKETS_2026.get(filing_status, [])
        
        for i, (threshold, adjustment) in enumerate(brackets):
            # Check if MAGI falls in this bracket
            if i == len(brackets) - 1:  # Last bracket
                if magi >= threshold:
                    return (adjustment, i + 1)
            else:
                next_threshold = brackets[i + 1][0]
                if threshold <= magi < next_threshold:
                    return (adjustment, i + 1)
        
        return (0, 0)
    
    def calculate_rmd(self, account_balance: float, age: int) -> float:
        """
        Calculate Required Minimum Distribution for traditional IRA/401k.
        
        Assumes age 73+ (RMD Start Age).
        """
        if age < RMD_START_AGE:
            return 0.0
        
        divisor = RMD_AGE_MULTIPLIERS.get(age, 1.0)
        if divisor == 0:
            return 0.0
        
        return account_balance / divisor
    
    def calculate_pro_rata_ratio(
        self, 
        pretax_total: float, 
        aftertax_total: float
    ) -> Tuple[float, float]:
        """
        Calculate pro-rata ratio for Roth conversions.
        
        Returns:
            Tuple of (pretax_ratio, aftertax_ratio)
            
        Note: IRS requires using ALL IRAs together for pro-rata calculation.
        """
        total = pretax_total + aftertax_total
        if total == 0:
            return (0, 0)
        
        return (pretax_total / total, aftertax_total / total)
    
    def calculate_roth_conversion_tax(
        self,
        conversion_amount: float,
        pretax_iira_balance: float,
        aftertax_ira_balance: float,
        other_income: float,
        filing_status: str = "married_filing_jointly",
        year: int = 2026
    ) -> Tuple[float, float, float]:
        """
        Calculate tax impact of a Roth conversion, including pro-rata rule.
        
        Returns:
            Tuple of (taxable_conversion_amount, federal_tax, state_tax)
        """
        # Calculate pro-rata ratio
        pretax_ratio, aftertax_ratio = self.calculate_pro_rata_ratio(
            pretax_iira_balance, aftertax_ira_balance
        )
        
        # Amount that's taxable (pro-rata rule)
        taxable_conversion = conversion_amount * pretax_ratio
        
        # Calculate tax on this income
        new_taxable_income = self.calculate_taxable_income(
            other_income + taxable_conversion,
            filing_status=filing_status
        )
        
        # Find marginal rate for the converted amount
        marginal_rate = self.calculate_marginal_rate(new_taxable_income, filing_status, year)
        
        # Tax on the conversion
        federal_tax = taxable_conversion * self.calculate_marginal_rate(
            new_taxable_income, filing_status, year
        )
        state_tax = taxable_conversion * self.state_tax_rate
        
        return (taxable_conversion, federal_tax, state_tax)
    
    def has_kiddie_tax(self, age: int) -> bool:
        """Check if unearned income kiddie tax rules apply (age < 24)."""
        return age < 24
    
    def calculate_qualified_dividend_tax(
        self,
        dividend_income: float,
        ordinary_income: float,
        filing_status: str = "married_filing_jointly"
    ) -> float:
        """
        Calculate tax on qualified dividends (preferential rates).
        
        Qualified dividends taxed at 0%, 15%, or 20% depending on bracket.
        """
        # Simplified: assume 15% rate
        return dividend_income * 0.15
