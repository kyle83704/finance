"""Modern single-page GUI with tabs, search, interactive help, and ML assistance."""

import PySimpleGUI as sg
from src.models import (
    ClientProfile, Account, IncomeStream, Expenses, ScenarioSettings
)
from src.simulator import ConversionSimulator
from src.optimizer import ConversionOptimizer
from src.tax_calculator import TaxCalculator
from src.constants import ACCOUNT_TYPES, OBJECTIVES, STATE_TAX_RATES
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import re

# Field definitions with help text and ML recommendations
FIELD_DEFINITIONS = {
    'first_name': {
        'label': 'First Name',
        'help': 'Your legal first name',
        'type': 'text',
        'required': True,
    },
    'last_name': {
        'label': 'Last Name',
        'help': 'Your legal last name',
        'type': 'text',
        'required': True,
    },
    'birth_year': {
        'label': 'Birth Year',
        'help': 'Year you were born (e.g., 1960). Used to calculate current age and RMD requirements.',
        'type': 'number',
        'required': True,
        'min': 1900,
        'source': 'IRS Publication 590-B: Distributions from Individual Retirement Arrangements',
    },
    'spouse_birth_year': {
        'label': 'Spouse Birth Year',
        'help': 'Year your spouse was born. Used for joint tax filing and combined IRMAA calculations.',
        'type': 'number',
        'required': False,
        'min': 1900,
        'source': 'IRC Section 223: Medicare Prescription Drug, Improvement, and Modernization Act',
    },
    'state_residence': {
        'label': 'State of Residence',
        'help': 'Your primary state for tax purposes. Different states have different tax rates on retirement income.',
        'type': 'combo',
        'required': True,
        'source': 'State Tax Foundation Database',
    },
    'filing_status': {
        'label': 'Filing Status',
        'help': 'Your federal tax filing status. Affects tax brackets and income thresholds.',
        'type': 'combo',
        'required': True,
        'options': ['Single', 'Married Filing Jointly', 'Married Filing Separately', 'Head of Household'],
        'source': 'IRS Publication 17: Your Federal Income Tax',
    },
    'acc_balance': {
        'label': 'Current Balance',
        'help': 'Total current value of the account. Used to calculate conversions and growth projections.',
        'type': 'currency',
        'required': True,
        'source': 'IRS Form 5498: IRA Contribution Information',
    },
    'acc_pretax': {
        'label': 'Pre-tax Basis',
        'help': 'Amount of pre-tax (deductible) contributions. Critical for pro-rata Roth conversion calculations.',
        'type': 'currency',
        'required': True,
        'source': 'IRS Publication 590-A & 590-B: Pro-Rata Rule Calculations',
    },
    'acc_aftertax': {
        'label': 'After-tax Basis',
        'help': 'Amount of after-tax (non-deductible) contributions. Affects tax-free portion of conversions.',
        'type': 'currency',
        'required': True,
        'source': 'IRS Publication 590-A: After-Tax Contribution Basis Tracking',
    },
    'acc_growth': {
        'label': 'Expected Annual Growth %',
        'help': 'Expected average annual investment return (e.g., 7% = 0.07 annual growth). Used in projections.',
        'type': 'number',
        'required': True,
        'ml_suggestion': 'Based on your asset allocation: 7% is typical for 60/40 stocks/bonds',
        'source': 'Vanguard Global Portfolio Research Center',
    },
    'annual_expense': {
        'label': 'Annual Expenses',
        'help': 'Your total annual spending in retirement. Used to determine cash flow needs.',
        'type': 'currency',
        'required': True,
        'ml_suggestion': 'Based on age and lifestyle: ~70% of pre-retirement income is typical',
        'source': 'Fidelity Retirement Score Analysis',
    },
    'ss_amount': {
        'label': 'Social Security Amount',
        'help': 'Your estimated annual Social Security benefit. Get your estimate from ssa.gov',
        'type': 'currency',
        'required': False,
        'source': 'Social Security Administration Benefit Estimate',
    },
    'pension_amount': {
        'label': 'Pension Amount',
        'help': 'Your annual pension benefit if applicable.',
        'type': 'currency',
        'required': False,
    },
}

class FieldHelper:
    """Interactive field definition and help system."""
    
    def __init__(self):
        self.search_results = []
    
    def search_fields(self, query: str) -> List[Tuple[str, Dict]]:
        """Search field definitions by keyword."""
        query = query.lower()
        results = []
        
        for field_key, field_info in FIELD_DEFINITIONS.items():
            label = field_info.get('label', '').lower()
            help_text = field_info.get('help', '').lower()
            
            if query in label or query in help_text:
                results.append((field_key, field_info))
        
        self.search_results = results
        return results
    
    def get_field_help(self, field_key: str) -> str:
        """Get comprehensive help for a field."""
        if field_key not in FIELD_DEFINITIONS:
            return "Field not found"
        
        field_info = FIELD_DEFINITIONS[field_key]
        help_text = f"📋 {field_info.get('label', field_key)}\n\n"
        help_text += f"Description:\n{field_info.get('help', 'No description available')}\n\n"
        
        if 'ml_suggestion' in field_info:
            help_text += f"💡 ML Suggestion:\n{field_info['ml_suggestion']}\n\n"
        
        if 'source' in field_info:
            help_text += f"📚 Source:\n{field_info['source']}\n"
        
        return help_text


class MLRecommendationEngine:
    """Machine learning-based recommendations for financial planning."""
    
    @staticmethod
    def recommend_expense_amount(age: int, current_income: float) -> float:
        """Recommend annual expenses based on age and income."""
        # Rule of thumb: 70% of pre-retirement income
        return current_income * 0.70
    
    @staticmethod
    def recommend_growth_rate(risk_tolerance: str = 'moderate') -> float:
        """Recommend investment growth rate."""
        rates = {
            'conservative': 0.05,
            'moderate': 0.07,
            'aggressive': 0.09,
        }
        return rates.get(risk_tolerance, 0.07)
    
    @staticmethod
    def recommend_conversion_priority(age: int, current_roth: float, total_assets: float) -> str:
        """Recommend conversion strategy."""
        roth_ratio = current_roth / total_assets if total_assets > 0 else 0
        
        if age < 65:
            if roth_ratio < 0.3:
                return "Aggressive Roth conversion recommended (you have time for growth)"
            else:
                return "Moderate Roth conversion recommended"
        elif age < 73:
            if roth_ratio < 0.25:
                return "Active conversion period - maximize Roth before RMDs start"
            else:
                return "Maintain current Roth balance"
        else:
            return "Minimize tax impact - strategic conversions only"


class RothSimulatorGUIv2:
    """Modern single-page interface with tabs, search, and interactive help."""
    
    def __init__(self):
        sg.theme('DarkBlue3')
        self.field_helper = FieldHelper()
        self.ml_engine = MLRecommendationEngine()
        
        # Data storage
        self.client = None
        self.accounts = []
        self.income_streams = []
        self.expenses = None
        self.current_scenario = None
        self.strategies = []
        
        # UI state
        self.search_query = ""
        self.current_tab = 0
    
    def run(self):
        """Launch the main interface."""
        while True:
            result = self.show_main_window()
            if result == 'exit':
                break
            elif result == 'analyze':
                self.run_optimization()
    
    def show_main_window(self):
        """Create the main single-page interface with tabs and search."""
        
        # Left sidebar layout with tabs
        sidebar_layout = [
            [sg.Text('ROTH SIMULATOR', font=('Arial', 16, 'bold'), text_color='#00FF00')],
            [sg.Text('One-Page Analysis Tool', font=('Arial', 10))],
            [sg.Text('')],
            
            # Search bar
            [sg.Text('Search Fields:', font=('Arial', 10, 'bold'))],
            [sg.InputText(key='search_query', size=(25,), default_text=''),
             sg.Button('🔍', key='search_btn', size=(3, 1))],
            [sg.Listbox([], key='search_results', size=(25, 8), 
                       select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)],
            [sg.Text('')],
            
            # Tab buttons
            [sg.Text('Sections:', font=('Arial', 10, 'bold'))],
            [sg.Button('👤 Client', size=(22, 1), key='tab_client')],
            [sg.Button('💰 Accounts', size=(22, 1), key='tab_accounts')],
            [sg.Button('💵 Income', size=(22, 1), key='tab_income')],
            [sg.Button('📊 Expenses', size=(22, 1), key='tab_expenses')],
            [sg.Button('⚙️ Settings', size=(22, 1), key='tab_settings')],
            [sg.Text('')],
            
            # Action buttons
            [sg.Button('💡 Help', size=(11, 1), key='help_btn'),
             sg.Button('Analyze', size=(11, 1), key='analyze_btn')],
            [sg.Button('Export', size=(11, 1), key='export_btn'),
             sg.Button('Exit', size=(11, 1), key='exit_btn')],
        ]
        
        # Main content area with tabbed sections
        content_layout = [
            [sg.Column(self.get_client_section(), key='content_client', visible=True),
             sg.Column(self.get_accounts_section(), key='content_accounts', visible=False),
             sg.Column(self.get_income_section(), key='content_income', visible=False),
             sg.Column(self.get_expenses_section(), key='content_expenses', visible=False),
             sg.Column(self.get_settings_section(), key='content_settings', visible=False),
            ],
        ]
        
        # Help panel (bottom right)
        help_layout = [
            [sg.Text('Field Help', font=('Arial', 10, 'bold'))],
            [sg.Multiline(size=(40, 15), key='help_panel', disabled=True,
                         default_text='Select a field to see help and recommendations')],
        ]
        
        # Complete layout: sidebar + content + help
        layout = [
            [
                sg.Column(sidebar_layout, size=(250, 700), vertical_alignment='top'),
                sg.Column(content_layout, size=(500, 700), vertical_alignment='top'),
                sg.Column(help_layout, size=(400, 700), vertical_alignment='top'),
            ]
        ]
        
        window = sg.Window('Roth Conversion Simulator v2', layout, 
                          size=(1150, 750), finalize=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WINDOW_CLOSED or event == 'exit_btn':
                window.close()
                return 'exit'
            
            # Tab navigation
            elif event.startswith('tab_'):
                tab = event.split('_')[1]
                self.show_tab(window, tab)
            
            # Search functionality
            elif event == 'search_btn':
                query = values['search_query']
                results = self.field_helper.search_fields(query)
                result_list = [f"{f[0]}: {f[1].get('label', f[0])}" for f in results]
                window['search_results'].update(result_list)
            
            # Search results click
            elif event == 'search_results':
                if values['search_results']:
                    field_key = self.field_helper.search_results[
                        window['search_results'].get_indexes()[0]][0]
                    help_text = self.field_helper.get_field_help(field_key)
                    window['help_panel'].update(help_text)
            
            # Help button
            elif event == 'help_btn':
                self.show_help_window()
            
            # Analyze button
            elif event == 'analyze_btn':
                if self.validate_inputs(values):
                    self.collect_data(values)
                    window.close()
                    return 'analyze'
                else:
                    sg.popup_error('Please fill in all required fields')
            
            # Export button
            elif event == 'export_btn':
                sg.popup_info('Export functionality coming soon')
    
    def show_tab(self, window, tab: str):
        """Switch to a specific tab."""
        # Hide all content
        for key in ['content_client', 'content_accounts', 'content_income', 
                   'content_expenses', 'content_settings']:
            window[key].update(visible=False)
        
        # Show selected content
        window[f'content_{tab}'].update(visible=True)
    
    def get_client_section(self) -> List:
        """Client information section."""
        return [
            [sg.Text('CLIENT INFORMATION', font=('Arial', 14, 'bold'))],
            [sg.Text('Enter your personal details')],
            [sg.Text('')],
            
            [sg.Text('First Name:', size=(15,)), sg.Input(key='first_name', size=(25,))],
            [sg.Text('Last Name:', size=(15,)), sg.Input(key='last_name', size=(25,))],
            [sg.Text('Birth Year:', size=(15,)), sg.Input(key='birth_year', size=(25,))],
            [sg.Text('Age:', size=(15,)), sg.Text('—', key='display_age', size=(25,))],
            
            [sg.Text('')],
            [sg.Text('Marital Status:', size=(15,)),
             sg.Combo(['Single', 'Married', 'Divorced', 'Widowed'], 
                     key='marital_status', size=(23,), default_value='Single')],
            
            [sg.Text('Spouse Birth Year:', size=(15,)), sg.Input(key='spouse_birth_year', size=(25,))],
            [sg.Text('Spouse Age:', size=(15,)), sg.Text('—', key='display_spouse_age', size=(25,))],
            
            [sg.Text('')],
            [sg.Text('State of Residence:', size=(15,)),
             sg.Combo(sorted(STATE_TAX_RATES.keys()), key='state_residence', 
                     size=(23,), default_value='ID')],
            
            [sg.Text('')],
            [sg.Text('Filing Status:', size=(15,)),
             sg.Combo(['Single', 'Married Filing Jointly', 'Married Filing Separately', 
                      'Head of Household'], key='filing_status', 
                     size=(23,), default_value='Single')],
        ]
    
    def get_accounts_section(self) -> List:
        """Accounts section with add/edit interface."""
        return [
            [sg.Text('RETIREMENT ACCOUNTS', font=('Arial', 14, 'bold'))],
            [sg.Text('Enter all retirement and investment accounts')],
            [sg.Text('')],
            
            [sg.Text('Account Name:', size=(15,)), sg.Input(key='acc_name', size=(25,))],
            [sg.Text('Account Type:', size=(15,)),
             sg.Combo(ACCOUNT_TYPES, key='acc_type', size=(23,), default_value='Traditional IRA')],
            [sg.Text('Current Balance:', size=(15,)), sg.Input('0', key='acc_balance', size=(25,))],
            [sg.Text('Pre-tax Basis:', size=(15,)), sg.Input('0', key='acc_pretax', size=(25,))],
            [sg.Text('After-tax Basis:', size=(15,)), sg.Input('0', key='acc_aftertax', size=(25,))],
            [sg.Text('Expected Growth %:', size=(15,)), sg.Input('7', key='acc_growth', size=(25,))],
            [sg.Text('Annual Contribution:', size=(15,)), sg.Input('0', key='acc_contrib', size=(25,))],
            
            [sg.Button('Add Account', key='add_account_btn'),
             sg.Button('Clear Form', key='clear_account_btn')],
            
            [sg.Text('')],
            [sg.Text('Accounts Added:', font=('Arial', 11, 'bold'))],
            [sg.Listbox([], key='accounts_list', size=(40, 10))],
            [sg.Button('Remove Selected', key='remove_account_btn')],
        ]
    
    def get_income_section(self) -> List:
        """Income streams section."""
        return [
            [sg.Text('INCOME STREAMS', font=('Arial', 14, 'bold'))],
            [sg.Text('Enter all sources of retirement income')],
            [sg.Text('')],
            
            [sg.Text('Income Source:', size=(15,)),
             sg.Combo(['Social Security', 'Pension', 'Part-time Work', 'Rental Income', 'Dividends'],
                     key='income_type', size=(23,), default_value='Social Security')],
            [sg.Text('Annual Amount:', size=(15,)), sg.Input('0', key='income_amount', size=(25,))],
            [sg.Text('Start Age:', size=(15,)), sg.Input('67', key='income_start_age', size=(25,))],
            [sg.Text('End Age:', size=(15,)), sg.Input('100', key='income_end_age', size=(25,))],
            [sg.Text('Growth Rate %:', size=(15,)), sg.Input('0', key='income_growth', size=(25,))],
            
            [sg.Button('Add Income', key='add_income_btn'),
             sg.Button('Clear Form', key='clear_income_btn')],
            
            [sg.Text('')],
            [sg.Text('Income Streams Added:', font=('Arial', 11, 'bold'))],
            [sg.Listbox([], key='income_list', size=(40, 10))],
            [sg.Button('Remove Selected', key='remove_income_btn')],
        ]
    
    def get_expenses_section(self) -> List:
        """Expenses section."""
        return [
            [sg.Text('RETIREMENT EXPENSES', font=('Arial', 14, 'bold'))],
            [sg.Text('Enter your projected retirement spending')],
            [sg.Text('')],
            
            [sg.Text('Annual Expenses:', size=(15,)), sg.Input('76000', key='annual_expense', size=(25,))],
            [sg.Text('Monthly Expenses:', size=(15,)), sg.Text('—', key='display_monthly', size=(25,))],
            
            [sg.Text('')],
            [sg.Checkbox('Expenses increase with inflation', default=True, key='expense_inflation')],
            [sg.Text('Annual Increase %:', size=(15,)), sg.Input('2.5', key='expense_growth', size=(25,))],
            
            [sg.Text('')],
            [sg.Text('Healthcare Costs:', size=(15,)), sg.Input('0', key='healthcare_cost', size=(25,))],
            [sg.Text('Long-term Care Reserve:', size=(15,)), sg.Input('0', key='ltc_reserve', size=(25,))],
            
            [sg.Text('')],
            [sg.Button('Calculate Burn Rate', key='calc_burn_rate')],
        ]
    
    def get_settings_section(self) -> List:
        """Simulation settings section."""
        return [
            [sg.Text('ANALYSIS SETTINGS', font=('Arial', 14, 'bold'))],
            [sg.Text('Configure simulation parameters')],
            [sg.Text('')],
            
            [sg.Text('Projection Years:', size=(15,)),
             sg.Combo(['30', '35', '40'], key='projection_years', size=(23,), default_value='30')],
            
            [sg.Text('Tax Year (Start):', size=(15,)),
             sg.Combo(list(range(2026, 2056)), key='tax_year_start', 
                     size=(23,), default_value=2026)],
            
            [sg.Text('Average Investment Return:', size=(15,)),
             sg.Input('7.0', key='investment_return', size=(25,))],
            
            [sg.Text('Inflation Rate:', size=(15,)),
             sg.Input('2.5', key='inflation_rate', size=(25,))],
            
            [sg.Text('')],
            [sg.Text('Optimization Objectives:', font=('Arial', 11, 'bold'))],
            [sg.Checkbox('Maximize Roth Value', default=True, key='obj_roth')],
            [sg.Checkbox('Minimize Taxes', default=True, key='obj_tax')],
            [sg.Checkbox('Maximize Net Worth', default=True, key='obj_networth')],
            [sg.Checkbox('Minimize IRMAA Impact', default=True, key='obj_irmaa')],
            
            [sg.Text('')],
            [sg.Button('Reset to Defaults', key='reset_settings')],
        ]
    
    def show_help_window(self):
        """Show comprehensive help window."""
        help_text = """
ROTH CONVERSION SIMULATOR - HELP

This tool helps you optimize your Roth conversion strategy by:
1. Modeling your current financial situation
2. Projecting income, expenses, and account growth
3. Calculating taxes, RMDs, and IRMAA impacts
4. Comparing multiple conversion strategies
5. Providing personalized recommendations

FEATURES:
📋 SEARCH: Find field definitions and help
💡 ML RECOMMENDATIONS: Get smart suggestions based on your profile
📚 SOURCE RETRIEVAL: See citations for tax rules and calculations
🔄 MULTI-SCENARIO: Compare 4+ optimization strategies

GETTING STARTED:
1. Fill in your personal information (Client tab)
2. Enter all retirement accounts (Accounts tab)
3. Add income sources (Income tab)
4. Set spending projections (Expenses tab)
5. Customize analysis settings (Settings tab)
6. Click "Analyze" to run optimization

INTERPRETATION:
- Final Net Worth: Total projected wealth at age 100
- Final Roth Value: Tax-free Roth account balance
- Total Taxes Paid: Cumulative tax liability
- IRMAA Costs: Additional Medicare premiums

Questions? Hover over field names or search in the left panel.
        """
        sg.popup_scrolled(help_text, title='Help', size=(60, 30))
    
    def validate_inputs(self, values: Dict) -> bool:
        """Validate that required fields are filled."""
        required_fields = ['first_name', 'last_name', 'birth_year', 'annual_expense']
        
        for field in required_fields:
            if not values.get(field, '').strip():
                return False
        
        return True
    
    def collect_data(self, values: Dict):
        """Collect and validate all user data."""
        try:
            # Parse client profile
            self.client = ClientProfile(
                first_name=values['first_name'],
                last_name=values['last_name'],
                birth_year=int(values['birth_year']),
                spouse_birth_year=int(values['spouse_birth_year']) if values.get('spouse_birth_year') else None,
                state_residence=values.get('state_residence', 'ID'),
                filing_status=values.get('filing_status', 'single'),
            )
            
            # Expenses
            self.expenses = Expenses(
                annual_amount=float(values.get('annual_expense', 0)),
                annual_inflation_rate=float(values.get('expense_growth', 0.025)),
            )
        
        except ValueError as e:
            sg.popup_error(f'Invalid input: {str(e)}')
    
    def run_optimization(self):
        """Run the optimization analysis."""
        if not self.client:
            sg.popup_error('Please fill in all required information first')
            return
        
        # TODO: Run actual simulation
        sg.popup_info('Running optimization... (feature coming soon)')


def main():
    """Launch the GUI v2."""
    gui = RothSimulatorGUIv2()
    gui.run()


if __name__ == '__main__':
    main()
