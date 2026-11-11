"""Tax calculations for Roth conversion simulator."""

from src.constants import (
    FEDERAL_TAX_BRACKETS_2026, STANDARD_DEDUCTION_2026,
    STATE_TAX_RATES, IRMAA_BRACKETS_2026, RMD_AGE_MULTIPLIERS, RMD_START_AGE
)
from typing import Tuple


class TaxCalculator:
    """Calculates federal and state income taxes, IRMAA, RMDs, etc."""

    def __init__(self, state_residence: str = "ID"):
        self.state = state_residence
        self.state_tax_rate = STATE_TAX_RATES.get(state_residence, 0.0)

    def calculate_federal_tax(self, taxable_income: float, filing_status: str,
                              year: int = 2026) -> float:
        """Calculate federal income tax based on taxable income."""
        if taxable_income <= 0:
            return 0.0

        brackets = FEDERAL_TAX_BRACKETS_2026.get(filing_status, [])
        if not brackets:
            return 0.0

        tax = 0.0
        for lower, upper, rate in brackets:
            if taxable_income <= lower:
                break

            bracket_top = min(taxable_income, upper)
            if bracket_top > lower:
                tax += (bracket_top - lower) * rate

        return tax

    def calculate_state_tax(self, taxable_income: float) -> float:
        """Calculate state income tax (simplified flat rate)."""
        return max(0.0, taxable_income) * self.state_tax_rate

    def calculate_total_tax(self, taxable_income: float, filing_status: str,
                            year: int = 2026) -> float:
        """Calculate combined federal + state income tax."""
        federal = self.calculate_federal_tax(taxable_income, filing_status, year)
        state = self.calculate_state_tax(taxable_income)
        return federal + state

    def calculate_income_tax(self, gross_income: float, filing_status: str,
                             year: int = 2026) -> float:
        """Calculate income tax on ordinary income after the standard deduction.

        This is the baseline tax before any voluntary Roth conversion.  The
        simulator uses it so conversion tax can be measured as the *extra* tax
        the conversion causes, rather than taxing the whole conversion at the
        top marginal rate.
        """
        taxable = self.calculate_taxable_income(
            gross_income, filing_status=filing_status
        )
        return self.calculate_total_tax(taxable, filing_status, year)

    def calculate_marginal_rate(self, taxable_income: float, filing_status: str,
                                year: int = 2026) -> float:
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
        """Calculate taxable income after the standard deduction.

        RMDs/traditional withdrawals and Roth conversions are ordinary income
        in the conversion year.  The ``traditional_ira_withdrawal`` argument is
        accepted for API symmetry; callers normally include the RMD directly in
        ``gross_income``.
        """
        agi = gross_income + traditional_ira_withdrawal + roth_conversion
        standard_deduction = self.get_standard_deduction(filing_status)
        return max(0.0, agi - standard_deduction)

    def calculate_irmaa(
        self,
        magi: float,
        filing_status: str = "married_filing_jointly"
    ) -> Tuple[float, int]:
        """Calculate the monthly IRMAA surcharge and tier.

        Returns:
            Tuple of (monthly_adjustment, tier_level)
        """
        brackets = IRMAA_BRACKETS_2026.get(filing_status, [])
        if not brackets:
            return (0.0, 0)

        for i, (threshold, adjustment) in enumerate(brackets):
            if i == len(brackets) - 1:
                if magi >= threshold:
                    return (adjustment, i + 1)
            else:
                next_threshold = brackets[i + 1][0]
                if threshold <= magi < next_threshold:
                    return (adjustment, i + 1)

        return (0.0, 0)

    def calculate_rmd(self, account_balance: float, age: int) -> float:
        """Calculate Required Minimum Distribution for traditional accounts."""
        if age < RMD_START_AGE or account_balance <= 0:
            return 0.0

        divisor = RMD_AGE_MULTIPLIERS.get(age, 1.0)
        if divisor <= 0:
            return 0.0

        return account_balance / divisor

    def calculate_pro_rata_ratio(
        self,
        pretax_total: float,
        aftertax_total: float
    ) -> Tuple[float, float]:
        """Calculate the IRA pro-rata ratio.

        Returns:
            Tuple of (pretax_ratio, aftertax_ratio)
        """
        total = max(0.0, pretax_total) + max(0.0, aftertax_total)
        if total == 0:
            return (0.0, 0.0)

        return (max(0.0, pretax_total) / total,
                max(0.0, aftertax_total) / total)

    def calculate_roth_conversion_tax(
        self,
        conversion_amount: float,
        pretax_iira_balance: float,
        aftertax_ira_balance: float,
        other_income: float,
        filing_status: str = "married_filing_jointly",
        year: int = 2026
    ) -> Tuple[float, float, float]:
        """Calculate the incremental tax caused by a Roth conversion.

        The old implementation applied the top marginal rate to the entire
        conversion.  That overstates the tax whenever a conversion crosses
        brackets or is partly sheltered by the standard deduction.  Instead,
        compare the tax with and without the conversion and return the
        difference.

        Returns:
            Tuple of (taxable_conversion_amount, incremental_federal_tax,
                      incremental_state_tax)
        """
        if conversion_amount <= 0:
            return (0.0, 0.0, 0.0)

        pretax_ratio, _ = self.calculate_pro_rata_ratio(
            pretax_iira_balance, aftertax_ira_balance
        )
        taxable_conversion = max(0.0, conversion_amount) * pretax_ratio

        baseline_taxable = self.calculate_taxable_income(
            max(0.0, other_income), filing_status=filing_status
        )
        conversion_taxable = self.calculate_taxable_income(
            max(0.0, other_income) + taxable_conversion,
            filing_status=filing_status,
        )

        federal_tax = (
            self.calculate_federal_tax(conversion_taxable, filing_status, year)
            - self.calculate_federal_tax(baseline_taxable, filing_status, year)
        )
        state_tax = (
            self.calculate_state_tax(conversion_taxable)
            - self.calculate_state_tax(baseline_taxable)
        )

        return (taxable_conversion, max(0.0, federal_tax), max(0.0, state_tax))

    def has_kiddie_tax(self, age: int) -> bool:
        """Check if unearned income kiddie tax rules apply (age < 24)."""
        return age < 24

    def calculate_qualified_dividend_tax(
        self,
        dividend_income: float,
        ordinary_income: float,
        filing_status: str = "married_filing_jointly"
    ) -> float:
        """Calculate tax on qualified dividends (simplified 15% rate).

        The simulator currently treats qualified dividends as ordinary income
        for the main projection; this helper remains available for callers that
        model the preferential rate explicitly.
        """
        return max(0.0, dividend_income) * 0.15
