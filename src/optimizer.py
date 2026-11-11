"""Multi-scenario optimizer for Roth conversion strategies."""

from typing import List, Dict, Tuple

import pandas as pd

from src.models import (
    ConversionStrategy, ScenarioSettings, ClientProfile,
    Account, IncomeStream, Expenses,
)
from src.simulator import ConversionSimulator
from src.tax_calculator import TaxCalculator


# Each objective gets a deliberately different conversion policy.  Earlier
# versions only changed a name, so several objectives produced identical
# results (and the GUI bypassed this table entirely).
OBJECTIVE_POLICIES = {
    "Maximize Roth Value": {
        "description": "Convert through the 32% federal bracket and accept IRMAA "
                       "to move the most money into tax-free Roth assets.",
        "fill_tax_bracket": True,
        "avoid_irmaa": False,
        "annual_conversion_target": None,
        "constraint_tax_rate": 0.32,
    },
    "Maximize Inheritance": {
        "description": "Convert aggressively while keeping the federal marginal "
                       "rate at 24% or less for tax-efficient legacy assets.",
        "fill_tax_bracket": True,
        "avoid_irmaa": False,
        "annual_conversion_target": None,
        "constraint_tax_rate": 0.24,
    },
    "Maximize Gross Net Worth": {
        "description": "Fill the 22% federal bracket without letting IRMAA limit "
                       "growth of the gross estate.",
        "fill_tax_bracket": True,
        "avoid_irmaa": False,
        "annual_conversion_target": None,
        "constraint_tax_rate": 0.22,
    },
    "Balanced Growth": {
        "description": "Fill the 22% bracket while staying under the first IRMAA "
                       "threshold—a middle path between taxes and growth.",
        "fill_tax_bracket": True,
        "avoid_irmaa": True,
        "annual_conversion_target": None,
        "constraint_tax_rate": 0.22,
    },
    "Minimize Tax Paid": {
        "description": "Make no voluntary conversions; take only RMDs and let the "
                       "pre-tax balance compound.",
        "fill_tax_bracket": False,
        "avoid_irmaa": True,
        "annual_conversion_target": 0,
        "constraint_tax_rate": None,
    },
    "Minimize IRMAA Impact": {
        "description": "Stay within the current bracket and never cross into a "
                       "Medicare premium surcharge tier.",
        "fill_tax_bracket": True,
        "avoid_irmaa": True,
        "annual_conversion_target": None,
        "constraint_tax_rate": None,
    },
}


class ConversionOptimizer:
    """Generates and compares multiple conversion strategies."""

    def __init__(self, client: ClientProfile):
        self.client = client
        self.tax_calc = TaxCalculator(client.state_residence)
        self.simulator = ConversionSimulator(client, self.tax_calc)

    def generate_scenarios(
        self,
        base_scenario: ScenarioSettings,
        objectives: List[str],
        conversion_amounts: List[float] = None
    ) -> List[ScenarioSettings]:
        """Generate one policy-driven scenario per selected objective.

        Each policy is explicit and testable.  The GUI uses this method so the
        scenario it runs is the same one the optimizer documents and tests.
        """
        scenarios: List[ScenarioSettings] = []

        for objective in objectives:
            policy = OBJECTIVE_POLICIES.get(
                objective, OBJECTIVE_POLICIES["Balanced Growth"]
            )
            scenario = ScenarioSettings(
                name=f"{objective} Strategy",
                description=policy["description"],
                start_year=base_scenario.start_year,
                end_year=base_scenario.end_year,
                target_objective=objective,
                annual_conversion_target=policy["annual_conversion_target"],
                max_conversion_allowed=float("inf"),
                avoid_irmaa=policy["avoid_irmaa"],
                fill_tax_bracket=policy["fill_tax_bracket"],
                constraint_tax_rate=policy["constraint_tax_rate"],
                tax_payment_source=base_scenario.tax_payment_source,
                external_tax_funding=base_scenario.external_tax_funding,
                deferred_tax_rate=base_scenario.deferred_tax_rate,
            )
            scenarios.append(scenario)

        if conversion_amounts:
            for amount in conversion_amounts:
                amount = max(0.0, float(amount))
                scenario = ScenarioSettings(
                    name=f"Fixed ${amount:,.0f}/year",
                    description=f"Convert a fixed ${amount:,.0f} annually.",
                    start_year=base_scenario.start_year,
                    end_year=base_scenario.end_year,
                    target_objective="Fixed Amount",
                    annual_conversion_target=amount,
                    max_conversion_allowed=amount,
                    avoid_irmaa=False,
                    fill_tax_bracket=False,
                    constraint_tax_rate=None,
                    tax_payment_source=base_scenario.tax_payment_source,
                    external_tax_funding=base_scenario.external_tax_funding,
                    deferred_tax_rate=base_scenario.deferred_tax_rate,
                )
                scenarios.append(scenario)

        return scenarios

    def run_scenario_comparison(
        self,
        scenarios: List[ScenarioSettings],
        accounts: List[Account],
        income_streams: List[IncomeStream],
        expenses: Expenses
    ) -> List[ConversionStrategy]:
        """Run every scenario against an independent copy of the accounts."""
        results: List[ConversionStrategy] = []

        for scenario in scenarios:
            strategy = self.simulator.run_full_simulation(
                scenario, accounts, income_streams, expenses
            )
            results.append(strategy)

        return results

    def compare_strategies(self, strategies: List[ConversionStrategy]) -> pd.DataFrame:
        """Create the results table shown in the GUI and HTML report."""
        data = []

        for strategy in strategies:
            data.append({
                "Strategy": strategy.scenario.name,
                "Objective": strategy.scenario.target_objective,
                "Total Conversions": f"${strategy.total_conversions:,.0f}",
                "Total Taxes Paid": f"${strategy.total_taxes_paid:,.0f}",
                "Total Tax Liability": f"${strategy.total_tax_liability:,.0f}",
                "Tax Paid": f"${strategy.total_taxes_paid:,.0f}",
                "Tax Unpaid": f"${strategy.total_taxes_unpaid:,.0f}",
                "Total IRMAA Costs": f"${strategy.total_irmaa_costs:,.0f}",
                "Final Roth Value": f"${strategy.final_roth_value:,.0f}",
                "Final Pretax Value": f"${strategy.final_pretax_value:,.0f}",
                "Final Taxable Value": f"${strategy.final_taxable_value:,.0f}",
                "Final Net Worth": f"${strategy.final_net_worth:,.0f}",
                "Deferred Tax Reserve": f"${strategy.final_deferred_tax_liability:,.0f}",
                "Net After All Taxes": f"${strategy.final_after_tax_net_worth:,.0f}",
            })

        return pd.DataFrame(data)

    def get_ranked_strategies(
        self,
        strategies: List[ConversionStrategy],
        rank_by: str = "Final Net Worth"
    ) -> List[Tuple[ConversionStrategy, int]]:
        """Rank strategies by a metric; lower taxes rank better."""
        ranking_metrics = {
            "Final Net Worth": lambda s: s.final_net_worth,
            "Final Roth Value": lambda s: s.final_roth_value,
            "Total Taxes Paid": lambda s: -s.total_taxes_paid,
            "Total Tax Liability": lambda s: -s.total_tax_liability,
            "Total IRMAA Costs": lambda s: -s.total_irmaa_costs,
            "After-Tax Net Worth": lambda s: s.final_after_tax_net_worth,
            "Final After-Tax Net Worth": lambda s: s.final_after_tax_net_worth,
        }

        metric_func = ranking_metrics.get(rank_by)
        if not metric_func:
            return []

        ranked = sorted(
            enumerate(strategies),
            key=lambda item: metric_func(item[1]),
            reverse=True,
        )
        return [(strategy, rank + 1) for rank, (_, strategy) in enumerate(ranked)]

    def export_strategy_to_csv(
        self,
        strategy: ConversionStrategy,
        filepath: str
    ) -> None:
        """Export a single strategy's year-by-year results to CSV."""
        data = []

        for year_result in strategy.years:
            data.append({
                "Year": year_result.year,
                "Age": year_result.age,
                "Start Pretax": year_result.start_balance_pretax,
                "Start Roth": year_result.start_balance_roth,
                "Start Taxable": year_result.start_balance_taxable,
                "RMD Required": year_result.rmd_required,
                "Taxable Social Security": year_result.taxable_social_security,
                "MAGI": year_result.magi,
                "IRMAA MAGI": year_result.irmaa_magi,
                "Recommended Conversion": year_result.recommended_conversion,
                "Conversion Tax": year_result.conversion_tax,
                "Income Tax": year_result.income_tax,
                "IRMAA Impact": year_result.irmaa_impact,
                "Tax Liability": year_result.total_tax_paid,
                "Tax Paid": year_result.taxes_paid,
                "Tax Unpaid": year_result.taxes_unpaid,
                "Spending Paid": year_result.spending_paid,
                "Spending Shortfall": year_result.spending_shortfall,
                "Taxable Withdrawals": year_result.taxable_withdrawals,
                "Realized Gains": year_result.realized_gains,
                "Withholding From Conversion": year_result.withholding_from_conversion,
                "External Tax Funding": year_result.external_tax_funding,
                "Reconciliation Difference": year_result.reconciliation_difference,
                "End Pretax": year_result.end_balance_pretax,
                "End Roth": year_result.end_balance_roth,
                "End Taxable": year_result.end_balance_taxable,
                "Notes": " | ".join(year_result.notes) if year_result.notes else "",
            })

        pd.DataFrame(data).to_csv(filepath, index=False)

    def calculate_breakeven_analysis(
        self,
        strategy1: ConversionStrategy,
        strategy2: ConversionStrategy
    ) -> Dict:
        """Analyze when one strategy's gross net worth overtakes the other."""
        analysis = {
            "strategy1": strategy1.scenario.name,
            "strategy2": strategy2.scenario.name,
            "crossover_years": [],
            "initial_advantage": None,
            "long_term_winner": None,
        }

        for i, (year1, year2) in enumerate(zip(strategy1.years, strategy2.years)):
            net1 = (year1.end_balance_pretax + year1.end_balance_roth
                    + year1.end_balance_taxable)
            net2 = (year2.end_balance_pretax + year2.end_balance_roth
                    + year2.end_balance_taxable)

            if i == 0:
                analysis["initial_advantage"] = (
                    "Strategy 1" if net1 > net2 else "Strategy 2"
                )

            if i > 0:
                prev1 = strategy1.years[i - 1]
                prev2 = strategy2.years[i - 1]
                prev_net1 = (prev1.end_balance_pretax + prev1.end_balance_roth
                             + prev1.end_balance_taxable)
                prev_net2 = (prev2.end_balance_pretax + prev2.end_balance_roth
                             + prev2.end_balance_taxable)

                if ((prev_net1 < prev_net2 and net1 >= net2)
                        or (prev_net1 >= prev_net2 and net1 < net2)):
                    analysis["crossover_years"].append(year1.year)

        if strategy1.years and strategy2.years:
            analysis["long_term_winner"] = (
                "Strategy 1"
                if strategy1.final_after_tax_net_worth
                >= strategy2.final_after_tax_net_worth
                else "Strategy 2"
            )

        return analysis
