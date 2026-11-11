"""Quick-start script demonstrating Roth conversion analysis programmatically."""

from src.models import (
    ClientProfile, Account, IncomeStream, Expenses, ScenarioSettings
)
from src.simulator import ConversionSimulator
from src.optimizer import ConversionOptimizer
import pandas as pd


def main():
    """Run a quick example analysis."""
    
    # Create a sample client profile
    client = ClientProfile(
        first_name="John",
        last_name="Smith",
        birth_year=1960,
        spouse_birth_year=1962,
        state_residence="ID",
        filing_status="married_filing_jointly",
    )
    
    print(f"=== Roth Conversion Analysis for {client.first_name} {client.last_name} ===")
    print(f"Current Age: {client.current_age}, Spouse Age: {client.spouse_current_age}")
    print()
    
    # Define accounts
    accounts = [
        Account(
            name="Traditional IRA",
            account_type="Traditional IRA",
            current_balance=400000,
            pretax_basis=400000,
            growth_rate=0.07,
        ),
        Account(
            name="Roth IRA",
            account_type="Roth IRA",
            current_balance=150000,
            growth_rate=0.07,
        ),
        Account(
            name="401(k)",
            account_type="401(k)",
            current_balance=250000,
            pretax_basis=250000,
            growth_rate=0.07,
        ),
        Account(
            name="Taxable Brokerage",
            account_type="Taxable Brokerage",
            current_balance=200000,
            cost_basis=150000,
            unrealized_gains=50000,
            growth_rate=0.06,
        ),
    ]
    
    print("ACCOUNTS:")
    for acc in accounts:
        print(f"  {acc.name:25} {acc.account_type:20} ${acc.current_balance:>15,.0f}")
    print(f"  {'TOTAL':25} {' ':20} ${sum(a.current_balance for a in accounts):>15,.0f}")
    print()
    
    # Define income streams
    income_streams = [
        IncomeStream(
            name="Social Security (Primary)",
            income_type="Social Security",
            annual_amount=32000,
            start_age=67,
            end_age=100,
            tax_treatment="tax_free",
        ),
        IncomeStream(
            name="Social Security (Spouse)",
            income_type="Social Security",
            annual_amount=28000,
            start_age=67,
            end_age=100,
            tax_treatment="tax_free",
        ),
        IncomeStream(
            name="Pension",
            income_type="Pension",
            annual_amount=45000,
            start_age=65,
            end_age=100,
        ),
    ]
    
    print("INCOME STREAMS:")
    for inc in income_streams:
        print(f"  {inc.name:30} ${inc.annual_amount:>12,.0f}/year (ages {inc.start_age}-{inc.end_age})")
    print()
    
    # Define expenses
    expenses = Expenses(
        housing=30000,
        utilities=4000,
        food=8000,
        transportation=6000,
        healthcare=10000,
        insurance=8000,
        discretionary=8000,
        other=2000,
    )
    
    print(f"ANNUAL EXPENSES: ${expenses.total_annual:,.0f}")
    print(f"MONTHLY EXPENSES: ${expenses.total_monthly:,.0f}")
    print()
    
    # Create optimizer
    optimizer = ConversionOptimizer(client)
    
    # Define scenarios to test
    base_scenario = ScenarioSettings(
        name="Base",
        start_year=2026,
        end_year=2055,
    )
    
    objectives = [
        "Maximize Roth Value",
        "Minimize Tax Paid",
        "Maximize Gross Net Worth",
        "Minimize IRMAA Impact",
    ]
    
    print(f"ANALYZING {len(objectives)} SCENARIOS...")
    print()
    
    # Generate scenarios
    scenarios = optimizer.generate_scenarios(base_scenario, objectives)
    
    # Run all scenarios
    strategies = optimizer.run_scenario_comparison(
        scenarios, accounts, income_streams, expenses
    )
    
    # Display results
    print("=" * 120)
    print("SCENARIO COMPARISON RESULTS")
    print("=" * 120)
    print()
    
    comparison_df = optimizer.compare_strategies(strategies)
    print(comparison_df.to_string(index=False))
    print()
    
    # Rank by different metrics
    print("=" * 120)
    print("RANKING BY FINAL NET WORTH")
    print("=" * 120)
    ranked = optimizer.get_ranked_strategies(strategies, "Final Net Worth")
    for strategy, rank in ranked:
        print(f"{rank}. {strategy.scenario.name:40} ${strategy.final_net_worth:>15,.0f}")
    print()
    
    print("=" * 120)
    print("RANKING BY FINAL ROTH VALUE")
    print("=" * 120)
    ranked = optimizer.get_ranked_strategies(strategies, "Final Roth Value")
    for strategy, rank in ranked:
        print(f"{rank}. {strategy.scenario.name:40} ${strategy.final_roth_value:>15,.0f}")
    print()
    
    print("=" * 120)
    print("RANKING BY TOTAL TAXES PAID")
    print("=" * 120)
    ranked = optimizer.get_ranked_strategies(strategies, "Total Taxes Paid")
    for strategy, rank in ranked:
        print(f"{rank}. {strategy.scenario.name:40} ${strategy.total_taxes_paid:>15,.0f}")
    print()
    
    # Show detail for top strategy
    print("=" * 120)
    print("DETAIL VIEW - TOP STRATEGY")
    print("=" * 120)
    top_strategy = strategies[0]
    print(f"\nStrategy: {top_strategy.scenario.name}")
    print(f"Objective: {top_strategy.scenario.target_objective}")
    print(f"Analysis Period: {top_strategy.scenario.start_year} to {top_strategy.scenario.end_year}")
    print()
    print("Year-by-Year Summary (First 5 and Last 5 Years):")
    print()
    
    if len(top_strategy.years) > 0:
        # Show first 5 years
        for i, year_result in enumerate(top_strategy.years[:5]):
            print(f"Year {year_result.year} (Age {year_result.age}): "
                  f"Conv=${year_result.recommended_conversion:>10,.0f} "
                  f"Tax=${year_result.conversion_tax:>9,.0f} "
                  f"Roth=${year_result.end_balance_roth:>13,.0f}")
        
        if len(top_strategy.years) > 10:
            print("  ...")
        
        # Show last 5 years
        for year_result in top_strategy.years[-5:]:
            print(f"Year {year_result.year} (Age {year_result.age}): "
                  f"Conv=${year_result.recommended_conversion:>10,.0f} "
                  f"Tax=${year_result.conversion_tax:>9,.0f} "
                  f"Roth=${year_result.end_balance_roth:>13,.0f}")
    
    print()
    print("=" * 120)
    print("SUMMARY")
    print("=" * 120)
    print(f"Total Conversions (30-year period): ${top_strategy.total_conversions:,.0f}")
    print(f"Total Taxes Paid:                   ${top_strategy.total_taxes_paid:,.0f}")
    print(f"Total IRMAA Costs:                  ${top_strategy.total_irmaa_costs:,.0f}")
    print(f"Final Roth Value:                   ${top_strategy.final_roth_value:,.0f}")
    print(f"Final Pre-tax Value:                ${top_strategy.final_pretax_value:,.0f}")
    print(f"Final Taxable Value:                ${top_strategy.final_taxable_value:,.0f}")
    print(f"Final Net Worth:                    ${top_strategy.final_net_worth:,.0f}")
    print()
    
    # Export to CSV
    csv_path = "example_strategy_detail.csv"
    optimizer.export_strategy_to_csv(top_strategy, csv_path)
    print(f"Detailed results exported to: {csv_path}")


if __name__ == "__main__":
    main()
