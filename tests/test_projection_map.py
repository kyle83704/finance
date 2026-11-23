"""Tests for the projection-map grid, sweet spots and taxable contributions."""

from datetime import datetime
import unittest

from src.models import Account, ClientProfile, Expenses, ScenarioSettings
from src.optimizer import ConversionOptimizer
from src.projection_map import (
    build_projection_map,
    conversion_grid,
    render_projection_map,
)
from src.simulator import ConversionSimulator


class TestConversionGrid(unittest.TestCase):

    def test_grid_includes_zero_max_and_is_ordered(self):
        grid = conversion_grid(100_000, 5)
        self.assertEqual(grid[0], 0.0)
        self.assertEqual(grid[-1], 100_000.0)
        self.assertEqual(grid, sorted(set(grid)))
        self.assertEqual(len(grid), 5)

    def test_zero_max_returns_only_zero(self):
        self.assertEqual(conversion_grid(0, 7), [0.0])


class TestProjectionMap(unittest.TestCase):

    def setUp(self):
        current_year = datetime.now().year
        self.client = ClientProfile(
            first_name='Map', last_name='Tester',
            birth_year=current_year - 65,
            state_residence='ID', filing_status='single',
        )
        self.accounts = [
            Account('IRA', 'Traditional IRA', 200_000, growth_rate=0.0),
            Account('Brokerage', 'Taxable Brokerage', 80_000,
                    cost_basis=80_000, growth_rate=0.0),
        ]
        self.base = ScenarioSettings(
            name='Map base',
            start_year=current_year,
            end_year=current_year + 3,
            tax_payment_source='taxable',
            deferred_tax_rate=0.22,
        )

    def _map(self, extra=0.0):
        return build_projection_map(
            self.client,
            self.base,
            self.accounts,
            [],
            Expenses(),
            conversion_targets=[0, 20_000, 40_000],
            extra_annual_funds=extra,
        )

    def test_map_has_years_tax_and_sweet_spots(self):
        result = self._map()
        self.assertEqual(len(result.points), 3)
        self.assertEqual(len(result.years), 4)
        self.assertTrue(result.sweet_spots)
        self.assertTrue(any(point.is_best_net for point in result.points))
        self.assertTrue(any(point.is_best_value for point in result.points))
        for point in result.points:
            self.assertEqual(len(point.after_tax_by_year), len(result.years))
            self.assertEqual(len(point.cumulative_tax_by_year), len(result.years))
            self.assertGreaterEqual(point.tax_load, 0.0)

    def test_added_funds_go_to_taxable_account(self):
        result = self._map(extra=5_000)
        self.assertEqual(result.added_funds_account, 'Brokerage')
        self.assertEqual(result.extra_annual_funds, 5_000)
        target = next(
            account for account in result.points[-1].strategy.accounts
            if account.name == 'Brokerage'
        )
        self.assertAlmostEqual(target.annual_contribution, 5_000)

    def test_added_funds_create_taxable_account_when_missing(self):
        accounts = [Account('IRA', 'Traditional IRA', 200_000, growth_rate=0.0)]
        result = build_projection_map(
            self.client,
            self.base,
            accounts,
            [],
            Expenses(),
            conversion_targets=[0, 20_000],
            extra_annual_funds=5_000,
        )
        self.assertEqual(result.added_funds_account, 'Added Funds (taxable)')
        target = next(
            account for account in result.points[-1].strategy.accounts
            if account.name == 'Added Funds (taxable)'
        )
        self.assertAlmostEqual(target.annual_contribution, 5_000)

    def test_added_funds_increase_after_tax_value(self):
        baseline = self._map(extra=0)
        added = self._map(extra=5_000)
        self.assertGreater(
            added.points[-1].final_after_tax_net_worth,
            baseline.points[-1].final_after_tax_net_worth,
        )

    def test_projection_map_renders_png(self):
        result = self._map(extra=5_000)
        image = render_projection_map(result)
        self.assertTrue(image.startswith(b'\x89PNG'))
        self.assertGreater(len(image), 10_000)

    def test_taxable_contribution_adds_cost_basis(self):
        simulator = ConversionSimulator(self.client)
        accounts = [Account(
            'Contributing Brokerage', 'Taxable Brokerage', 10_000,
            cost_basis=10_000, annual_contribution=2_000, growth_rate=0.0,
        )]
        scenario = ScenarioSettings(
            name='Contribution check',
            start_year=datetime.now().year,
            end_year=datetime.now().year,
            annual_conversion_target=0,
            max_conversion_allowed=0,
            fill_tax_bracket=False,
            avoid_irmaa=False,
        )
        simulator.simulate_year(
            year=datetime.now().year,
            age=self.client.current_age,
            accounts=accounts,
            income_streams=[],
            expenses=Expenses(),
            scenario=scenario,
        )
        self.assertAlmostEqual(accounts[0].current_balance, 12_000)
        self.assertAlmostEqual(accounts[0].cost_basis, 12_000)


if __name__ == '__main__':
    unittest.main()
