"""Core simulation engine for Roth conversion analysis."""

import copy
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from src.constants import (
    IRMAA_LOOKBACK_YEARS,
    MEDICARE_AGE,
    PRETAX_ACCOUNT_TYPES,
    ROTH_ACCOUNT_TYPES,
    TAXABLE_ACCOUNT_TYPES,
)
from src.models import (
    ClientProfile, Account, IncomeStream, Expenses,
    ScenarioSettings, ConversionResult, ConversionStrategy, LedgerEntry
)
from src.tax_calculator import TaxCalculator

AccountCollection = Union[Dict[str, Account], List[Account]]


class ConversionSimulator:
    """Main engine for simulating Roth conversion strategies."""

    def __init__(self, client: ClientProfile,
                 tax_calculator: Optional[TaxCalculator] = None):
        self.client = client
        self.tax_calc = tax_calculator or TaxCalculator(client.state_residence)
        self.rmd_start_age = self.tax_calc.rmd_start_age_for_birth_year(
            client.birth_year
        )

    # ------------------------------------------------------------------
    # Account helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _account_list(accounts: AccountCollection) -> List[Account]:
        """Return accounts as a list, accepting the legacy dict interface."""
        if isinstance(accounts, dict):
            return list(accounts.values())
        return list(accounts)

    @staticmethod
    def _add_account(accounts: AccountCollection, account: Account) -> Account:
        """Add a synthetic account, keeping dict keys unique when needed."""
        if isinstance(accounts, dict):
            base_name = account.name
            name = base_name
            suffix = 2
            while name in accounts:
                name = f"{base_name} ({suffix})"
                suffix += 1
            account.name = name
            accounts[name] = account
        else:
            accounts.append(account)
        return account

    @staticmethod
    def _is_pretax(account: Account) -> bool:
        return account.account_type in PRETAX_ACCOUNT_TYPES

    @staticmethod
    def _is_roth(account: Account) -> bool:
        return account.account_type in ROTH_ACCOUNT_TYPES

    @staticmethod
    def _is_taxable(account: Account) -> bool:
        return account.account_type in TAXABLE_ACCOUNT_TYPES

    def _pretax_balance(self, accounts: AccountCollection) -> float:
        return sum(acc.current_balance for acc in self._account_list(accounts)
                   if self._is_pretax(acc))

    def _withdraw_pretax(self, accounts: AccountCollection, amount: float) -> float:
        """Withdraw from all pre-tax accounts pro rata.

        RMDs and conversions both reduce the pre-tax bucket.  Withdrawing pro
        rata preserves the relative account balances instead of draining the
        first account in the list.
        """
        if amount <= 0:
            return 0.0

        pretax = [acc for acc in self._account_list(accounts)
                  if self._is_pretax(acc) and acc.current_balance > 0]
        total = sum(acc.current_balance for acc in pretax)
        if total <= 0:
            return 0.0

        amount = min(amount, total)
        for account in pretax:
            share = amount * (account.current_balance / total)
            account.current_balance = max(0.0, account.current_balance - share)
        return amount

    def _add_to_roth(self, accounts: AccountCollection, amount: float) -> None:
        if amount <= 0:
            return

        target = next((acc for acc in self._account_list(accounts)
                       if self._is_roth(acc)), None)
        if target is None:
            pretax = [acc for acc in self._account_list(accounts)
                      if self._is_pretax(acc)]
            total = sum(acc.current_balance for acc in pretax)
            source_growth = (
                sum(acc.current_balance * acc.growth_rate for acc in pretax) / total
                if total > 0 else 0.0
            )
            target = self._add_account(accounts, Account(
                name="Roth Conversion Account",
                account_type="Roth IRA",
                current_balance=0.0,
                growth_rate=source_growth,
            ))
        target.current_balance += amount

    def _add_rmd_proceeds(self, accounts: AccountCollection, amount: float) -> None:
        """Park RMD proceeds in a taxable account.

        This keeps gross net worth unchanged when the RMD is withdrawn: the
        money moves from the pre-tax bucket to the taxable bucket.  Taxes are
        tracked separately and deducted for the after-tax comparison.
        """
        if amount <= 0:
            return

        target = next((acc for acc in self._account_list(accounts)
                       if self._is_taxable(acc)), None)
        if target is None:
            target = self._add_account(accounts, Account(
                name="Taxable RMD Proceeds",
                account_type="Taxable Brokerage",
                current_balance=0.0,
                growth_rate=0.04,
            ))
        target.current_balance += amount
        target.cost_basis += amount

    def _sell_taxable(self, accounts: AccountCollection, amount: float) -> Tuple[float, float]:
        """Sell taxable assets pro rata and return (proceeds, realized gains)."""
        remaining = max(0.0, amount)
        proceeds = 0.0
        gains = 0.0
        for account in self._account_list(accounts):
            if remaining <= 0:
                break
            if not self._is_taxable(account) or account.current_balance <= 0:
                continue
            sold = min(remaining, account.current_balance)
            basis = min(max(0.0, account.cost_basis), account.current_balance)
            basis_ratio = basis / account.current_balance if account.current_balance else 1.0
            basis_removed = sold * basis_ratio
            gains += sold - basis_removed
            account.current_balance = max(0.0, account.current_balance - sold)
            account.cost_basis = min(
                max(0.0, account.cost_basis - basis_removed),
                account.current_balance,
            )
            proceeds += sold
            remaining -= sold
        return proceeds, gains

    def _withdraw_roth(self, accounts: AccountCollection, amount: float) -> float:
        """Reduce Roth balances pro rata for explicit tax withholding."""
        remaining = max(0.0, amount)
        taken = 0.0
        roth = [acc for acc in self._account_list(accounts)
                if self._is_roth(acc) and acc.current_balance > 0]
        total = sum(acc.current_balance for acc in roth)
        if total <= 0:
            return 0.0
        for account in roth:
            if remaining <= 0:
                break
            share = min(remaining, total * (account.current_balance / total))
            share = min(share, account.current_balance)
            account.current_balance -= share
            taken += share
            remaining -= share
        return taken

    def _deposit_cash(self, accounts: AccountCollection, amount: float) -> str:
        """Sweep residual cash into the first taxable account."""
        if amount <= 0:
            return ""
        target = next((acc for acc in self._account_list(accounts)
                       if self._is_taxable(acc)), None)
        if target is None:
            target = self._add_account(accounts, Account(
                name="Cash Reserve",
                account_type="Taxable Brokerage",
                current_balance=0.0,
                cost_basis=0.0,
                growth_rate=0.0,
            ))
        target.current_balance += amount
        target.cost_basis += amount
        return target.name

    # ------------------------------------------------------------------
    # Income
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize(value: str) -> str:
        return (value or "").strip().lower().replace("-", "_").replace(" ", "_")

    def _active_income(self, year: int, income_streams: List[IncomeStream]):
        """Yield (stream, amount) for streams active in ``year``."""
        current_year = datetime.now().year
        age_in_year = self.client.current_age + (year - current_year)

        for stream in income_streams:
            start_age = stream.start_age
            if self._normalize(stream.income_type) == "social_security" \
                    and stream.ss_claim_age:
                start_age = max(start_age, stream.ss_claim_age)

            if not (start_age <= age_in_year <= stream.end_age):
                continue

            years_elapsed = year - current_year
            amount = stream.annual_amount * (1 + stream.growth_rate) ** years_elapsed
            yield stream, amount

    def calculate_annual_income(
        self,
        year: int,
        income_streams: List[IncomeStream],
        taxable_only: bool = False,
    ) -> float:
        """Calculate total income for a given year.

        Social Security can use ``ss_claim_age`` as its effective start age.
        ``taxable_only`` excludes streams marked ``tax_free``.  Social Security
        is handled separately by ``calculate_income_components`` because its
        taxable portion depends on provisional income.
        """
        total_income = 0.0
        for stream, amount in self._active_income(year, income_streams):
            if taxable_only and self._normalize(stream.tax_treatment) == "tax_free":
                continue
            total_income += amount
        return total_income

    def calculate_income_components(
        self,
        year: int,
        income_streams: List[IncomeStream],
    ) -> Dict[str, float]:
        """Split income into ordinary, Social Security, qualified and tax-free."""
        components = {
            "ordinary": 0.0,
            "social_security": 0.0,
            "qualified_dividends": 0.0,
            "tax_free": 0.0,
            "total": 0.0,
        }

        for stream, amount in self._active_income(year, income_streams):
            income_type = self._normalize(stream.income_type)
            treatment = self._normalize(stream.tax_treatment)
            if income_type == "social_security" or treatment == "social_security":
                components["social_security"] += amount
            elif treatment == "tax_free":
                components["tax_free"] += amount
            elif treatment == "qualified_dividends":
                components["qualified_dividends"] += amount
            else:
                components["ordinary"] += amount
            components["total"] += amount

        return components

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

    # ------------------------------------------------------------------
    # Year simulation
    # ------------------------------------------------------------------
    def simulate_year(
        self,
        year: int,
        age: int,
        accounts: AccountCollection,
        income_streams: List[IncomeStream],
        expenses: Expenses,
        scenario: ScenarioSettings,
        tax_year: int = 2026,
        irmaa_magi: Optional[float] = None,
    ) -> ConversionResult:
        """Simulate one retirement year.

        Order of operations:
        1. Receive income and calculate the RMD; withdraw it pro rata from
           pre-tax accounts and hold the proceeds as cash.
        2. Determine taxable Social Security from provisional income.
        3. Determine and execute a Roth conversion from the remaining pre-tax
           balance.
        4. Recompute Social Security taxability and calculate baseline income
           tax, incremental conversion tax, gain tax and IRMAA.
        5. Pay living expenses from cash first, then taxable assets; report an
           explicit shortfall if neither is available.
        6. Settle tax from the selected source, record paid/unpaid amounts and
           reconcile every asset movement in the ledger.
        7. Apply growth to every account.

        ``irmaa_magi`` is the MAGI from two years earlier when the caller has it;
        otherwise current-year MAGI is used as a documented fallback.
        """
        result = ConversionResult(
            year=year,
            age=age,
            start_balance_pretax=sum(
                acc.current_balance for acc in self._account_list(accounts)
                if self._is_pretax(acc)
            ),
            start_balance_roth=sum(
                acc.current_balance for acc in self._account_list(accounts)
                if self._is_roth(acc)
            ),
            start_balance_taxable=sum(
                acc.current_balance for acc in self._account_list(accounts)
                if self._is_taxable(acc)
            ),
        )

        pretax_start = result.start_balance_pretax
        beginning_assets = sum(
            acc.current_balance for acc in self._account_list(accounts)
        )
        ledger: List[LedgerEntry] = []
        cash = 0.0
        taxes_paid = 0.0
        taxes_paid_from_assets = 0.0
        taxes_paid_external = 0.0
        withholding_from_conversion = 0.0
        taxable_withdrawals = 0.0
        realized_gains = 0.0
        external_used = 0.0

        def post(category: str, amount: float, account: str = "",
                 description: str = "") -> None:
            if abs(amount) > 1e-9:
                ledger.append(LedgerEntry(category, amount, account, description))

        result.beginning_assets = beginning_assets
        components = self.calculate_income_components(year, income_streams)
        total_stream_income = components["total"]
        cash += total_stream_income
        post("income", total_stream_income, "Cash", "Income streams received")
        spouse_age = None
        if self.client.spouse_current_age is not None:
            spouse_age = self.client.spouse_current_age + (
                year - datetime.now().year
            )

        # ------------------------------------------------------------------
        # Required Minimum Distribution
        # ------------------------------------------------------------------
        rmd_required = 0.0
        if age >= self.rmd_start_age and pretax_start > 0:
            for account in self._account_list(accounts):
                if self._is_pretax(account):
                    rmd_required += self.tax_calc.calculate_rmd(
                        account.current_balance, age,
                        start_age=self.rmd_start_age,
                    )
            rmd_required = min(rmd_required, pretax_start)
            if rmd_required > 0:
                result.rmd_required = self._withdraw_pretax(accounts, rmd_required)
                result.rmd_source = "All pre-tax accounts (pro rata)"
                cash += result.rmd_required
                post("rmd", -result.rmd_required, "Pre-tax accounts",
                     "RMD withdrawal")
                post("rmd", result.rmd_required, "Cash", "RMD proceeds received")
                result.notes.append(
                    f"RMD of ${result.rmd_required:,.0f} withdrawn; "
                    "proceeds received as cash and taxed this year."
                )

        # ------------------------------------------------------------------
        # Social Security and Roth conversion
        # ------------------------------------------------------------------
        other_income_for_ss = (
            components["ordinary"]
            + components["qualified_dividends"]
            + result.rmd_required
        )
        taxable_ss_baseline = self.tax_calc.calculate_taxable_social_security(
            components["social_security"],
            other_income_for_ss,
            self.client.filing_status,
        )
        ordinary_income = (
            components["ordinary"] + taxable_ss_baseline + result.rmd_required
        )
        qualified_income = components["qualified_dividends"]
        total_income_for_policy = ordinary_income + qualified_income

        conversion = self._calculate_optimal_conversion(
            age=age,
            pretax_balance=pretax_start,
            rmd_required=result.rmd_required,
            total_income=total_income_for_policy,
            annual_expenses=getattr(expenses, "total_annual", 0.0) or 0.0,
            scenario=scenario,
            tax_year=tax_year,
            qualified_income=qualified_income,
            spouse_age=spouse_age,
        )
        pre_conversion_pretax = self._pretax_balance(accounts)
        # Snapshot basis *before* the conversion reduces the accounts.
        pretax_taxable_balance = sum(
            max(0.0, acc.current_balance - acc.aftertax_basis)
            for acc in self._account_list(accounts) if self._is_pretax(acc)
        )
        aftertax_basis = sum(
            acc.aftertax_basis for acc in self._account_list(accounts)
            if self._is_pretax(acc)
        )
        conversion = min(conversion, pre_conversion_pretax)
        conversion = self._withdraw_pretax(accounts, conversion)
        result.recommended_conversion = conversion
        if conversion > 0:
            self._add_to_roth(accounts, conversion)
            post("conversion", -conversion, "Pre-tax accounts",
                 "Roth conversion")
            post("conversion", conversion, "Roth", "Roth conversion")
            result.notes.append(
                f"Converted ${conversion:,.0f} to Roth; "
                f"{scenario.target_objective} policy."
            )

        # ------------------------------------------------------------------
        # Taxes
        # ------------------------------------------------------------------
        # The pro-rata ratio and taxable amount use the snapshots captured
        # before the conversion.  Using post-conversion balances makes the
        # ratio zero (and the tax vanish) when the conversion empties the
        # account.  The pre-tax portion is balance minus non-deductible basis.
        taxable_conversion, _fed_tax, _state_tax = (
            self.tax_calc.calculate_roth_conversion_tax(
                conversion_amount=conversion,
                pretax_iira_balance=pretax_taxable_balance,
                aftertax_ira_balance=aftertax_basis,
                other_income=ordinary_income,
                filing_status=self.client.filing_status,
                year=tax_year,
                qualified_income=qualified_income,
                age=age,
                spouse_age=spouse_age,
            )
        )

        # A conversion raises provisional income, which can make more Social
        # Security taxable (the "tax torpedo").  Calculate the actual tax with
        # the conversion and take the difference from the no-conversion tax.
        other_income_after_ss = (
            components["ordinary"]
            + qualified_income
            + result.rmd_required
            + taxable_conversion
        )
        taxable_ss_after = self.tax_calc.calculate_taxable_social_security(
            components["social_security"],
            other_income_after_ss,
            self.client.filing_status,
        )
        ordinary_after = (
            components["ordinary"] + taxable_ss_after + result.rmd_required
        )
        result.income_tax = self.tax_calc.calculate_income_tax(
            total_income_for_policy,
            self.client.filing_status,
            tax_year,
            qualified_income=qualified_income,
            age=age,
            spouse_age=spouse_age,
        )
        after_conversion_tax = self.tax_calc.calculate_income_tax(
            ordinary_after + taxable_conversion + qualified_income,
            self.client.filing_status,
            tax_year,
            qualified_income=qualified_income,
            age=age,
            spouse_age=spouse_age,
        )
        result.conversion_tax = max(0.0, after_conversion_tax - result.income_tax)
        result.taxable_social_security = taxable_ss_after
        if components["social_security"] > 0:
            result.notes.append(
                f"${taxable_ss_after:,.0f} of "
                f"${components['social_security']:,.0f} Social Security is taxable."
            )
        if taxable_ss_after > taxable_ss_baseline + 1:
            result.notes.append(
                "The conversion increases the taxable Social Security portion "
                "through provisional income."
            )
        if taxable_conversion < conversion:
            result.notes.append(
                f"${conversion - taxable_conversion:,.0f} of the conversion "
                "was non-taxable under the pro-rata rule."
            )

        # IRMAA is a Medicare premium surcharge.  A 2026 premium uses MAGI from
        # 2024 (two-year lookback); the projection passes that prior MAGI in.
        magi = ordinary_after + taxable_conversion + qualified_income
        result.magi = magi
        premium_magi = irmaa_magi if irmaa_magi is not None else magi
        result.irmaa_magi = premium_magi
        if age >= MEDICARE_AGE:
            monthly_adjustment, _tier = self.tax_calc.calculate_irmaa(
                premium_magi, self.client.filing_status, tax_year
            )
            people = 1
            if self.client.filing_status == "married_filing_jointly":
                if spouse_age is None or spouse_age >= MEDICARE_AGE:
                    people = 2
            result.irmaa_impact = monthly_adjustment * 12 * people
            if result.irmaa_impact > 0:
                result.notes.append(
                    f"IRMAA surcharge of ${result.irmaa_impact:,.0f}/year "
                    f"for {people} Medicare enrollee(s)."
                )
            if irmaa_magi is not None:
                result.notes.append(
                    f"IRMAA based on {year - IRMAA_LOOKBACK_YEARS} MAGI of "
                    f"${irmaa_magi:,.0f}."
                )

        # ------------------------------------------------------------------
        # Spending settlement
        # ------------------------------------------------------------------
        annual_expenses = max(0.0, getattr(expenses, "total_annual", 0.0) or 0.0)
        spending_paid = 0.0
        spending_shortfall = 0.0
        if annual_expenses > 0:
            from_cash = min(cash, annual_expenses)
            cash -= from_cash
            spending_paid += from_cash
            post("spending", -from_cash, "Cash", "Living expenses")
            remaining_spending = annual_expenses - from_cash

            if remaining_spending > 0:
                sold, gains = self._sell_taxable(accounts, remaining_spending)
                if sold > 0:
                    taxable_withdrawals += sold
                    realized_gains += gains
                    spending_paid += sold
                    remaining_spending -= sold
                    post("spending", -sold, "Taxable accounts",
                         "Living expenses")

            if remaining_spending > 0:
                spending_shortfall = remaining_spending
                result.notes.append(
                    f"Spending shortfall of ${spending_shortfall:,.0f}; "
                    "no cash or taxable assets were available."
                )

        result.spending_paid = spending_paid
        result.spending_shortfall = spending_shortfall

        # Gains realized to fund spending are taxable in this year.
        gain_tax = self.tax_calc.calculate_capital_gains_tax(
            realized_gains,
            ordinary_after + taxable_conversion,
            qualified_income,
            self.client.filing_status,
            tax_year,
            age=age,
            spouse_age=spouse_age,
        )
        tax_due = (
            result.income_tax + result.conversion_tax
            + result.irmaa_impact + gain_tax
        )

        # ------------------------------------------------------------------
        # Tax settlement
        # ------------------------------------------------------------------
        external_available = max(
            0.0, float(scenario.external_tax_funding or 0.0)
        )

        def take_cash(amount: float) -> float:
            nonlocal cash, taxes_paid, taxes_paid_from_assets
            used = min(cash, max(0.0, amount))
            if used > 0:
                cash -= used
                taxes_paid += used
                taxes_paid_from_assets += used
                post("tax_payment", -used, "Cash", "Tax payment from cash")
            return used

        def take_roth(amount: float) -> float:
            nonlocal taxes_paid, taxes_paid_from_assets, withholding_from_conversion
            used = self._withdraw_roth(accounts, amount)
            if used > 0:
                taxes_paid += used
                taxes_paid_from_assets += used
                withholding_from_conversion += used
                post("tax_payment", -used, "Roth",
                     "Tax withheld from conversion")
            return used

        def take_taxable(amount: float) -> float:
            nonlocal taxes_paid, taxes_paid_from_assets
            nonlocal taxable_withdrawals, realized_gains
            sold, gains = self._sell_taxable(accounts, amount)
            if sold > 0:
                taxable_withdrawals += sold
                realized_gains += gains
                taxes_paid += sold
                taxes_paid_from_assets += sold
                post("tax_payment", -sold, "Taxable accounts",
                     "Tax payment from taxable assets")
            return sold

        def take_external(amount: float) -> float:
            nonlocal taxes_paid, taxes_paid_external, external_used
            used = min(
                max(0.0, amount),
                max(0.0, external_available - external_used),
            )
            if used > 0:
                external_used += used
                taxes_paid += used
                taxes_paid_external += used
                post("external_tax_funding", used, "External",
                     "Explicit external tax funding")
                post("tax_payment", -used, "External",
                     "Tax payment from external funds")
            return used

        source = (scenario.tax_payment_source or "cash").strip().lower()
        def settle_tax(amount: float) -> float:
            """Pay a liability using the scenario's ordered, capped sources."""
            remaining = max(0.0, amount)
            if source == "external":
                remaining -= take_external(remaining)
                remaining -= take_cash(remaining)
                remaining -= take_roth(remaining)
            elif source == "withhold":
                remaining -= take_roth(remaining)
                remaining -= take_cash(remaining)
                remaining -= take_external(remaining)
            elif source == "taxable":
                remaining -= take_taxable(remaining)
                remaining -= take_cash(remaining)
                remaining -= take_roth(remaining)
                remaining -= take_external(remaining)
            else:
                remaining -= take_cash(remaining)
                remaining -= take_roth(remaining)
                remaining -= take_external(remaining)
            return max(0.0, remaining)

        remaining_tax = settle_tax(tax_due)

        # A taxable sale used to pay tax can itself realize a gain. Recalculate
        # and settle that incremental liability until the feedback is below a
        # cent. The cap prevents malformed calculator inputs from looping.
        accounted_gain_tax = gain_tax
        for _ in range(20):
            total_gain_tax = self.tax_calc.calculate_capital_gains_tax(
                realized_gains,
                ordinary_after + taxable_conversion,
                qualified_income,
                self.client.filing_status,
                tax_year,
                age=age,
                spouse_age=spouse_age,
            )
            extra_gain_tax = max(0.0, total_gain_tax - accounted_gain_tax)
            if extra_gain_tax < 0.01:
                break
            accounted_gain_tax = total_gain_tax
            tax_due += extra_gain_tax
            remaining_tax += settle_tax(extra_gain_tax)
        else:
            result.notes.append(
                "Taxable-sale tax funding reached the iteration limit; "
                "review the remaining unpaid tax."
            )

        taxes_unpaid = max(0.0, remaining_tax)
        result.total_tax_paid = tax_due
        result.taxes_paid = taxes_paid
        result.taxes_paid_from_assets = taxes_paid_from_assets
        result.taxes_paid_external = taxes_paid_external
        result.taxes_unpaid = taxes_unpaid
        result.withholding_from_conversion = withholding_from_conversion
        result.taxable_withdrawals = taxable_withdrawals
        result.realized_gains = realized_gains
        result.external_tax_funding = external_used

        if taxes_unpaid > 0:
            result.notes.append(
                f"${taxes_unpaid:,.0f} of tax remains unpaid; no permitted "
                "funding source covered it."
            )
        if withholding_from_conversion > 0:
            result.notes.append(
                f"${withholding_from_conversion:,.0f} of tax was withheld from "
                "the Roth conversion; the Roth receives the net amount."
            )

        # No untracked cash is allowed to remain outside the ledger.
        if cash > 0:
            cash_target = self._deposit_cash(accounts, cash)
            if cash_target:
                post("cash_sweep", -cash, "Cash", "Residual cash sweep")
                post("cash_sweep", cash, cash_target, "Residual cash sweep")
            cash = 0.0

        # ------------------------------------------------------------------
        # Growth and ending balances
        # ------------------------------------------------------------------
        for account in self._account_list(accounts):
            before = account.current_balance
            contribution = max(0.0, account.annual_contribution or 0.0)
            after = self.calculate_account_growth(
                before,
                account.growth_rate,
                1,
                contribution,
            )
            account.current_balance = after
            if contribution:
                # Contributions to a taxable account add to its cost basis.
                # Without this, later sales would overstate realized gains.
                if self._is_taxable(account):
                    account.cost_basis += contribution
                post("contribution", contribution, account.name,
                     "Annual contribution")
            post("growth", after - before - contribution, account.name,
                 "Investment growth")

        result.end_balance_pretax = sum(
            acc.current_balance for acc in self._account_list(accounts)
            if self._is_pretax(acc)
        )
        result.end_balance_roth = sum(
            acc.current_balance for acc in self._account_list(accounts)
            if self._is_roth(acc)
        )
        result.end_balance_taxable = sum(
            acc.current_balance for acc in self._account_list(accounts)
            if self._is_taxable(acc)
        )
        result.ending_assets = sum(
            acc.current_balance for acc in self._account_list(accounts)
        )
        ledger_total = sum(entry.amount for entry in ledger)
        result.reconciliation_difference = (
            result.ending_assets - result.beginning_assets - ledger_total
        )
        result.ledger = ledger
        if abs(result.reconciliation_difference) > 1.0:
            result.notes.append(
                f"Ledger reconciliation difference: "
                f"${result.reconciliation_difference:,.2f}."
            )

        return result

    # ------------------------------------------------------------------
    # Conversion policy
    # ------------------------------------------------------------------
    def _calculate_optimal_conversion(
        self,
        age: int,
        pretax_balance: float,
        rmd_required: float,
        total_income: float,
        annual_expenses: float,
        scenario: ScenarioSettings,
        tax_year: int,
        qualified_income: float = 0.0,
        spouse_age: Optional[int] = None,
    ) -> float:
        """Determine the voluntary Roth conversion for the year.

        RMDs are handled separately by ``simulate_year``.  The conversion is
        only the *additional* amount moved to Roth after satisfying the RMD.
        """
        if pretax_balance <= 0:
            return 0.0

        conversion = 0.0
        if scenario.annual_conversion_target is not None:
            conversion = max(0.0, float(scenario.annual_conversion_target))
        elif scenario.fill_tax_bracket:
            conversion = self._calculate_bracket_fill_amount(
                total_income, scenario, tax_year,
                age=age,
                spouse_age=spouse_age,
                qualified_income=qualified_income,
            )

        if scenario.constraint_tax_rate is not None:
            conversion = min(
                conversion,
                self._calculate_room_under_rate(
                    total_income, scenario.constraint_tax_rate,
                    tax_year=tax_year,
                    age=age,
                    spouse_age=spouse_age,
                    qualified_income=qualified_income,
                ),
            )

        # Conversions at 63+ can affect IRMAA at 65 because of the two-year
        # lookback.  Younger conversions are not constrained by IRMAA.
        if scenario.avoid_irmaa and age >= MEDICARE_AGE - IRMAA_LOOKBACK_YEARS:
            conversion = min(
                conversion,
                self._calculate_max_before_irmaa(
                    total_income, self.client.filing_status, tax_year
                ),
            )

        available = max(0.0, pretax_balance - rmd_required)
        max_allowed = scenario.max_conversion_allowed
        if max_allowed is not None:
            available = min(available, max(0.0, float(max_allowed)))

        return max(0.0, min(conversion, available))

    def _calculate_bracket_fill_amount(
        self,
        current_income: float,
        scenario: ScenarioSettings,
        tax_year: int,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
        qualified_income: float = 0.0,
    ) -> float:
        """Amount that fills the client's current federal tax bracket."""
        standard_deduction = self.tax_calc.get_standard_deduction(
            self.client.filing_status, tax_year, age=age, spouse_age=spouse_age
        )
        taxable_income = max(0.0, current_income - standard_deduction)
        # Qualified dividends sit on top of ordinary income and use their own
        # rates, so only the ordinary portion determines the ordinary-bracket
        # room available for a conversion.
        qualified_taxable = min(max(0.0, qualified_income), taxable_income)
        ordinary_taxable = max(0.0, taxable_income - qualified_taxable)
        brackets = self.tax_calc.get_federal_brackets(
            self.client.filing_status, tax_year
        )

        # With no explicit ceiling, fill only the bracket the client is in
        # today.  Objectives with ``constraint_tax_rate`` may deliberately
        # reach through several lower brackets up to their ceiling.
        if scenario.constraint_tax_rate is None:
            for _lower, upper, _rate in brackets:
                if ordinary_taxable < upper:
                    if upper == float("inf"):
                        return 0.0
                    return max(0.0, upper - ordinary_taxable)
            return 0.0

        ceiling = 0.0
        for _lower, upper, rate in brackets:
            if rate <= scenario.constraint_tax_rate + 1e-9:
                ceiling = upper
            else:
                break

        if ceiling == float("inf"):
            return 0.0
        return max(0.0, ceiling - ordinary_taxable)

    def _calculate_room_under_rate(
        self,
        current_income: float,
        max_rate: float,
        tax_year: int = 2026,
        age: Optional[int] = None,
        spouse_age: Optional[int] = None,
        qualified_income: float = 0.0,
    ) -> float:
        """Room available before the federal marginal rate exceeds ``max_rate``.

        State tax is excluded from the comparison so the policy is expressed in
        familiar federal-bracket terms.  Returns ``inf`` when every bracket is
        within the requested rate.
        """
        standard_deduction = self.tax_calc.get_standard_deduction(
            self.client.filing_status, tax_year, age=age, spouse_age=spouse_age
        )
        taxable_income = max(0.0, current_income - standard_deduction)
        qualified_taxable = min(max(0.0, qualified_income), taxable_income)
        ordinary_taxable = max(0.0, taxable_income - qualified_taxable)
        brackets = self.tax_calc.get_federal_brackets(
            self.client.filing_status, tax_year
        )

        cap = 0.0
        saw_bracket = False
        for _lower, upper, rate in brackets:
            if rate <= max_rate + 1e-9:
                saw_bracket = True
                cap = upper
            else:
                break

        if not saw_bracket:
            return 0.0
        if cap == float("inf"):
            return float("inf")
        return max(0.0, cap - ordinary_taxable)

    def _calculate_max_before_irmaa(
        self,
        current_income: float,
        filing_status: str,
        tax_year: int = 2026,
    ) -> float:
        """Maximum conversion before crossing the first IRMAA threshold."""
        brackets = self.tax_calc.get_irmaa_brackets(filing_status, tax_year)

        for threshold, adjustment in brackets:
            if adjustment > 0:
                return max(0.0, threshold - current_income)

        return 0.0

    # ------------------------------------------------------------------
    # Full strategy
    # ------------------------------------------------------------------
    def run_full_simulation(
        self,
        scenario: ScenarioSettings,
        accounts: AccountCollection,
        income_streams: List[IncomeStream],
        expenses: Expenses
    ) -> ConversionStrategy:
        """Run a complete projection and return a ConversionStrategy.

        Accounts are deep-copied so running several scenarios never mutates the
        caller's accounts or lets one scenario start where the previous one
        ended.
        """
        strategy = ConversionStrategy(
            scenario=scenario,
            client=self.client,
            accounts=copy.deepcopy(accounts),
            income_streams=list(income_streams),
            expenses=expenses,
        )

        sim_accounts = copy.deepcopy(accounts)
        current_year = datetime.now().year
        current_age = self.client.current_age
        magi_history: Dict[int, float] = {}

        for year in range(scenario.start_year, scenario.end_year + 1):
            age = current_age + (year - current_year)

            if age > 120:
                break

            result = self.simulate_year(
                year=year,
                age=age,
                accounts=sim_accounts,
                income_streams=income_streams,
                expenses=expenses,
                scenario=scenario,
                tax_year=year,
                irmaa_magi=magi_history.get(year - IRMAA_LOOKBACK_YEARS),
            )
            magi_history[year] = result.magi

            strategy.years.append(result)
            strategy.total_conversions += result.recommended_conversion
            strategy.total_conversion_taxes += result.conversion_tax
            strategy.total_income_taxes += result.income_tax + result.conversion_tax
            strategy.total_taxes_paid += result.taxes_paid
            strategy.total_tax_liability += result.total_tax_paid
            strategy.total_taxes_unpaid += result.taxes_unpaid
            strategy.total_irmaa_costs += result.irmaa_impact
            strategy.total_spending += result.spending_paid
            strategy.total_spending_shortfall += result.spending_shortfall
            strategy.total_taxable_withdrawals += result.taxable_withdrawals
            strategy.total_realized_gains += result.realized_gains
            strategy.total_external_tax_funding += result.external_tax_funding

        if strategy.years:
            last_year = strategy.years[-1]
            strategy.final_roth_value = last_year.end_balance_roth
            strategy.final_pretax_value = last_year.end_balance_pretax
            strategy.final_taxable_value = last_year.end_balance_taxable
            strategy.final_net_worth = (
                last_year.end_balance_roth
                + last_year.end_balance_pretax
                + last_year.end_balance_taxable
            )
            deferred_rate = max(0.0, min(1.0, float(scenario.deferred_tax_rate)))
            strategy.final_deferred_tax_liability = (
                max(0.0, last_year.end_balance_pretax) * deferred_rate
            )

        return strategy
