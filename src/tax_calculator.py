"""Tax calculations for Roth conversion simulator.

The 2026 federal parameters come from IRS Rev. Proc. 2025-32 and the CMS 2026
Medicare premium tables.  Future-year thresholds are indexed with a documented
planning assumption because the IRS does not publish future tables.
"""

from typing import Optional, Tuple

from src.constants import (
    ADDITIONAL_STANDARD_DEDUCTION_2026,
    FEDERAL_TAX_BRACKETS_2026,
    IRMAA_BRACKETS_2026,
    LTCG_BRACKETS_2026,
    RMD_AGE_MULTIPLIERS,
    RMD_START_AGE,
    RMD_START_AGE_1960_PLUS,
    STANDARD_DEDUCTION_2026,
    STATE_TAX_RATES,
    TAX_BRACKET_INFLATION_RATE,
)


class TaxCalculator:
    """Calculates federal and state income taxes, IRMAA, RMDs, etc."""

    def __init__(self, state_residence: str = "ID",
                 inflation_rate: float = TAX_BRACKET_INFLATION_RATE):
        self.state = state_residence
        self.state_tax_rate = STATE_TAX_RATES.get(state_residence, 0.0)
        self.inflation_rate = max(0.0, inflation_rate)

    # ------------------------------------------------------------------
    # Indexing and table helpers
    # ------------------------------------------------------------------
    def inflation_factor(self, year: int) -> float:
        """Return the cumulative indexing factor for a projection year."""
        return (1.0 + self.inflation_rate) ** max(0, year - 2026)

    def get_federal_brackets(self, filing_status: str,
                             year: int = 2026):
        """Return 2026 brackets scaled to ``year``."""
        factor = self.inflation_factor(year)
        brackets = FEDERAL_TAX_BRACKETS_2026.get(filing_status, [])
        return [
            (
                lower * factor,
                upper if upper == float("inf") else upper * factor,
                rate,
            )
            for lower, upper, rate in brackets
        ]

    def get_ltcg_brackets(self, filing_status: str,
                          year: int = 2026):
        """Return long-term capital gain/qualified dividend brackets."""
        factor = self.inflation_factor(year)
        brackets = LTCG_BRACKETS_2026.get(
            filing_status, LTCG_BRACKETS_2026.get("single", [])
        )
        return [
            (
                lower * factor,
                upper if upper == float("inf") else upper * factor,
                rate,
            )
            for lower, upper, rate in brackets
        ]

    def get_irmaa_brackets(self, filing_status: str,
                           year: int = 2026):
        """Return IRMAA thresholds scaled to ``year``.

        Adjustments are monthly Part B + Part D surcharges per person.
        """
        factor = self.inflation_factor(year)
        brackets = IRMAA_BRACKETS_2026.get(filing_status)
        if not brackets:
            brackets = IRMAA_BRACKETS_2026.get("married_filing_jointly", [])
        return [
            (threshold * factor if threshold else 0.0, adjustment)
            for threshold, adjustment in brackets
        ]

    # ------------------------------------------------------------------
    # Ordinary income tax
    # ------------------------------------------------------------------
    def calculate_federal_tax(self, taxable_income: float, filing_status: str,
                              year: int = 2026) -> float:
        """Calculate federal income tax on ordinary taxable income."""
        if taxable_income <= 0:
            return 0.0

        tax = 0.0
        for lower, upper, rate in self.get_federal_brackets(filing_status, year):
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
        """Calculate combined federal + state ordinary income tax."""
        federal = self.calculate_federal_tax(taxable_income, filing_status, year)
        state = self.calculate_state_tax(taxable_income)
        return federal + state

    def calculate_taxable_income(
        self,
        gross_income: float,
        traditional_ira_withdrawal: float = 0.0,
        roth_conversion: float = 0.0,
        filing_status: str = "married_filing_jointly",
        year: int = 2026,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
    ) -> float:
        """Calculate taxable income after the age-aware standard deduction."""
        agi = (
            max(0.0, gross_income)
            + max(0.0, traditional_ira_withdrawal)
            + max(0.0, roth_conversion)
        )
        standard_deduction = self.get_standard_deduction(
            filing_status, year, age=age, spouse_age=spouse_age
        )
        return max(0.0, agi - standard_deduction)

    def get_standard_deduction(self, filing_status: str, year: int = 2026,
                               age: Optional[int] = None,
                               spouse_age: Optional[int] = None) -> float:
        """Get the standard deduction, including the 65+ additional amount.

        The additional amount is per qualifying person.  A married couple where
        both spouses are 65+ therefore gets two additional amounts.
        """
        factor = self.inflation_factor(year)
        base = STANDARD_DEDUCTION_2026.get(filing_status, 0.0) * factor
        if age is None or age < 65:
            return base

        additional = ADDITIONAL_STANDARD_DEDUCTION_2026.get(
            filing_status, 0.0
        ) * factor
        if filing_status == "married_filing_jointly":
            qualifying_people = 1
            if spouse_age is not None and spouse_age >= 65:
                qualifying_people += 1
            return base + additional * qualifying_people
        return base + additional

    def calculate_marginal_rate(self, taxable_income: float,
                                filing_status: str,
                                year: int = 2026) -> float:
        """Calculate marginal federal rate plus the flat state rate."""
        federal_marginal = 0.0
        for lower, upper, rate in self.get_federal_brackets(filing_status, year):
            if lower <= taxable_income < upper:
                federal_marginal = rate
                break
        return federal_marginal + self.state_tax_rate

    # ------------------------------------------------------------------
    # Social Security and preferential income
    # ------------------------------------------------------------------
    def calculate_taxable_social_security(
        self,
        social_security_benefit: float,
        other_income: float,
        filing_status: str = "married_filing_jointly",
        tax_exempt_interest: float = 0.0,
    ) -> float:
        """Calculate the taxable portion of Social Security benefits.

        Uses the provisional-income formula.  The $32,000/$44,000 (MFJ) and
        $25,000/$34,000 (single/HOH) thresholds are statutory and are not
        indexed.  For married filing separately, up to 85% is taxable.
        """
        benefit = max(0.0, social_security_benefit)
        if benefit <= 0:
            return 0.0

        if filing_status == "married_filing_jointly":
            base_threshold, adjusted_threshold = 32_000.0, 44_000.0
        elif filing_status in ("single", "head_of_household"):
            base_threshold, adjusted_threshold = 25_000.0, 34_000.0
        else:
            base_threshold, adjusted_threshold = 0.0, 0.0

        provisional_income = (
            max(0.0, other_income)
            + 0.5 * benefit
            + max(0.0, tax_exempt_interest)
        )
        if provisional_income <= base_threshold:
            return 0.0

        if provisional_income <= adjusted_threshold:
            return min(
                0.5 * benefit,
                0.5 * (provisional_income - base_threshold),
            )

        first_tier = min(
            0.5 * benefit,
            0.5 * (adjusted_threshold - base_threshold),
        )
        second_tier = 0.85 * (provisional_income - adjusted_threshold)
        return min(0.85 * benefit, first_tier + second_tier)

    def _calculate_preferential_tax(
        self,
        qualified_taxable: float,
        ordinary_taxable: float,
        filing_status: str,
        year: int = 2026,
    ) -> float:
        """Tax qualified dividends/LTCG at 0/15/20% on top of ordinary income."""
        remaining = max(0.0, qualified_taxable)
        base = max(0.0, ordinary_taxable)
        tax = 0.0

        for lower, upper, rate in self.get_ltcg_brackets(filing_status, year):
            if remaining <= 0:
                break
            start = max(base, lower)
            if upper <= start:
                continue
            amount = remaining if upper == float("inf") else min(
                remaining, upper - start
            )
            tax += amount * rate
            remaining -= amount
            base += amount

        return tax

    def calculate_federal_tax_with_qualified(
        self,
        total_income: float,
        qualified_income: float,
        filing_status: str,
        year: int = 2026,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
    ) -> float:
        """Federal tax when part of income is qualified dividends/LTCG."""
        taxable_total = self.calculate_taxable_income(
            total_income,
            filing_status=filing_status,
            year=year,
            age=age,
            spouse_age=spouse_age,
        )
        qualified_taxable = min(max(0.0, qualified_income), taxable_total)
        ordinary_taxable = max(0.0, taxable_total - qualified_taxable)
        return (
            self.calculate_federal_tax(
                ordinary_taxable, filing_status, year
            )
            + self._calculate_preferential_tax(
                qualified_taxable, ordinary_taxable, filing_status, year
            )
        )

    def calculate_income_tax(
        self,
        gross_income: float,
        filing_status: str,
        year: int = 2026,
        qualified_income: float = 0.0,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
    ) -> float:
        """Calculate total income tax on ordinary and qualified income.

        ``gross_income`` includes the qualified portion; ``qualified_income``
        identifies how much of it receives 0/15/20% federal rates.  State tax is
        applied to the same taxable total at the simplified flat rate.
        """
        taxable_total = self.calculate_taxable_income(
            gross_income,
            filing_status=filing_status,
            year=year,
            age=age,
            spouse_age=spouse_age,
        )
        federal = self.calculate_federal_tax_with_qualified(
            gross_income,
            qualified_income,
            filing_status,
            year=year,
            age=age,
            spouse_age=spouse_age,
        )
        state = self.calculate_state_tax(taxable_total)
        return federal + state

    # ------------------------------------------------------------------
    # IRMAA and RMDs
    # ------------------------------------------------------------------
    def calculate_irmaa(
        self,
        magi: float,
        filing_status: str = "married_filing_jointly",
        year: int = 2026,
    ) -> Tuple[float, int]:
        """Calculate the monthly IRMAA surcharge and tier.

        The returned amount combines Part B and Part D per person.  A MAGI at
        the first threshold is still in tier 1; the next dollar enters tier 2.
        """
        brackets = self.get_irmaa_brackets(filing_status, year)
        if not brackets:
            return (0.0, 0)

        if len(brackets) > 1 and magi <= brackets[1][0]:
            return (brackets[0][1], 1)

        for i in range(1, len(brackets)):
            threshold, adjustment = brackets[i]
            if i == len(brackets) - 1:
                if magi >= threshold:
                    return (adjustment, i + 1)
            else:
                next_threshold = brackets[i + 1][0]
                if threshold < magi <= next_threshold:
                    # The top CMS tier starts at its threshold, so do not let
                    # the tier below capture an exact top-threshold MAGI.
                    if i + 1 == len(brackets) - 1 and magi == next_threshold:
                        continue
                    return (adjustment, i + 1)

        return (0.0, 0)

    def calculate_rmd(self, account_balance: float, age: int,
                      start_age: int = RMD_START_AGE) -> float:
        """Calculate Required Minimum Distribution for traditional accounts."""
        if age < start_age or account_balance <= 0:
            return 0.0

        divisor = RMD_AGE_MULTIPLIERS.get(age, 1.0)
        if divisor <= 0:
            return 0.0

        return account_balance / divisor

    @staticmethod
    def rmd_start_age_for_birth_year(birth_year: int) -> int:
        """Return the SECURE 2.0 RMD age for a birth year.

        SECURE 2.0 sets age 73 for people born 1951-1959 and age 75 for people
        born in 1960 or later.  Earlier birth years retain age 72.
        """
        if birth_year >= 1960:
            return RMD_START_AGE_1960_PLUS
        if birth_year >= 1951:
            return RMD_START_AGE
        return 72

    # ------------------------------------------------------------------
    # Conversion pro-rata and incremental tax
    # ------------------------------------------------------------------
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
        year: int = 2026,
        qualified_income: float = 0.0,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """Calculate the incremental tax caused by a Roth conversion.

        The old implementation applied the top marginal rate to the entire
        conversion.  This compares the tax with and without the conversion so
        bracket crossings and standard-deduction sheltering are handled.

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

        baseline_total = max(0.0, other_income) + max(0.0, qualified_income)
        converted_total = baseline_total + taxable_conversion

        baseline_federal = self.calculate_federal_tax_with_qualified(
            baseline_total,
            qualified_income,
            filing_status,
            year=year,
            age=age,
            spouse_age=spouse_age,
        )
        converted_federal = self.calculate_federal_tax_with_qualified(
            converted_total,
            qualified_income,
            filing_status,
            year=year,
            age=age,
            spouse_age=spouse_age,
        )
        baseline_state = self.calculate_state_tax(
            self.calculate_taxable_income(
                baseline_total,
                filing_status=filing_status,
                year=year,
                age=age,
                spouse_age=spouse_age,
            )
        )
        converted_state = self.calculate_state_tax(
            self.calculate_taxable_income(
                converted_total,
                filing_status=filing_status,
                year=year,
                age=age,
                spouse_age=spouse_age,
            )
        )

        return (
            taxable_conversion,
            max(0.0, converted_federal - baseline_federal),
            max(0.0, converted_state - baseline_state),
        )

    def calculate_capital_gains_tax(
        self,
        realized_gains: float,
        ordinary_income: float,
        qualified_income: float = 0.0,
        filing_status: str = "married_filing_jointly",
        year: int = 2026,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
    ) -> float:
        """Incremental federal + state tax from long-term realized gains.

        All gains are treated as long-term and stacked on top of ordinary and
        qualified income.  The caller is responsible for supplying the correct
        ordinary-income base; this method does not model short-term gains.
        """
        gains = max(0.0, realized_gains)
        if gains <= 0:
            return 0.0

        baseline = self.calculate_income_tax(
            max(0.0, ordinary_income) + max(0.0, qualified_income),
            filing_status,
            year,
            qualified_income=qualified_income,
            age=age,
            spouse_age=spouse_age,
        )
        with_gains = self.calculate_income_tax(
            max(0.0, ordinary_income) + max(0.0, qualified_income) + gains,
            filing_status,
            year,
            qualified_income=max(0.0, qualified_income) + gains,
            age=age,
            spouse_age=spouse_age,
        )
        return max(0.0, with_gains - baseline)

    def has_kiddie_tax(self, age: int) -> bool:
        """Check if unearned income kiddie tax rules apply (age < 24)."""
        return age < 24

    def calculate_qualified_dividend_tax(
        self,
        dividend_income: float,
        ordinary_income: float,
        filing_status: str = "married_filing_jointly",
        year: int = 2026,
    ) -> float:
        """Calculate federal tax on qualified dividends at 0/15/20% rates."""
        total_income = max(0.0, ordinary_income) + max(0.0, dividend_income)
        taxable_total = self.calculate_taxable_income(
            total_income, filing_status=filing_status, year=year
        )
        qualified_taxable = min(max(0.0, dividend_income), taxable_total)
        ordinary_taxable = max(0.0, taxable_total - qualified_taxable)
        return self._calculate_preferential_tax(
            qualified_taxable, ordinary_taxable, filing_status, year
        )
