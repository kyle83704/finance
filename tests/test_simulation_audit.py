"""Deterministic 1,000-case randomized audit of simulation invariants."""

import copy
import math
import random
import unittest
from datetime import datetime

from src.models import Account, ClientProfile, Expenses, IncomeStream, ScenarioSettings
from src.simulator import ConversionSimulator


class TestThousandCaseSimulationAudit(unittest.TestCase):

    def test_one_thousand_varied_plans_preserve_financial_identities(self):
        rng = random.Random(20261123)
        current_year = datetime.now().year

        for case in range(1_000):
            age = rng.randint(55, 80)
            filing_status = rng.choice(["single", "married_filing_jointly"])
            client = ClientProfile(
                first_name="Audit",
                last_name=str(case),
                birth_year=current_year - age,
                spouse_birth_year=(current_year - max(50, age - rng.randint(-3, 5))
                                   if filing_status == "married_filing_jointly"
                                   else None),
                state_residence=rng.choice(["ID", "CA", "TX", "FL", "NY"]),
                filing_status=filing_status,
            )
            pretax = rng.uniform(0, 1_500_000)
            roth = rng.uniform(0, 800_000)
            taxable = rng.uniform(0, 1_000_000)
            basis_ratio = rng.random()
            accounts = [
                Account("Traditional", "Traditional IRA", pretax,
                        growth_rate=rng.uniform(0.0, 0.10)),
                Account("Roth", "Roth IRA", roth,
                        growth_rate=rng.uniform(0.0, 0.10)),
                Account("Brokerage", "Taxable Brokerage", taxable,
                        cost_basis=taxable * basis_ratio,
                        growth_rate=rng.uniform(0.0, 0.10)),
            ]
            original_accounts = copy.deepcopy(accounts)
            horizon = rng.randint(1, 12)
            target = rng.uniform(0, 120_000)
            external_cap = rng.uniform(0, 40_000)
            scenario = ScenarioSettings(
                name=f"Audit {case}",
                start_year=current_year,
                end_year=current_year + horizon - 1,
                annual_conversion_target=target,
                max_conversion_allowed=target,
                avoid_irmaa=rng.choice([True, False]),
                fill_tax_bracket=False,
                tax_payment_source=rng.choice(
                    ["cash", "withhold", "taxable", "external"]
                ),
                external_tax_funding=external_cap,
                deferred_tax_rate=rng.uniform(0.0, 0.40),
                annual_return_path=[rng.uniform(-0.60, 0.45)
                                    for _ in range(horizon)],
                annual_inflation_path=[rng.uniform(-0.02, 0.12)
                                       for _ in range(horizon)],
                return_method="audit",
            )
            incomes = [IncomeStream(
                "Pension", "Pension", rng.uniform(0, 90_000),
                start_age=50, end_age=105, growth_rate=rng.uniform(0.0, 0.04),
            )]
            expenses = Expenses(
                housing=rng.uniform(0, 45_000),
                healthcare=rng.uniform(0, 25_000),
                discretionary=rng.uniform(0, 30_000),
            )

            strategy = ConversionSimulator(client).run_full_simulation(
                scenario, accounts, incomes, expenses
            )

            self.assertEqual(accounts, original_accounts, f"case {case}: mutation")
            self.assertLessEqual(len(strategy.years), horizon)
            for year in strategy.years:
                values = (
                    year.beginning_assets, year.ending_assets,
                    year.total_tax_paid, year.taxes_paid, year.taxes_unpaid,
                    year.spending_paid, year.spending_shortfall,
                    year.reconciliation_difference,
                )
                self.assertTrue(all(math.isfinite(value) for value in values),
                                f"case {case}, year {year.year}: non-finite")
                self.assertGreaterEqual(year.ending_assets, -0.01)
                self.assertGreaterEqual(year.end_balance_pretax, -0.01)
                self.assertGreaterEqual(year.end_balance_roth, -0.01)
                self.assertGreaterEqual(year.end_balance_taxable, -0.01)
                self.assertAlmostEqual(
                    year.beginning_assets + sum(entry.amount for entry in year.ledger),
                    year.ending_assets, delta=0.02,
                    msg=f"case {case}, year {year.year}: ledger",
                )
                self.assertAlmostEqual(
                    year.taxes_paid + year.taxes_unpaid,
                    year.total_tax_paid, delta=0.05,
                    msg=f"case {case}, year {year.year}: tax identity",
                )
                self.assertAlmostEqual(
                    year.taxes_paid_from_assets + year.taxes_paid_external,
                    year.taxes_paid, delta=0.02,
                    msg=f"case {case}, year {year.year}: payment sources",
                )
                self.assertLessEqual(year.taxes_paid_external, external_cap + 0.01)
                self.assertLessEqual(
                    year.recommended_conversion,
                    year.start_balance_pretax + 0.01,
                )

            self.assertAlmostEqual(
                strategy.total_taxes_paid + strategy.total_taxes_unpaid,
                strategy.total_tax_liability,
                delta=0.05 * max(1, len(strategy.years)),
                msg=f"case {case}: strategy tax identity",
            )
            self.assertAlmostEqual(
                strategy.final_roth_value + strategy.final_pretax_value
                + strategy.final_taxable_value,
                strategy.final_net_worth,
                delta=0.02,
                msg=f"case {case}: final balances",
            )


if __name__ == "__main__":
    unittest.main()
