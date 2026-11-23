"""Tests for historical, resampled, stress and low-discrepancy paths."""

import os
import tempfile
import unittest
from datetime import datetime

from src.market_simulation import (
    METHODS,
    HistoricalObservation,
    apply_return_path,
    block_bootstrap_paths,
    empirical_sobol_paths,
    historical_windows,
    load_historical_csv,
    run_return_paths,
    sensitivity_grid,
    stress_path,
)
from src.models import Account, ClientProfile, Expenses, ScenarioSettings
from src.simulator import ConversionSimulator


class TestPathGeneration(unittest.TestCase):

    def setUp(self):
        self.history = [
            HistoricalObservation(2000, -0.10, 0.03, 0.05),
            HistoricalObservation(2001, 0.20, 0.02, 0.04),
            HistoricalObservation(2002, -0.30, 0.01, 0.03),
            HistoricalObservation(2003, 0.15, 0.025, 0.035),
        ]

    def test_csv_loader_parses_percentages_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(
                    "year,portfolio_return,inflation_rate,interest_rate\n"
                    "2001,20%,2%,4%\n2000,-0.10,0.03,0.05\n"
                )
            loaded = load_historical_csv(path)
        self.assertEqual([item.year for item in loaded], [2000, 2001])
        self.assertAlmostEqual(loaded[1].portfolio_return, 0.20)

    def test_historical_windows_require_contiguous_years(self):
        windows = historical_windows(self.history, 3)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0].source_years, [2000, 2001, 2002])
        self.assertEqual(windows[0].returns, [-0.10, 0.20, -0.30])

    def test_block_bootstrap_is_reproducible_and_uses_observations(self):
        first = block_bootstrap_paths(self.history, 7, 2, block_size=2, seed=9)
        second = block_bootstrap_paths(self.history, 7, 2, block_size=2, seed=9)
        self.assertEqual(first, second)
        observed = {item.portfolio_return for item in self.history}
        self.assertTrue(set(first[0].returns).issubset(observed))

    def test_stress_and_sensitivity_validation(self):
        path = stress_path("Crash", [-0.40, -0.10, 0.15], [0.07, 0.06, 0.04])
        self.assertEqual(path.method, "stress")
        grid = sensitivity_grid(inflation=[0.02, 0.04], returns=[0.03, 0.06])
        self.assertEqual(len(grid), 4)
        with self.assertRaises(ValueError):
            stress_path("Impossible", [-1.01])

    def test_empirical_sobol_paths_are_deterministic_and_bounded(self):
        first = empirical_sobol_paths(self.history, horizon=3, count=4)
        second = empirical_sobol_paths(self.history, horizon=3, count=4)
        self.assertEqual(first, second)
        observed = {item.portfolio_return for item in self.history}
        self.assertTrue(all(set(path.returns).issubset(observed) for path in first))

    def test_complex_system_methods_are_not_misrepresented(self):
        self.assertEqual(METHODS["agent_based"].status, "out_of_scope")
        self.assertEqual(METHODS["system_dynamics"].status, "out_of_scope")
        self.assertEqual(METHODS["discrete_event"].status, "out_of_scope")


class TestPathIntegration(unittest.TestCase):

    def test_return_and_inflation_path_feed_normal_ledger_simulator(self):
        current_year = datetime.now().year
        client = ClientProfile(
            "Path", "Test", current_year - 60,
            state_residence="ID", filing_status="single",
        )
        base = ScenarioSettings(
            name="Historical",
            start_year=current_year,
            end_year=current_year + 1,
            annual_conversion_target=0,
            max_conversion_allowed=0,
            avoid_irmaa=False,
            fill_tax_bracket=False,
        )
        scenario = apply_return_path(
            base,
            stress_path("Two year", [-0.50, 0.20], [0.10, 0.0]),
        )
        strategy = ConversionSimulator(client).run_full_simulation(
            scenario,
            [Account("Brokerage", "Taxable Brokerage", 100_000,
                     cost_basis=100_000, growth_rate=0.99)],
            [],
            Expenses(),
        )

        self.assertAlmostEqual(strategy.years[0].ending_assets, 50_000, delta=1)
        self.assertAlmostEqual(strategy.years[1].ending_assets, 60_000, delta=1)
        for year in strategy.years:
            self.assertAlmostEqual(
                year.beginning_assets + sum(entry.amount for entry in year.ledger),
                year.ending_assets,
                delta=0.01,
            )

    def test_inflation_path_escalates_next_year_spending(self):
        current_year = datetime.now().year
        client = ClientProfile(
            "Inflation", "Test", current_year - 60,
            state_residence="ID", filing_status="single",
        )
        scenario = ScenarioSettings(
            name="Inflation",
            start_year=current_year,
            end_year=current_year + 1,
            annual_conversion_target=0,
            max_conversion_allowed=0,
            avoid_irmaa=False,
            fill_tax_bracket=False,
            annual_return_path=[0.0, 0.0],
            annual_inflation_path=[0.10, 0.0],
            return_method="historical",
        )
        strategy = ConversionSimulator(client).run_full_simulation(
            scenario,
            [Account("Brokerage", "Taxable Brokerage", 100_000,
                     cost_basis=100_000, growth_rate=0.0)],
            [],
            Expenses(housing=10_000),
        )
        self.assertAlmostEqual(strategy.years[0].spending_paid, 10_000, delta=1)
        self.assertAlmostEqual(strategy.years[1].spending_paid, 11_000, delta=1)

    def test_batch_paths_are_independent(self):
        current_year = datetime.now().year
        client = ClientProfile(
            "Batch", "Test", current_year - 60,
            state_residence="ID", filing_status="single",
        )
        scenario = ScenarioSettings(
            name="Batch", start_year=current_year, end_year=current_year,
            annual_conversion_target=0, max_conversion_allowed=0,
            avoid_irmaa=False, fill_tax_bracket=False,
        )
        strategies = run_return_paths(
            ConversionSimulator(client), scenario,
            [stress_path("Loss", [-0.10]), stress_path("Gain", [0.10])],
            [Account("Brokerage", "Taxable Brokerage", 100_000,
                     cost_basis=100_000, growth_rate=0.0)],
            [], Expenses(),
        )
        self.assertAlmostEqual(strategies[0].final_net_worth, 90_000, delta=1)
        self.assertAlmostEqual(strategies[1].final_net_worth, 110_000, delta=1)


if __name__ == "__main__":
    unittest.main()
