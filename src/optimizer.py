"""Multi-scenario optimizer for Roth conversion strategies."""

from src.models import ConversionStrategy, ScenarioSettings, ClientProfile, Account, IncomeStream, Expenses
from src.simulator import ConversionSimulator
from src.tax_calculator import TaxCalculator
from typing import List, Dict, Tuple
import pandas as pd


class ConversionOptimizer:
    """Generates and compares multiple conversion strategies to find optimal approach."""
    
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
        """
        Generate multiple scenarios to test different conversion strategies.
        
        Args:
            base_scenario: Template scenario with base settings
            objectives: List of objectives to optimize for
            conversion_amounts: Optional list of fixed annual conversion amounts to test
            
        Returns:
            List of ScenarioSettings, one per strategy
        """
        scenarios = []
        
        for objective in objectives:
            scenario = ScenarioSettings(
                name=f"{objective} Strategy",
                description=f"Optimized for {objective}",
                start_year=base_scenario.start_year,
                end_year=base_scenario.end_year,
                target_objective=objective,
            )
            
            # Customize based on objective
            if objective == "Maximize Roth Value":
                scenario.fill_tax_bracket = True
                scenario.avoid_irmaa = False
                scenario.max_conversion_allowed = float('inf')
            
            elif objective == "Minimize Tax Paid":
                scenario.fill_tax_bracket = False
                scenario.avoid_irmaa = True
                scenario.annual_conversion_target = 0
            
            elif objective == "Maximize Gross Net Worth":
                scenario.fill_tax_bracket = True
                scenario.avoid_irmaa = True
            
            elif objective == "Maximize Inheritance":
                scenario.fill_tax_bracket = True
                scenario.avoid_irmaa = False
            
            elif objective == "Minimize IRMAA Impact":
                scenario.avoid_irmaa = True
                scenario.annual_conversion_target = 0
            
            elif objective == "Balanced Growth":
                scenario.fill_tax_bracket = True
                scenario.avoid_irmaa = True
                scenario.annual_conversion_target = None
            
            scenarios.append(scenario)
        
        # Add fixed amount scenarios if provided
        if conversion_amounts:
            for amount in conversion_amounts:
                scenario = ScenarioSettings(
                    name=f"Fixed ${amount:,.0f}/year",
                    description=f"Convert fixed amount of ${amount:,.0f} annually",
                    start_year=base_scenario.start_year,
                    end_year=base_scenario.end_year,
                    target_objective="Fixed Amount",
                    annual_conversion_target=amount,
                    max_conversion_allowed=amount,
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
        """
        Run all scenarios and return results.
        
        Returns:
            List of ConversionStrategy results
        """
        results = []
        
        for scenario in scenarios:
            strategy = self.simulator.run_full_simulation(
                scenario, accounts, income_streams, expenses
            )
            results.append(strategy)
        
        return results
    
    def compare_strategies(self, strategies: List[ConversionStrategy]) -> pd.DataFrame:
        """
        Create comparison table of all strategies.
        
        Returns:
            DataFrame with key metrics for each strategy
        """
        data = []
        
        for strategy in strategies:
            data.append({
                "Strategy": strategy.scenario.name,
                "Objective": strategy.scenario.target_objective,
                "Total Conversions": f"${strategy.total_conversions:,.0f}",
                "Total Taxes Paid": f"${strategy.total_taxes_paid:,.0f}",
                "Total IRMAA Costs": f"${strategy.total_irmaa_costs:,.0f}",
                "Final Roth Value": f"${strategy.final_roth_value:,.0f}",
                "Final Pretax Value": f"${strategy.final_pretax_value:,.0f}",
                "Final Taxable Value": f"${strategy.final_taxable_value:,.0f}",
                "Final Net Worth": f"${strategy.final_net_worth:,.0f}",
                "Net After All Taxes": f"${strategy.final_net_worth - strategy.total_taxes_paid - strategy.total_irmaa_costs:,.0f}",
            })
        
        df = pd.DataFrame(data)
        return df
    
    def get_ranked_strategies(
        self, 
        strategies: List[ConversionStrategy],
        rank_by: str = "Final Net Worth"
    ) -> List[Tuple[ConversionStrategy, int]]:
        """
        Rank strategies by a specific metric.
        
        Args:
            strategies: List of strategies to rank
            rank_by: Metric to rank on ("Final Net Worth", "Final Roth Value", 
                    "Total Taxes Paid", etc.)
            
        Returns:
            List of (strategy, rank) tuples, sorted by rank
        """
        ranking_metrics = {
            "Final Net Worth": lambda s: s.final_net_worth,
            "Final Roth Value": lambda s: s.final_roth_value,
            "Total Taxes Paid": lambda s: -s.total_taxes_paid,  # Negative = minimize
            "Total IRMAA Costs": lambda s: -s.total_irmaa_costs,  # Negative = minimize
            "After-Tax Net Worth": lambda s: (s.final_net_worth - s.total_taxes_paid - s.total_irmaa_costs),
        }
        
        metric_func = ranking_metrics.get(rank_by)
        if not metric_func:
            return []
        
        ranked = sorted(enumerate(strategies), key=lambda x: metric_func(x[1]), reverse=True)
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
                "Recommended Conversion": year_result.recommended_conversion,
                "Conversion Tax": year_result.conversion_tax,
                "IRMAA Impact": year_result.irmaa_impact,
                "Total Tax": year_result.total_tax_paid,
                "End Pretax": year_result.end_balance_pretax,
                "End Roth": year_result.end_balance_roth,
                "End Taxable": year_result.end_balance_taxable,
                "Notes": " | ".join(year_result.notes) if year_result.notes else "",
            })
        
        df = pd.DataFrame(data)
        df.to_csv(filepath, index=False)
    
    def calculate_breakeven_analysis(
        self,
        strategy1: ConversionStrategy,
        strategy2: ConversionStrategy
    ) -> Dict:
        """
        Analyze when one strategy becomes better than another.
        
        Returns:
            Dictionary with breakeven analysis
        """
        analysis = {
            "strategy1": strategy1.scenario.name,
            "strategy2": strategy2.scenario.name,
            "crossover_years": [],
            "initial_advantage": None,
            "long_term_winner": None,
        }
        
        # Find years where one strategy is better
        for i, (year1, year2) in enumerate(zip(strategy1.years, strategy2.years)):
            net1 = year1.end_balance_pretax + year1.end_balance_roth + year1.end_balance_taxable
            net2 = year2.end_balance_pretax + year2.end_balance_roth + year2.end_balance_taxable
            
            if i == 0:
                analysis["initial_advantage"] = (
                    "Strategy 1" if net1 > net2 else "Strategy 2"
                )
            
            # Check for crossover
            if i > 0:
                prev_net1 = (strategy1.years[i-1].end_balance_pretax + 
                           strategy1.years[i-1].end_balance_roth + 
                           strategy1.years[i-1].end_balance_taxable)
                prev_net2 = (strategy2.years[i-1].end_balance_pretax + 
                           strategy2.years[i-1].end_balance_roth + 
                           strategy2.years[i-1].end_balance_taxable)
                
                if (prev_net1 < prev_net2 and net1 >= net2) or (prev_net1 >= prev_net2 and net1 < net2):
                    analysis["crossover_years"].append(year1.year)
        
        if strategy1.years and strategy2.years:
            final1 = (strategy1.years[-1].end_balance_pretax + 
                     strategy1.years[-1].end_balance_roth + 
                     strategy1.years[-1].end_balance_taxable)
            final2 = (strategy2.years[-1].end_balance_pretax + 
                     strategy2.years[-1].end_balance_roth + 
                     strategy2.years[-1].end_balance_taxable)
            
            analysis["long_term_winner"] = (
                "Strategy 1" if final1 > final2 else "Strategy 2"
            )
        
        return analysis
