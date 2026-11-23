"""Cash-flow, funding and provenance tests for the Phase B accounting model."""

import unittest
from datetime import datetime

from src.models import Account, ClientProfile, Expenses, IncomeStream, ScenarioSettings
from src.rules import get_rule, get_rules, registry_summary
from src.simulator import ConversionSimulator
from src.tax_calculator import TaxCalculator


def _client(age=60):
    current_year = datetime.now().year
    return ClientProfile(
        first_name="Test",
        last_name="Client",
        birth_year=current_year - age,
        state_residence="ID",
        filing_status="single",
    )


def _scenario(**overrides):
    current_year = datetime.now().year
    values = dict(
        name="Phase B Test",
        start_year=current_year,
        end_year=current_year,
        annual_conversion_target=0,
        max_conversion_allowed=0,
        fill_tax_bracket=False,
        avoid_irmaa=False,
    )
    values.update(overrides)
    return ScenarioSettings(**values)


class TestCashFlowAccounting(unittest.TestCase):

    def test_spending_reduces_assets_and_tax_is_paid_from_cash(self):
        client = _client()
        accounts = [
            Account(
                name="Brokerage",
                account_type="Taxable Brokerage",
                current_balance=100_000,
                cost_basis=100_000,
                growth_rate=0.0,
            )
        ]
        income = [
            IncomeStream(
                name="Pension",
                income_type="Pension",
                annual_amount=30_000,
                start_age=50,
                end_age=100,
                growth_rate=0.0,
            )
        ]
        result = ConversionSimulator(client).run_full_simulation(
            _scenario(tax_payment_source="cash"),
            accounts,
            income,
            Expenses(housing=20_000),
        ).years[0]

        self.assertAlmostEqual(result.spending_paid, 20_000, delta=1)
        self.assertAlmostEqual(result.spending_shortfall, 0, delta=1)
        self.assertGreater(result.taxes_paid, 0)
        self.assertAlmostEqual(
            result.taxes_paid + result.taxes_unpaid,
            result.total_tax_paid,
            delta=1,
        )
        self.assertAlmostEqual(
            result.ending_assets,
            100_000 + 30_000 - result.spending_paid - result.taxes_paid,
            delta=1,
        )
        self.assertAlmostEqual(
            result.beginning_assets + sum(e.amount for e in result.ledger),
            result.ending_assets,
            delta=1,
        )

    def test_withholding_reduces_roth_and_does_not_create_cash(self):
        result = ConversionSimulator(_client()).run_full_simulation(
            _scenario(
                annual_conversion_target=50_000,
                max_conversion_allowed=50_000,
                tax_payment_source="withhold",
            ),
            [Account("IRA", "Traditional IRA", 100_000, growth_rate=0.0)],
            [],
            Expenses(),
        ).years[0]

        self.assertGreater(result.withholding_from_conversion, 0)
        self.assertAlmostEqual(
            result.withholding_from_conversion, result.taxes_paid, delta=1
        )
        self.assertAlmostEqual(result.end_balance_pretax, 50_000, delta=1)
        self.assertAlmostEqual(
            result.end_balance_roth,
            50_000 - result.withholding_from_conversion,
            delta=1,
        )
        self.assertAlmostEqual(result.taxes_unpaid, 0, delta=1)
        self.assertAlmostEqual(
            result.beginning_assets + sum(e.amount for e in result.ledger),
            result.ending_assets,
            delta=1,
        )

    def test_taxable_sale_uses_cost_basis_and_reports_gains(self):
        result = ConversionSimulator(_client()).run_full_simulation(
            _scenario(
                tax_payment_source="external",
                external_tax_funding=100_000,
            ),
            [
                Account(
                    name="Brokerage",
                    account_type="Taxable Brokerage",
                    current_balance=100_000,
                    cost_basis=60_000,
                    growth_rate=0.0,
                )
            ],
            [
                IncomeStream(
                    name="Pension",
                    income_type="Pension",
                    annual_amount=20_000,
                    start_age=50,
                    end_age=100,
                    growth_rate=0.0,
                )
            ],
            Expenses(housing=50_000),
        ).years[0]

        self.assertAlmostEqual(result.spending_paid, 50_000, delta=1)
        self.assertAlmostEqual(result.taxable_withdrawals, 30_000, delta=1)
        self.assertAlmostEqual(result.realized_gains, 12_000, delta=1)
        self.assertAlmostEqual(result.end_balance_taxable, 70_000, delta=1)
        self.assertAlmostEqual(result.taxes_unpaid, 0, delta=1)
        self.assertAlmostEqual(
            result.taxes_paid_external, result.total_tax_paid, delta=1
        )
        self.assertAlmostEqual(result.external_tax_funding, result.total_tax_paid,
                               delta=1)

    def test_external_funding_is_capped_and_unpaid_tax_is_explicit(self):
        result = ConversionSimulator(_client()).run_full_simulation(
            _scenario(
                tax_payment_source="external",
                external_tax_funding=1_000,
            ),
            [
                Account(
                    name="Brokerage",
                    account_type="Taxable Brokerage",
                    current_balance=100_000,
                    cost_basis=0.0,
                    growth_rate=0.0,
                )
            ],
            [],
            Expenses(housing=100_000),
        ).years[0]

        self.assertAlmostEqual(result.spending_paid, 100_000, delta=1)
        self.assertAlmostEqual(result.external_tax_funding, 1_000, delta=1)
        self.assertAlmostEqual(result.taxes_paid_external, 1_000, delta=1)
        self.assertGreater(result.taxes_unpaid, 0)
        self.assertAlmostEqual(
            result.taxes_paid + result.taxes_unpaid,
            result.total_tax_paid,
            delta=1,
        )
        self.assertAlmostEqual(
            result.beginning_assets + sum(e.amount for e in result.ledger),
            result.ending_assets,
            delta=1,
        )

    def test_taxable_tax_funding_settles_tax_on_its_own_gains(self):
        result = ConversionSimulator(_client()).run_full_simulation(
            _scenario(
                annual_conversion_target=50_000,
                max_conversion_allowed=50_000,
                tax_payment_source="taxable",
            ),
            [
                Account("IRA", "Traditional IRA", 50_000, growth_rate=0.0),
                Account(
                    "Brokerage",
                    "Taxable Brokerage",
                    100_000,
                    cost_basis=0.0,
                    growth_rate=0.0,
                ),
            ],
            [],
            Expenses(),
        ).years[0]

        self.assertGreater(result.realized_gains, 0)
        self.assertAlmostEqual(result.taxes_unpaid, 0, delta=0.01)
        self.assertAlmostEqual(
            result.taxes_paid, result.total_tax_paid, delta=0.01
        )
        self.assertAlmostEqual(
            result.beginning_assets + sum(e.amount for e in result.ledger),
            result.ending_assets,
            delta=0.01,
        )

    def test_deferred_tax_reserve_reduces_after_tax_net_worth(self):
        strategy = ConversionSimulator(_client()).run_full_simulation(
            _scenario(deferred_tax_rate=0.22),
            [Account("IRA", "Traditional IRA", 100_000, growth_rate=0.0)],
            [],
            Expenses(),
        )

        self.assertAlmostEqual(strategy.final_net_worth, 100_000, delta=1)
        self.assertAlmostEqual(
            strategy.final_deferred_tax_liability, 22_000, delta=1
        )
        self.assertAlmostEqual(
            strategy.final_after_tax_net_worth, 78_000, delta=1
        )
        self.assertAlmostEqual(strategy.total_taxes_unpaid, 0, delta=1)


class TestRulesAndGainTax(unittest.TestCase):

    def test_registry_separates_verified_rules_from_assumptions(self):
        self.assertEqual(
            get_rule("federal_brackets_2026_single").status, "verified"
        )
        self.assertEqual(get_rule("post_2026_indexing").status, "assumption")
        unsupported = {rule.rule_id for rule in get_rules("unsupported")}
        self.assertIn("mfs_hoh_federal_brackets", unsupported)
        self.assertIn("obbba_senior_deduction", unsupported)
        self.assertGreater(registry_summary().get("verified", 0), 0)

    def test_capital_gains_tax_is_incremental_and_uses_qualified_rates(self):
        calculator = TaxCalculator("ID")
        baseline = calculator.calculate_income_tax(50_000, "single", 2026)
        with_gain = calculator.calculate_income_tax(
            60_000, "single", 2026, qualified_income=10_000
        )
        self.assertAlmostEqual(
            calculator.calculate_capital_gains_tax(
                10_000, 50_000, 0.0, "single", 2026
            ),
            with_gain - baseline,
            delta=1,
        )
        self.assertEqual(
            calculator.calculate_capital_gains_tax(
                0.0, 50_000, 0.0, "single", 2026
            ),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
