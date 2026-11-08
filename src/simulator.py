"""Core simulation engine for Roth conversion analysis."""

from src.models import (
    ClientProfile, Account, IncomeStream, Expenses, 
    ScenarioSettings, ConversionResult, ConversionStrategy
)
from src.tax_calculator import TaxCalculator
from typing import List, Tuple, Optional, Dict
from datetime import datetime


class ConversionSimulator:
    """Main engine for simulating Roth conversion strategies."""
    
    def __init__(self, client: ClientProfile, tax_calculator: Optional[TaxCalculator] = None):
        self.client = client
        self.tax_calc = tax_calculator or TaxCalculator(client.state_residence)
    
    def calculate_annual_income(
        self, 
        year: int,
        income_streams: List[IncomeStream]
    ) -> float:
        """Calculate total income for a given year."""
        total_income = 0.0
        current_year = datetime.now().year
        age_in_year = self.client.current_age + (year - current_year)
        
        for stream in income_streams:
            # Check if income is active in this year
            if stream.start_age <= age_in_year <= stream.end_age:
                # Calculate growth from start to current year
                years_elapsed = year - current_year
                amount = stream.annual_amount * (1 + stream.growth_rate) ** years_elapsed
                total_income += amount
        
        return total_income
    
    def calculate_account_growth(
        self,
        balance: float,
        growth_rate: float,
        years: int,
        annual_contribution: float = 0.0
    ) -> float:
        """Calculate account balance after growth and contributions."""
        current_balance = balance
        for _ in range(years):
            current_balance = (current_balance + annual_contribution) * (1 + growth_rate)
        return current_balance
    
    def simulate_year(
        self,
        year: int,
        age: int,
        accounts: Dict[str, Account],
        income_streams: List[IncomeStream],
        expenses: Expenses,
        scenario: ScenarioSettings,
        tax_year: int = 2026
    ) -> ConversionResult:
        """
        Simulate a single year of retirement, determining optimal Roth conversion.
        
        Args:
            year: Calendar year for simulation
            age: Client's age during this year
            accounts: Dict of account_name -> Account object
            income_streams: List of income streams
            expenses: Annual expenses
            scenario: Scenario settings with objectives
            tax_year: Year for tax bracket/IRMAA lookup
            
        Returns:
            ConversionResult with details for the year
        """
        result = ConversionResult(
            year=year,
            age=age,
            start_balance_pretax=sum(
                acc.current_balance for acc in accounts.values() 
                if acc.account_type in ["Traditional IRA", "SEP IRA", "Solo 401(k)", "401(k)", "403(b)"]
            ),
            start_balance_roth=sum(
                acc.current_balance for acc in accounts.values() 
                if acc.account_type == "Roth IRA"
            ),
            start_balance_taxable=sum(
                acc.current_balance for acc in accounts.values() 
                if acc.account_type == "Taxable Brokerage"
            ),
        )
        
        # Calculate RMD if applicable
        if age >= 73:  # RMD Start Age
            for name, acc in accounts.items():
                if acc.account_type in ["Traditional IRA", "SEP IRA", "Solo 401(k)", "401(k)", "403(b)"]:
                    result.rmd_required += self.tax_calc.calculate_rmd(acc.current_balance, age)
            result.rmd_source = "Traditional IRA"
        
        # Calculate income for the year
        total_income = self.calculate_annual_income(year, income_streams)
        
        # Determine recommended conversion amount
        result.recommended_conversion = self._calculate_optimal_conversion(
            age, 
            result.start_balance_pretax,
            result.rmd_required,
            total_income,
            expenses.total_annual,
            scenario,
            tax_year
        )
        
        # Calculate tax on conversion
        pretax_ira = sum(
            acc.current_balance for acc in accounts.values()
            if acc.account_type in ["Traditional IRA", "SEP IRA"]
        )
        aftertax_ira = sum(
            acc.aftertax_basis for acc in accounts.values()
            if acc.account_type in ["Traditional IRA", "SEP IRA"]
        )
        
        taxable_conv, fed_tax, state_tax = self.tax_calc.calculate_roth_conversion_tax(
            result.recommended_conversion,
            pretax_ira,
            aftertax_ira,
            total_income,
            self.client.filing_status,
            tax_year
        )
        
        result.conversion_tax = fed_tax + state_tax
        
        # Calculate IRMAA impact
        magi = total_income + taxable_conv
        irmaa_adj, irmaa_tier = self.tax_calc.calculate_irmaa(magi, self.client.filing_status)
        result.irmaa_impact = irmaa_adj * 12  # Convert monthly to annual
        
        result.total_tax_paid = result.conversion_tax + result.irmaa_impact
        
        # Update account balances
        for name, acc in accounts.items():
            if result.recommended_conversion > 0 and acc.account_type in ["Traditional IRA", "SEP IRA"]:
                # Reduce pretax account, increase Roth
                withdrawal_amount = result.recommended_conversion
                acc.current_balance = max(0, acc.current_balance - withdrawal_amount)
            
            # Apply growth
            acc.current_balance = self.calculate_account_growth(
                acc.current_balance, 
                acc.growth_rate, 
                1,
                acc.annual_contribution
            )
        
        result.end_balance_pretax = sum(
            acc.current_balance for acc in accounts.values()
            if acc.account_type in ["Traditional IRA", "SEP IRA", "Solo 401(k)", "401(k)", "403(b)"]
        )
        result.end_balance_roth = sum(
            acc.current_balance for acc in accounts.values()
            if acc.account_type == "Roth IRA"
        ) + result.recommended_conversion
        
        result.end_balance_taxable = sum(
            acc.current_balance for acc in accounts.values()
            if acc.account_type == "Taxable Brokerage"
        )
        
        return result
    
    def _calculate_optimal_conversion(
        self,
        age: int,
        pretax_balance: float,
        rmd_required: float,
        total_income: float,
        annual_expenses: float,
        scenario: ScenarioSettings,
        tax_year: int
    ) -> float:
        """
        Calculate optimal Roth conversion amount based on scenario settings.
        
        Strategies:
        1. Fixed amount if annual_conversion_target is set
        2. Fill available tax bracket if fill_tax_bracket is True
        3. Avoid IRMAA if avoid_irmaa is True
        4. Return RMD amount + conversion opportunity
        """
        conversion = 0.0
        
        # Start with RMD (must be taken anyway)
        conversion = rmd_required
        
        # Add additional conversion based on strategy
        if scenario.annual_conversion_target:
            conversion = scenario.annual_conversion_target
        elif scenario.fill_tax_bracket:
            conversion = self._calculate_bracket_fill_amount(
                total_income, scenario, tax_year
            )
        
        # Constrain by available balance and settings
        conversion = min(conversion, pretax_balance - rmd_required)
        conversion = min(conversion, scenario.max_conversion_allowed)
        
        # Consider IRMAA if avoidance is prioritized
        if scenario.avoid_irmaa:
            conversion = min(conversion, self._calculate_max_before_irmaa(
                total_income, self.client.filing_status
            ))
        
        return max(0, conversion)
    
    def _calculate_bracket_fill_amount(
        self,
        current_income: float,
        scenario: ScenarioSettings,
        tax_year: int
    ) -> float:
        """Calculate how much can be converted to fill current tax bracket."""
        standard_ded = self.tax_calc.get_standard_deduction(self.client.filing_status)
        taxable_income = max(0, current_income - standard_ded)
        
        # Get brackets
        brackets = {
            "married_filing_jointly": [23200, 94300, 201050, 383900, 487450, 731200],
            "single": [11600, 47150, 100525, 191950, 243725, 609350],
        }
        
        bracket_limits = brackets.get(self.client.filing_status, [])
        
        # Find current bracket and remaining room
        for limit in bracket_limits:
            if taxable_income < limit:
                room_to_fill = limit - taxable_income
                return room_to_fill
        
        return 0  # At top bracket
    
    def _calculate_max_before_irmaa(
        self,
        current_income: float,
        filing_status: str
    ) -> float:
        """Calculate max conversion before triggering IRMAA."""
        irmaa_brackets = {
            "married_filing_jointly": [194000, 246000, 306000, 366000],
            "single": [97000, 123000, 153000, 183000],
        }
        
        thresholds = irmaa_brackets.get(filing_status, [194000])
        first_threshold = thresholds[0]
        
        if current_income >= first_threshold:
            return 0  # Already in IRMAA
        
        return first_threshold - current_income
    
    def run_full_simulation(
        self,
        scenario: ScenarioSettings,
        accounts: List[Account],
        income_streams: List[IncomeStream],
        expenses: Expenses
    ) -> ConversionStrategy:
        """
        Run complete simulation from current year to end_year.
        
        Returns:
            ConversionStrategy with year-by-year results
        """
        strategy = ConversionStrategy(
            scenario=scenario,
            client=self.client,
            accounts=accounts,
            income_streams=income_streams,
            expenses=expenses
        )
        
        # Create mutable copies of accounts
        sim_accounts = {acc.name: acc for acc in accounts}
        
        current_year = datetime.now().year
        current_age = self.client.current_age
        
        for year in range(scenario.start_year, scenario.end_year + 1):
            age = current_age + (year - current_year)
            
            # Stop simulation if person has passed (for modeling purposes)
            if age > 120:
                break
            
            result = self.simulate_year(
                year, age, sim_accounts, income_streams, 
                expenses, scenario, tax_year=2026  # Can parameterize
            )
            
            strategy.years.append(result)
            strategy.total_conversions += result.recommended_conversion
            strategy.total_taxes_paid += result.conversion_tax
            strategy.total_irmaa_costs += result.irmaa_impact
        
        # Calculate final values
        if strategy.years:
            last_year = strategy.years[-1]
            strategy.final_roth_value = last_year.end_balance_roth
            strategy.final_pretax_value = last_year.end_balance_pretax
            strategy.final_taxable_value = last_year.end_balance_taxable
            strategy.final_net_worth = (
                last_year.end_balance_roth + 
                last_year.end_balance_pretax + 
                last_year.end_balance_taxable
            )
        
        return strategy
