"""PySimpleGUI-based interface for Roth conversion simulator."""

import PySimpleGUI as sg
from src.models import (
    ClientProfile, Account, IncomeStream, Expenses, ScenarioSettings
)
from src.simulator import ConversionSimulator
from src.optimizer import ConversionOptimizer
from src.tax_calculator import TaxCalculator
from src.constants import ACCOUNT_TYPES, OBJECTIVES, STATE_TAX_RATES
import pandas as pd
from typing import Dict, List, Tuple
from datetime import datetime
import os


class RothSimulatorGUI:
    """PySimpleGUI interface for Roth conversion simulator."""
    
    def __init__(self):
        sg.theme('DarkBlue3')
        self.client = None
        self.accounts = []
        self.income_streams = []
        self.expenses = None
        self.current_scenario = None
        self.strategies = []
    
    def run(self):
        """Main application loop."""
        self.show_main_menu()
    
    def show_main_menu(self):
        """Display main menu."""
        layout = [
            [sg.Text('ROTH CONVERSION SIMULATOR', font=('Arial', 20, 'bold'))],
            [sg.Text('Optimize your Roth conversion strategy for retirement', font=('Arial', 12))],
            [sg.Text('')],
            [
                sg.Button('New Analysis', size=(20, 2)),
                sg.Button('Open Project', size=(20, 2)),
            ],
            [
                sg.Button('Help', size=(20, 2)),
                sg.Button('Exit', size=(20, 2)),
            ],
        ]
        
        window = sg.Window('Roth Conversion Simulator', layout, finalize=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Exit':
                break
            elif event == 'New Analysis':
                window.close()
                self.wizard_new_analysis()
                break
            elif event == 'Open Project':
                sg.popup_not_implemented('Project loading coming soon')
            elif event == 'Help':
                self.show_help()
        
        window.close()
    
    def wizard_new_analysis(self):
        """Multi-step wizard for creating a new analysis."""
        # Step 1: Client Profile
        self.client = self.step_client_profile()
        if self.client is None:
            self.show_main_menu()
            return
        
        # Step 2: Accounts
        self.accounts = self.step_accounts()
        if self.accounts is None:
            self.show_main_menu()
            return
        
        # Step 3: Income Streams
        self.income_streams = self.step_income_streams()
        if self.income_streams is None:
            self.show_main_menu()
            return
        
        # Step 4: Expenses
        self.expenses = self.step_expenses()
        if self.expenses is None:
            self.show_main_menu()
            return
        
        # Step 5: Scenario Selection
        scenarios = self.step_scenario_selection()
        if scenarios is None:
            self.show_main_menu()
            return
        
        # Run optimization
        self.run_optimization(scenarios)
    
    def step_client_profile(self) -> ClientProfile:
        """Collect client profile information."""
        current_year = datetime.now().year
        
        layout = [
            [sg.Text('CLIENT PROFILE', font=('Arial', 14, 'bold'))],
            [sg.Text('')],
            
            [sg.Text('First Name:', size=(15,)), sg.Input(key='first_name', size=(30,))],
            [sg.Text('Last Name:', size=(15,)), sg.Input(key='last_name', size=(30,))],
            [sg.Text('Birth Year:', size=(15,)), sg.Input(key='birth_year', size=(30,))],
            [sg.Text('Married?', size=(15,)), sg.Radio('Yes', 'married', True, key='married_yes'), 
             sg.Radio('No', 'married', False, key='married_no')],
            [sg.Text('Spouse Birth Year:', size=(15,)), sg.Input(key='spouse_birth_year', size=(30,), disabled=True)],
            [sg.Text('State Residence:', size=(15,)), 
             sg.Combo(sorted(STATE_TAX_RATES.keys()), key='state', default_value='ID', size=(28,))],
            [sg.Text('')],
            [sg.Button('Next', size=(15, 1)), sg.Button('Cancel', size=(15, 1))],
        ]
        
        window = sg.Window('New Analysis - Step 1/5: Client Profile', layout, finalize=True)
        window['married_yes'].bind('<ButtonRelease>', '_CHANGED')
        window['married_no'].bind('<ButtonRelease>', '_CHANGED')
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Cancel':
                window.close()
                return None
            
            elif event in ('married_yes_CHANGED', 'married_no_CHANGED'):
                window['spouse_birth_year'].update(disabled=not values['married_yes'])
            
            elif event == 'Next':
                # Validate inputs
                try:
                    first_name = values['first_name'].strip()
                    last_name = values['last_name'].strip()
                    birth_year = int(values['birth_year'])
                    
                    if not first_name or not last_name or birth_year <= 1900 or birth_year > current_year:
                        sg.popup_error('Please enter valid name and birth year')
                        continue
                    
                    spouse_birth_year = None
                    if values['married_yes']:
                        spouse_birth_year = int(values['spouse_birth_year'])
                        if spouse_birth_year <= 1900 or spouse_birth_year > current_year:
                            sg.popup_error('Please enter valid spouse birth year')
                            continue
                    
                    client = ClientProfile(
                        first_name=first_name,
                        last_name=last_name,
                        birth_year=birth_year,
                        spouse_birth_year=spouse_birth_year,
                        state_residence=values['state'],
                        filing_status='married_filing_jointly' if values['married_yes'] else 'single',
                    )
                    
                    window.close()
                    return client
                
                except ValueError:
                    sg.popup_error('Please enter valid numbers for birth years')
        
        window.close()
        return None
    
    def step_accounts(self) -> List[Account]:
        """Collect account information."""
        accounts = []
        
        layout = [
            [sg.Text('ACCOUNTS', font=('Arial', 14, 'bold'))],
            [sg.Text('Add all of your retirement and investment accounts')],
            [sg.Text('')],
            
            [sg.Text('Account Name:', size=(15,)), sg.Input(key='acc_name', size=(25,))],
            [sg.Text('Account Type:', size=(15,)), 
             sg.Combo(ACCOUNT_TYPES, key='acc_type', size=(23,))],
            [sg.Text('Current Balance:', size=(15,)), sg.Input(key='acc_balance', size=(25,))],
            [sg.Text('Pre-tax Basis:', size=(15,)), sg.Input(key='acc_pretax', size=(25,))],
            [sg.Text('After-tax Basis:', size=(15,)), sg.Input(key='acc_aftertax', size=(25,))],
            [sg.Text('Expected Growth %:', size=(15,)), sg.Input('7.0', key='acc_growth', size=(25,))],
            [sg.Text('Annual Contribution:', size=(15,)), sg.Input('0', key='acc_contrib', size=(25,))],
            [sg.Text('')],
            
            [sg.Button('Add Account', size=(15, 1)), sg.Button('Done', size=(15, 1)), 
             sg.Button('Cancel', size=(15, 1))],
            
            [sg.Text('')],
            [sg.Text('Accounts Added:', font=('Arial', 11, 'bold'))],
            [sg.Listbox([], key='acc_list', size=(60, 8), disabled=True)],
        ]
        
        window = sg.Window('New Analysis - Step 2/5: Accounts', layout, finalize=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Cancel':
                window.close()
                return None
            
            elif event == 'Add Account':
                try:
                    name = values['acc_name'].strip()
                    acc_type = values['acc_type']
                    balance = float(values['acc_balance'])
                    pretax = float(values['acc_pretax']) if values['acc_pretax'] else 0.0
                    aftertax = float(values['acc_aftertax']) if values['acc_aftertax'] else 0.0
                    growth = float(values['acc_growth']) / 100
                    contrib = float(values['acc_contrib']) if values['acc_contrib'] else 0.0
                    
                    if not name or not acc_type:
                        sg.popup_error('Please enter account name and type')
                        continue
                    
                    if balance < 0:
                        sg.popup_error('Balance must be non-negative')
                        continue
                    
                    account = Account(
                        name=name,
                        account_type=acc_type,
                        current_balance=balance,
                        pretax_basis=pretax,
                        aftertax_basis=aftertax,
                        growth_rate=growth,
                        annual_contribution=contrib,
                    )
                    
                    accounts.append(account)
                    
                    # Update list
                    list_items = [f"{a.name} ({a.account_type}) - ${a.current_balance:,.0f}" for a in accounts]
                    window['acc_list'].update(list_items)
                    
                    # Clear inputs
                    window['acc_name'].update('')
                    window['acc_type'].update('')
                    window['acc_balance'].update('')
                    window['acc_pretax'].update('')
                    window['acc_aftertax'].update('')
                    window['acc_growth'].update('7.0')
                    window['acc_contrib'].update('0')
                
                except ValueError:
                    sg.popup_error('Please enter valid numbers for all fields')
            
            elif event == 'Done':
                if not accounts:
                    sg.popup_error('Please add at least one account')
                    continue
                window.close()
                return accounts
        
        window.close()
        return None
    
    def step_income_streams(self) -> List[IncomeStream]:
        """Collect income stream information."""
        income_streams = []
        
        layout = [
            [sg.Text('INCOME STREAMS', font=('Arial', 14, 'bold'))],
            [sg.Text('Add all sources of income (Social Security, pensions, work, etc.)')],
            [sg.Text('')],
            
            [sg.Text('Income Name:', size=(15,)), sg.Input(key='inc_name', size=(25,))],
            [sg.Text('Type:', size=(15,)), 
             sg.Combo(['W2 Income', 'Self-Employment', 'Social Security', 'Pension', 'Dividends'], 
                     key='inc_type', size=(23,))],
            [sg.Text('Annual Amount:', size=(15,)), sg.Input(key='inc_amount', size=(25,))],
            [sg.Text('Start Age:', size=(15,)), sg.Input('65', key='inc_start', size=(25,))],
            [sg.Text('End Age:', size=(15,)), sg.Input('100', key='inc_end', size=(25,))],
            [sg.Text('Annual Growth %:', size=(15,)), sg.Input('0', key='inc_growth', size=(25,))],
            [sg.Text('Tax Treatment:', size=(15,)), 
             sg.Combo(['Ordinary Income', 'Qualified Dividends', 'Tax-Free'], 
                     key='inc_tax', default_value='Ordinary Income', size=(23,))],
            [sg.Text('')],
            
            [sg.Button('Add Income', size=(15, 1)), sg.Button('Done', size=(15, 1)), 
             sg.Button('Cancel', size=(15, 1))],
            
            [sg.Text('')],
            [sg.Text('Income Streams:', font=('Arial', 11, 'bold'))],
            [sg.Listbox([], key='inc_list', size=(60, 8), disabled=True)],
        ]
        
        window = sg.Window('New Analysis - Step 3/5: Income Streams', layout, finalize=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Cancel':
                window.close()
                return None
            
            elif event == 'Add Income':
                try:
                    name = values['inc_name'].strip()
                    inc_type = values['inc_type']
                    amount = float(values['inc_amount'])
                    start = int(values['inc_start'])
                    end = int(values['inc_end'])
                    growth = float(values['inc_growth']) / 100
                    tax = values['inc_tax'].lower().replace(' ', '_')
                    
                    if not name or not inc_type:
                        sg.popup_error('Please enter income name and type')
                        continue
                    
                    if amount < 0 or start < 0 or end < start:
                        sg.popup_error('Please enter valid amounts and age ranges')
                        continue
                    
                    income = IncomeStream(
                        name=name,
                        income_type=inc_type,
                        annual_amount=amount,
                        start_age=start,
                        end_age=end,
                        growth_rate=growth,
                        tax_treatment=tax,
                    )
                    
                    income_streams.append(income)
                    
                    # Update list
                    list_items = [f"{i.name} - ${i.annual_amount:,.0f}/year (ages {i.start_age}-{i.end_age})" 
                                 for i in income_streams]
                    window['inc_list'].update(list_items)
                    
                    # Clear inputs
                    window['inc_name'].update('')
                    window['inc_type'].update('')
                    window['inc_amount'].update('')
                    window['inc_start'].update('65')
                    window['inc_end'].update('100')
                    window['inc_growth'].update('0')
                
                except ValueError:
                    sg.popup_error('Please enter valid numbers for all fields')
            
            elif event == 'Done':
                if not income_streams:
                    sg.popup_error('Please add at least one income stream')
                    continue
                window.close()
                return income_streams
        
        window.close()
        return None
    
    def step_expenses(self) -> Expenses:
        """Collect expense information."""
        layout = [
            [sg.Text('ANNUAL EXPENSES', font=('Arial', 14, 'bold'))],
            [sg.Text('Enter your expected annual expenses by category')],
            [sg.Text('')],
            
            [sg.Text('Housing:', size=(15,)), sg.Input(key='housing', size=(20,))],
            [sg.Text('Utilities:', size=(15,)), sg.Input(key='utilities', size=(20,))],
            [sg.Text('Food:', size=(15,)), sg.Input(key='food', size=(20,))],
            [sg.Text('Transportation:', size=(15,)), sg.Input(key='transportation', size=(20,))],
            [sg.Text('Healthcare:', size=(15,)), sg.Input(key='healthcare', size=(20,))],
            [sg.Text('Insurance:', size=(15,)), sg.Input(key='insurance', size=(20,))],
            [sg.Text('Discretionary:', size=(15,)), sg.Input(key='discretionary', size=(20,))],
            [sg.Text('Other:', size=(15,)), sg.Input(key='other', size=(20,))],
            [sg.Text('')],
            [sg.Text('Total Monthly:', size=(15,)), sg.Text('$0', key='monthly_total', size=(20,))],
            [sg.Text('Total Annual:', size=(15,)), sg.Text('$0', key='annual_total', size=(20,))],
            [sg.Text('')],
            
            [sg.Button('Calculate Total', size=(15, 1)), sg.Button('Next', size=(15, 1)), 
             sg.Button('Cancel', size=(15, 1))],
        ]
        
        window = sg.Window('New Analysis - Step 4/5: Expenses', layout, finalize=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Cancel':
                window.close()
                return None
            
            elif event == 'Calculate Total':
                try:
                    total = sum(float(values[key]) if values[key] else 0 
                               for key in ['housing', 'utilities', 'food', 'transportation',
                                         'healthcare', 'insurance', 'discretionary', 'other'])
                    
                    window['annual_total'].update(f"${total:,.0f}")
                    window['monthly_total'].update(f"${total/12:,.0f}")
                
                except ValueError:
                    sg.popup_error('Please enter valid numbers')
            
            elif event == 'Next':
                try:
                    expenses = Expenses(
                        housing=float(values['housing']) if values['housing'] else 0,
                        utilities=float(values['utilities']) if values['utilities'] else 0,
                        food=float(values['food']) if values['food'] else 0,
                        transportation=float(values['transportation']) if values['transportation'] else 0,
                        healthcare=float(values['healthcare']) if values['healthcare'] else 0,
                        insurance=float(values['insurance']) if values['insurance'] else 0,
                        discretionary=float(values['discretionary']) if values['discretionary'] else 0,
                        other=float(values['other']) if values['other'] else 0,
                    )
                    
                    window.close()
                    return expenses
                
                except ValueError:
                    sg.popup_error('Please enter valid numbers for all fields')
        
        window.close()
        return None
    
    def step_scenario_selection(self) -> List[ScenarioSettings]:
        """Select which scenarios to analyze."""
        layout = [
            [sg.Text('SCENARIO SELECTION', font=('Arial', 14, 'bold'))],
            [sg.Text('Choose which strategies to analyze')],
            [sg.Text('')],
            
            [sg.Checkbox('Maximize Roth Value', key='obj_roth', default=True)],
            [sg.Checkbox('Maximize Gross Net Worth', key='obj_networth', default=True)],
            [sg.Checkbox('Maximize Inheritance', key='obj_inheritance', default=False)],
            [sg.Checkbox('Minimize Tax Paid', key='obj_tax', default=True)],
            [sg.Checkbox('Minimize IRMAA Impact', key='obj_irmaa', default=True)],
            [sg.Checkbox('Balanced Growth', key='obj_balanced', default=True)],
            [sg.Text('')],
            
            [sg.Text('Analysis Period:', size=(15,))],
            [sg.Text('From Year:', size=(10,)), sg.Input('2026', key='start_year', size=(10,)),
             sg.Text('To Year:', size=(10,)), sg.Input('2055', key='end_year', size=(10,))],
            [sg.Text('')],
            
            [sg.Button('Run Analysis', size=(15, 1)), sg.Button('Cancel', size=(15, 1))],
        ]
        
        window = sg.Window('New Analysis - Step 5/5: Scenarios', layout, finalize=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Cancel':
                window.close()
                return None
            
            elif event == 'Run Analysis':
                try:
                    selected = []
                    if values['obj_roth']:
                        selected.append('Maximize Roth Value')
                    if values['obj_networth']:
                        selected.append('Maximize Gross Net Worth')
                    if values['obj_inheritance']:
                        selected.append('Maximize Inheritance')
                    if values['obj_tax']:
                        selected.append('Minimize Tax Paid')
                    if values['obj_irmaa']:
                        selected.append('Minimize IRMAA Impact')
                    if values['obj_balanced']:
                        selected.append('Balanced Growth')
                    
                    if not selected:
                        sg.popup_error('Please select at least one scenario')
                        continue
                    
                    start_year = int(values['start_year'])
                    end_year = int(values['end_year'])
                    
                    if start_year >= end_year:
                        sg.popup_error('Start year must be before end year')
                        continue
                    
                    # Create scenario objects
                    scenarios = []
                    for obj in selected:
                        scenario = ScenarioSettings(
                            name=f"{obj}",
                            start_year=start_year,
                            end_year=end_year,
                            target_objective=obj,
                        )
                        scenarios.append(scenario)
                    
                    window.close()
                    return scenarios
                
                except ValueError:
                    sg.popup_error('Please enter valid years')
        
        window.close()
        return None
    
    def run_optimization(self, scenarios: List[ScenarioSettings]):
        """Run optimization and display results."""
        optimizer = ConversionOptimizer(self.client)
        
        # Show progress
        sg.popup_animated(sg.DEFAULT_BASE64_LOADING_GIF, transparent_color=sg.theme_background_color(),
                         time_between_frames=100)
        
        try:
            # Generate scenarios with custom objectives
            self.strategies = optimizer.run_scenario_comparison(
                scenarios, self.accounts, self.income_streams, self.expenses
            )
            
            sg.popup_animated(None)
            self.show_results(optimizer)
        
        except Exception as e:
            sg.popup_animated(None)
            sg.popup_error(f'Error running analysis: {str(e)}')
            self.show_main_menu()
    
    def show_results(self, optimizer: ConversionOptimizer):
        """Display analysis results."""
        # Create comparison table
        comparison_df = optimizer.compare_strategies(self.strategies)
        
        layout = [
            [sg.Text('ANALYSIS RESULTS', font=('Arial', 14, 'bold'))],
            [sg.Text('')],
            [sg.Text('Strategy Comparison:', font=('Arial', 11, 'bold'))],
            [sg.Table(
                values=comparison_df.values.tolist(),
                headings=comparison_df.columns.tolist(),
                key='results_table',
                size=(100, 15),
                justification='right',
            )],
            [sg.Text('')],
            [sg.Button('Export to CSV', size=(15, 1)),
             sg.Button('Detail View', size=(15, 1)),
             sg.Button('Back to Menu', size=(15, 1))],
        ]
        
        window = sg.Window('Analysis Results', layout, finalize=True, size=(1200, 600))
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'Back to Menu':
                break
            elif event == 'Export to CSV':
                folder = sg.popup_get_folder('Select folder for export')
                if folder:
                    for i, strategy in enumerate(self.strategies):
                        filename = f"{folder}\\strategy_{i+1}_{strategy.scenario.name.replace(' ', '_')}.csv"
                        optimizer.export_strategy_to_csv(strategy, filename)
                    sg.popup_ok(f'Exported {len(self.strategies)} strategies')
            elif event == 'Detail View':
                self.show_detail_view(optimizer)
        
        window.close()
        self.show_main_menu()
    
    def show_detail_view(self, optimizer: ConversionOptimizer):
        """Show detailed year-by-year view for a strategy."""
        if not self.strategies:
            return
        
        # Let user select which strategy
        strategy_names = [s.scenario.name for s in self.strategies]
        choice = sg.popup_get_choice(
            'Select a strategy to view in detail:',
            strategy_names,
            title='Select Strategy'
        )
        
        if not choice:
            return
        
        strategy = self.strategies[strategy_names.index(choice)]
        
        # Create year-by-year data
        data = []
        for year_result in strategy.years:
            data.append([
                year_result.year,
                year_result.age,
                f"${year_result.start_balance_pretax:,.0f}",
                f"${year_result.recommended_conversion:,.0f}",
                f"${year_result.conversion_tax:,.0f}",
                f"${year_result.irmaa_impact:,.0f}",
                f"${year_result.end_balance_roth:,.0f}",
                f"${year_result.total_tax_paid:,.0f}",
            ])
        
        headings = ['Year', 'Age', 'Start Pretax', 'Conversion', 'Conv. Tax', 'IRMAA', 'End Roth', 'Total Tax']
        
        layout = [
            [sg.Text(f'Detail View: {choice}', font=('Arial', 14, 'bold'))],
            [sg.Table(
                values=data,
                headings=headings,
                key='detail_table',
                size=(120, 20),
                justification='right',
            )],
            [sg.Button('Close', size=(15, 1))],
        ]
        
        window = sg.Window('Strategy Detail', layout, finalize=True, size=(1000, 600))
        
        while True:
            event, values = window.read()
            if event == sg.WINDOW_CLOSED or event == 'Close':
                break
        
        window.close()
    
    def show_help(self):
        """Show help documentation."""
        help_text = """
ROTH CONVERSION SIMULATOR - Help

This tool helps you optimize Roth conversion strategies for retirement by:

1. Modeling your complete financial picture (assets, income, expenses)
2. Projecting account values to age 100
3. Analyzing multiple conversion strategies
4. Identifying optimal approaches based on your goals

KEY CONCEPTS:

Roth Conversion: Moving money from traditional (pre-tax) IRAs to Roth (after-tax) accounts.
- Pro: Tax-free growth, no RMDs, tax-free inheritance
- Con: Pay income tax on conversion amount

IRMAA: Income-Related Monthly Adjustment Amounts
- Medicare premiums increase at higher incomes ($194k+ for couples in 2026)
- Conversions increase income, potentially triggering IRMAA

RMD: Required Minimum Distributions
- Start at age 73 (2023+)
- Must withdraw a percentage of traditional IRA/401k each year
- Roth IRAs have no RMD during owner's lifetime

OBJECTIVES:

1. Maximize Roth Value: Convert aggressively to build tax-free assets
2. Maximize Net Worth: Balance conversions against tax impact
3. Minimize Tax Paid: Minimize lifetime tax burden
4. Minimize IRMAA: Keep income below Medicare premium thresholds
5. Maximize Inheritance: Optimize tax efficiency for heirs
6. Balanced Growth: Reasonable conversion with tax awareness

For more information, visit the documentation.
        """
        sg.popup_scrolled(help_text, title='Help', size=(70, 30))
    
    def main(self):
        """Entry point for GUI."""
        self.run()


if __name__ == '__main__':
    app = RothSimulatorGUI()
    app.main()
