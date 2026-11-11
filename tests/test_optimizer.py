"""Tests for objective generation, scenario isolation and ranking."""

import unittest
from datetime import datetime

from src.models import (
    Account, ClientProfile, Expenses, ScenarioSettings,
)
from src.optimizer import ConversionOptimizer, OBJECTIVE_POLICIES


class TestScenarioGeneration(unittest.TestCase):

    def setUp(self):
        current_year = datetime.now().year
        self.client = ClientProfile(
            first_name='Ada', last_name='Lovelace',
            birth_year=current_year - 66,
            state_residence='ID', filing_status='single',
        )
        self.optimizer = ConversionOptimizer(self.client)
        self.base = ScenarioSettings(
            name='Base', start_year=current_year, end_year=current_year + 9,
        )

    def test_every_objective_has_a_scenario(self):
        scenarios = self.optimizer.generate_scenarios(
            self.base, list(OBJECTIVE_POLICIES)
        )
        self.assertEqual(len(scenarios), len(OBJECTIVE_POLICIES))
        self.assertEqual(
            [scenario.target_objective for scenario in scenarios],
            list(OBJECTIVE_POLICIES),
        )
        for scenario in scenarios:
            self.assertEqual(scenario.start_year, self.base.start_year)
            self.assertEqual(scenario.end_year, self.base.end_year)
            self.assertTrue(scenario.description)

    def test_policy_settings_are_distinct(self):
        scenarios = self.optimizer.generate_scenarios(
            self.base, list(OBJECTIVE_POLICIES)
        )
        signatures = {
            (
                scenario.fill_tax_bracket,
                scenario.avoid_irmaa,
                scenario.annual_conversion_target,
                scenario.constraint_tax_rate,
            )
            for scenario in scenarios
        }
        self.assertEqual(len(signatures), len(scenarios))

    def test_fixed_amount_scenarios_are_exact_targets(self):
        scenarios = self.optimizer.generate_scenarios(
            self.base, ['Balanced Growth'], conversion_amounts=[25000]
        )
        fixed = scenarios[-1]
        self.assertEqual(fixed.annual_conversion_target, 25000)
        self.assertEqual(fixed.max_conversion_allowed, 25000)
        self.assertFalse(fixed.fill_tax_bracket)
        self.assertFalse(fixed.avoid_irmaa)


class TestScenarioIsolation(unittest.TestCase):

    def setUp(self):
        current_year = datetime.now().year
        self.client = ClientProfile(
            first_name='Grace', last_name='Hopper',
            birth_year=current_year - 60,
            state_residence='ID', filing_status='single',
        )
        self.optimizer = ConversionOptimizer(self.client)
        self.accounts = [
            Account('Traditional IRA', 'Traditional IRA', 500000,
                    pretax_basis=500000, growth_rate=0.0),
        ]
        self.income = []
        self.expenses = Expenses()

    def _scenario(self, name, target):
        year = datetime.now().year
        return ScenarioSettings(
            name=name,
            start_year=year,
            end_year=year,
            target_objective='Fixed Amount',
            annual_conversion_target=target,
            max_conversion_allowed=target,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )

    def test_order_does_not_change_results_or_mutate_accounts(self):
        small = self._scenario('Small', 10000)
        large = self._scenario('Large', 100000)

        first = self.optimizer.run_scenario_comparison(
            [small, large], self.accounts, self.income, self.expenses
        )
        second = self.optimizer.run_scenario_comparison(
            [large, small], self.accounts, self.income, self.expenses
        )

        self.assertAlmostEqual(self.accounts[0].current_balance, 500000)
        self.assertAlmostEqual(first[0].final_pretax_value, 490000)
        self.assertAlmostEqual(first[1].final_pretax_value, 400000)
        self.assertAlmostEqual(second[1].final_pretax_value, 490000)
        self.assertAlmostEqual(second[0].final_pretax_value, 400000)


class TestComparisonAndRanking(unittest.TestCase):

    def setUp(self):
        current_year = datetime.now().year
        self.client = ClientProfile(
            first_name='Katherine', last_name='Johnson',
            birth_year=current_year - 60,
            state_residence='ID', filing_status='single',
        )
        self.optimizer = ConversionOptimizer(self.client)
        scenario = ScenarioSettings(
            name='Convert', start_year=current_year, end_year=current_year,
            annual_conversion_target=10000,
            max_conversion_allowed=10000,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )
        self.strategy = self.optimizer.run_scenario_comparison(
            [scenario],
            [Account('IRA', 'Traditional IRA', 100000, growth_rate=0.0)],
            [],
            Expenses(),
        )[0]

    def test_comparison_uses_total_taxes_and_after_tax_net_worth(self):
        frame = self.optimizer.compare_strategies([self.strategy])
        row = frame.iloc[0]

        self.assertEqual(
            row['Total Taxes Paid'],
            f"${self.strategy.total_taxes_paid:,.0f}",
        )
        self.assertEqual(
            row['Net After All Taxes'],
            f"${self.strategy.final_after_tax_net_worth:,.0f}",
        )

    def test_ranking_minimizes_taxes_and_maximizes_after_tax_worth(self):
        low_tax = self.strategy
        high_tax = type(self.strategy)(
            scenario=ScenarioSettings(
                name='High Tax', start_year=2026, end_year=2026,
            ),
            client=self.client,
            accounts=[],
            income_streams=[],
            expenses=Expenses(),
            total_taxes_paid=low_tax.total_taxes_paid + 1000,
            final_net_worth=low_tax.final_net_worth - 30_000,
        )

        tax_ranking = self.optimizer.get_ranked_strategies(
            [high_tax, low_tax], 'Total Taxes Paid'
        )
        self.assertIs(tax_ranking[0][0], low_tax)

        worth_ranking = self.optimizer.get_ranked_strategies(
            [low_tax, high_tax], 'After-Tax Net Worth'
        )
        self.assertIs(worth_ranking[0][0], low_tax)


if __name__ == '__main__':
    unittest.main()
