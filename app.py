"""Modern Flask web application for Roth conversion simulator."""

from flask import Flask, render_template, request, jsonify, send_file
from src.models import ClientProfile, Account, IncomeStream, Expenses, ScenarioSettings
from src.simulator import ConversionSimulator
from src.optimizer import ConversionOptimizer
from src.tax_calculator import TaxCalculator
from src.constants import ACCOUNT_TYPES, STATE_TAX_RATES
from datetime import datetime
import json
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['JSON_SORT_KEYS'] = False

# Session data storage
session_data = {
    'client': None,
    'accounts': [],
    'income_streams': [],
    'expenses': None,
    'results': None,
}

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')

@app.route('/api/states')
def get_states():
    """Get list of states."""
    return jsonify(sorted(STATE_TAX_RATES.keys()))

@app.route('/api/account-types')
def get_account_types():
    """Get list of account types."""
    return jsonify(ACCOUNT_TYPES)

@app.route('/api/save-client', methods=['POST'])
def save_client():
    """Save client profile."""
    data = request.json
    try:
        session_data['client'] = {
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'birth_year': int(data.get('birth_year', 0)),
            'spouse_birth_year': int(data.get('spouse_birth_year')) if data.get('spouse_birth_year') else None,
            'state_residence': data.get('state_residence', 'ID'),
            'filing_status': data.get('filing_status', 'single'),
            'current_age': datetime.now().year - int(data.get('birth_year', 0)),
            'spouse_age': datetime.now().year - int(data.get('spouse_birth_year', 0)) if data.get('spouse_birth_year') else None,
        }
        return jsonify({'success': True, 'message': 'Client profile saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/save-account', methods=['POST'])
def save_account():
    """Save account."""
    data = request.json
    try:
        account = {
            'name': data.get('name'),
            'type': data.get('type'),
            'balance': float(data.get('balance', 0)),
            'pretax': float(data.get('pretax', 0)),
            'aftertax': float(data.get('aftertax', 0)),
            'growth': float(data.get('growth', 7)) / 100,
            'contribution': float(data.get('contribution', 0)),
        }
        session_data['accounts'].append(account)
        return jsonify({'success': True, 'message': 'Account added', 'total_accounts': len(session_data['accounts'])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/get-accounts')
def get_accounts():
    """Get all accounts."""
    return jsonify(session_data['accounts'])

@app.route('/api/delete-account/<int:index>', methods=['DELETE'])
def delete_account(index):
    """Delete account."""
    try:
        if 0 <= index < len(session_data['accounts']):
            session_data['accounts'].pop(index)
            return jsonify({'success': True, 'message': 'Account deleted'})
        return jsonify({'success': False, 'error': 'Invalid index'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/save-income', methods=['POST'])
def save_income():
    """Save income stream."""
    data = request.json
    try:
        income = {
            'type': data.get('type'),
            'amount': float(data.get('amount', 0)),
            'start_age': int(data.get('start_age', 67)),
            'end_age': int(data.get('end_age', 100)),
            'growth': float(data.get('growth', 0)) / 100,
        }
        session_data['income_streams'].append(income)
        return jsonify({'success': True, 'message': 'Income stream added', 'total_income': len(session_data['income_streams'])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/get-income')
def get_income():
    """Get all income streams."""
    return jsonify(session_data['income_streams'])

@app.route('/api/delete-income/<int:index>', methods=['DELETE'])
def delete_income(index):
    """Delete income stream."""
    try:
        if 0 <= index < len(session_data['income_streams']):
            session_data['income_streams'].pop(index)
            return jsonify({'success': True, 'message': 'Income stream deleted'})
        return jsonify({'success': False, 'error': 'Invalid index'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/save-expenses', methods=['POST'])
def save_expenses():
    """Save expenses."""
    data = request.json
    try:
        session_data['expenses'] = {
            'annual': float(data.get('annual', 0)),
            'inflation': float(data.get('inflation', 2.5)) / 100,
            'healthcare': float(data.get('healthcare', 0)),
            'ltc': float(data.get('ltc', 0)),
        }
        return jsonify({'success': True, 'message': 'Expenses saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Run comprehensive analysis with projections and strategies."""
    try:
        if not session_data['client'] or not session_data['accounts'] or not session_data['expenses']:
            return jsonify({'success': False, 'error': 'Please complete all sections first'}), 400
        
        data = request.json
        
        # Create client profile
        client = ClientProfile(
            first_name=session_data['client']['first_name'],
            last_name=session_data['client']['last_name'],
            birth_year=session_data['client']['birth_year'],
            spouse_birth_year=session_data['client']['spouse_birth_year'],
            state_residence=session_data['client']['state_residence'],
            filing_status=session_data['client']['filing_status'],
        )
        
        # Create accounts
        accounts = [
            Account(
                name=acc['name'],
                account_type=acc['type'],
                current_balance=acc['balance'],
                pretax_basis=acc['pretax'],
                aftertax_basis=acc['aftertax'],
                expected_growth_rate=acc['growth'],
                annual_contribution=acc['contribution'],
            )
            for acc in session_data['accounts']
        ]
        
        # Create income streams
        income_streams = [
            IncomeStream(
                source_type=inc['type'],
                annual_amount=inc['amount'],
                start_age=inc['start_age'],
                end_age=inc['end_age'],
                annual_growth_rate=inc['growth'],
            )
            for inc in session_data['income_streams']
        ]
        
        # Create expenses
        expenses = Expenses(
            annual_amount=session_data['expenses']['annual'],
            annual_inflation_rate=session_data['expenses']['inflation'],
            healthcare_annual=session_data['expenses']['healthcare'],
            ltc_reserve=session_data['expenses']['ltc'],
        )
        
        # Run simulation
        simulator = ConversionSimulator(client, accounts, income_streams, expenses)
        projection_years = int(data.get('projection_years', 30))
        results = simulator.run_full_simulation(projection_years)
        
        # Run optimizer
        optimizer = ConversionOptimizer()
        strategies = optimizer.run_scenario_comparison(
            client, accounts, income_streams, expenses, projection_years
        )
        
        # Generate projection data and charts
        projections = generate_projections(client, accounts, income_streams, expenses, projection_years)
        charts = generate_charts(projections, strategies)
        
        # Calculate advanced metrics
        metrics = calculate_advanced_metrics(client, accounts, income_streams, expenses, strategies)
        
        session_data['results'] = {
            'total_accounts': len(accounts),
            'total_balance': sum(acc.current_balance for acc in accounts),
            'total_income': sum(inc.annual_amount for inc in income_streams),
            'annual_expenses': expenses.annual_amount,
            'strategies': [
                {
                    'name': s['strategy_name'],
                    'objective': s['objective'],
                    'total_conversions': s['total_conversions'],
                    'total_taxes': s['total_taxes_paid'],
                    'final_roth': s['final_roth_value'],
                    'final_networth': s['final_net_worth'],
                }
                for s in strategies
            ],
            'projections': projections,
            'charts': charts,
            'metrics': metrics,
        }
        
        return jsonify({
            'success': True,
            'results': session_data['results'],
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 400


def generate_projections(client, accounts, income_streams, expenses, years):
    """Generate year-by-year financial projections."""
    projections = []
    current_year = datetime.now().year
    age = current_year - client.birth_year
    
    total_balance = sum(acc.current_balance for acc in accounts)
    total_income = sum(inc.annual_amount for inc in income_streams)
    
    balance = total_balance
    
    for year_idx in range(years):
        year = current_year + year_idx
        year_age = age + year_idx
        
        # Calculate year metrics
        annual_income = sum(
            inc.annual_amount * ((1 + inc.annual_growth_rate) ** year_idx)
            for inc in income_streams
            if year_age >= inc.start_age and year_age <= inc.end_age
        )
        
        annual_expenses = expenses.annual_amount * ((1 + expenses.annual_inflation_rate) ** year_idx)
        
        # Account growth
        balance_growth = balance * 0.07  # 7% average
        balance += balance_growth - (annual_expenses - annual_income)
        
        # RMD calculation (simplified)
        rmd = 0
        if year_age >= 73:
            # RMD = account balance / life expectancy factor
            rmd = balance / (120 - year_age + 1)
        
        # IRMAA calculation (simplified)
        irmaa = 0
        if annual_income > 94000:  # 2024 threshold
            income_excess = annual_income - 94000
            irmaa = min(income_excess * 0.03, 580)  # Simplified
        
        projections.append({
            'year': year,
            'age': year_age,
            'balance': round(balance, 2),
            'income': round(annual_income, 2),
            'expenses': round(annual_expenses, 2),
            'rmd': round(rmd, 2),
            'irmaa': round(irmaa, 2),
            'net_cash_flow': round(annual_income - annual_expenses, 2),
        })
    
    return projections


def generate_charts(projections, strategies):
    """Generate chart images as base64."""
    charts = {}
    
    try:
        # Chart 1: Balance Projection Over Time
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='#0f172a', edgecolor='none')
        ax.set_facecolor('#1e293b')
        
        years = [p['year'] for p in projections]
        balances = [p['balance'] / 1000000 for p in projections]
        
        ax.plot(years, balances, color='#3b82f6', linewidth=3, marker='o', markersize=4, label='Projected Balance')
        ax.fill_between(years, 0, balances, alpha=0.2, color='#3b82f6')
        
        ax.set_xlabel('Year', color='#cbd5e1', fontsize=11)
        ax.set_ylabel('Balance ($M)', color='#cbd5e1', fontsize=11)
        ax.set_title('Wealth Projection Over Time', color='#f1f5f9', fontsize=14, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.2, color='#475569', linestyle='--')
        ax.tick_params(colors='#cbd5e1')
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', facecolor='#0f172a')
        img.seek(0)
        charts['balance'] = base64.b64encode(img.getvalue()).decode()
        plt.close(fig)
        
        # Chart 2: Income vs Expenses
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='#0f172a', edgecolor='none')
        ax.set_facecolor('#1e293b')
        
        years = [p['year'] for p in projections]
        income = [p['income'] / 1000 for p in projections]
        expenses = [p['expenses'] / 1000 for p in projections]
        
        ax.plot(years, income, color='#10b981', linewidth=2.5, marker='o', markersize=3, label='Income')
        ax.plot(years, expenses, color='#ef4444', linewidth=2.5, marker='s', markersize=3, label='Expenses')
        ax.fill_between(years, income, alpha=0.2, color='#10b981')
        
        ax.set_xlabel('Year', color='#cbd5e1', fontsize=11)
        ax.set_ylabel('Amount ($k)', color='#cbd5e1', fontsize=11)
        ax.set_title('Income vs Expenses Projection', color='#f1f5f9', fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', framealpha=0.9, facecolor='#334155')
        ax.grid(True, alpha=0.2, color='#475569', linestyle='--')
        ax.tick_params(colors='#cbd5e1')
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', facecolor='#0f172a')
        img.seek(0)
        charts['income_expenses'] = base64.b64encode(img.getvalue()).decode()
        plt.close(fig)
        
        # Chart 3: Strategy Comparison
        fig, ax = plt.subplots(figsize=(12, 6), facecolor='#0f172a', edgecolor='none')
        ax.set_facecolor('#1e293b')
        
        strategy_names = [s['name'] for s in strategies[:4]]
        final_wealth = [s['final_networth'] / 1000000 for s in strategies[:4]]
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
        
        bars = ax.barh(strategy_names, final_wealth, color=colors, alpha=0.8)
        ax.set_xlabel('Final Net Worth ($M)', color='#cbd5e1', fontsize=11)
        ax.set_title('Strategy Comparison - Final Net Worth', color='#f1f5f9', fontsize=14, fontweight='bold', pad=20)
        ax.tick_params(colors='#cbd5e1')
        
        for i, (bar, value) in enumerate(zip(bars, final_wealth)):
            ax.text(value, i, f'  ${value:.1f}M', va='center', color='#cbd5e1', fontsize=10, fontweight='bold')
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight', facecolor='#0f172a')
        img.seek(0)
        charts['strategies'] = base64.b64encode(img.getvalue()).decode()
        plt.close(fig)
        
    except Exception as e:
        print(f"Chart generation error: {e}")
    
    return charts


def calculate_advanced_metrics(client, accounts, income_streams, expenses, strategies):
    """Calculate advanced financial metrics."""
    metrics = {}
    
    current_age = datetime.now().year - client.birth_year
    total_assets = sum(acc.current_balance for acc in accounts)
    annual_income = sum(inc.annual_amount for inc in income_streams)
    
    # Expense ratio
    expense_ratio = expenses.annual_amount / annual_income if annual_income > 0 else 0
    
    # Safe withdrawal rate (4% rule)
    safe_withdrawal = total_assets * 0.04
    
    # Asset allocation
    pretax_total = sum(acc.pretax_basis for acc in accounts)
    aftertax_total = sum(acc.aftertax_basis for acc in accounts)
    roth_total = sum(acc.current_balance for acc in accounts if 'Roth' in acc.account_type)
    
    metrics = {
        'current_age': current_age,
        'total_assets': round(total_assets, 2),
        'annual_income': round(annual_income, 2),
        'annual_expenses': round(expenses.annual_amount, 2),
        'expense_ratio': round(expense_ratio * 100, 1),
        'safe_withdrawal': round(safe_withdrawal, 2),
        'pretax_pct': round((pretax_total / total_assets * 100) if total_assets > 0 else 0, 1),
        'aftertax_pct': round((aftertax_total / total_assets * 100) if total_assets > 0 else 0, 1),
        'roth_pct': round((roth_total / total_assets * 100) if total_assets > 0 else 0, 1),
        'years_to_retirement': max(0, 65 - current_age),
        'life_expectancy_analysis': 'On track' if expense_ratio < 1 else 'May need adjustments',
    }
    
    return metrics

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Clear session data."""
    global session_data
    session_data = {
        'client': None,
        'accounts': [],
        'income_streams': [],
        'expenses': None,
        'results': None,
    }
    return jsonify({'success': True, 'message': 'Session cleared'})

@app.route('/api/international-strategies')
def get_international_strategies():
    """Get available international tax optimization strategies."""
    strategies = [
        {
            'id': 'expat-exemption',
            'name': 'Foreign Earned Income Exclusion (FEIE)',
            'description': 'Exclude up to $120,000 of foreign earned income from US taxation',
            'requirements': [
                'Physical presence test (330+ days outside US per 12-month period)',
                'Bona fide residency in foreign country',
                'Foreign earned income only (not investment income)',
            ],
            'tax_savings': 'Up to $36,000 annual savings (at 30% rate)',
            'countries': ['Mexico', 'Portugal', 'Costa Rica', 'Thailand', 'Panama', 'Philippines'],
            'complexity': 'Moderate',
            'risk': 'Medium - IRS scrutinizes this heavily',
        },
        {
            'id': 'foreign-tax-credit',
            'name': 'Foreign Tax Credit (FTC)',
            'description': 'Claim credit for taxes paid to foreign governments',
            'requirements': [
                'Income sourced in foreign country',
                'Paid taxes to foreign government',
                'Not claimed as deduction',
            ],
            'tax_savings': 'Varies by country (10-45% rates globally)',
            'countries': ['All'],
            'complexity': 'Moderate',
            'risk': 'Low - well-established rule',
        },
        {
            'id': 'treaty-planning',
            'name': 'Tax Treaty Planning',
            'description': 'Leverage US tax treaties to reduce withholding taxes',
            'requirements': [
                'Residency in treaty country',
                'Investment income eligible under treaty',
                'Proper tax residency documentation',
            ],
            'tax_savings': 'Reduces withholding from 30% to 5-15%',
            'countries': ['Most developed nations'],
            'complexity': 'High',
            'risk': 'Medium - careful documentation required',
        },
        {
            'id': 'hong-kong-corp',
            'name': 'Hong Kong Corporation Strategy',
            'description': 'Use Hong Kong entity for investment income deferral',
            'requirements': [
                'Non-resident status for HK purposes',
                'Investment income only (not Hong Kong sourced)',
                'Proper corporate structure',
            ],
            'tax_savings': '15-20% deferral advantage',
            'countries': ['Hong Kong'],
            'complexity': 'Very High',
            'risk': 'High - GILTI rules may apply',
        },
        {
            'id': 'singapore-planning',
            'name': 'Singapore Private Wealth Structure',
            'description': 'Establish Singapore residency for favorable tax treatment',
            'requirements': [
                'Genuine relocation to Singapore',
                '3-5 year commitment typically required',
                'Foreigners taxed only on Singapore-source income',
            ],
            'tax_savings': 'Up to 50% reduction on investment income',
            'countries': ['Singapore'],
            'complexity': 'High',
            'risk': 'Medium - requires genuine move',
        },
        {
            'id': 'uae-residency',
            'name': 'UAE Residency (Zero Income Tax)',
            'description': 'Move to UAE which has no personal income tax',
            'requirements': [
                'Genuine relocation and residence',
                'Valid UAE residency visa',
                '183+ days in UAE annually',
            ],
            'tax_savings': '0% on personal income (31-55% reduction)',
            'countries': ['UAE'],
            'complexity': 'Moderate',
            'risk': 'Low - straightforward rule',
        },
        {
            'id': 'portugal-nhr',
            'name': 'Portugal Non-Habitual Resident (NHR)',
            'description': 'Tax exemption on foreign income for 10 years',
            'requirements': [
                'New resident to Portugal',
                'Not been resident in 5 previous years',
                'Foreign-source income',
            ],
            'tax_savings': '0% tax on foreign income (10 years)',
            'countries': ['Portugal'],
            'complexity': 'Moderate',
            'risk': 'Low - established program',
        },
        {
            'id': 'panama-residency',
            'name': 'Panama Pensioner Visa',
            'description': 'Territorial tax system - foreign income not taxed',
            'requirements': [
                'Monthly pension/income of $1,000+',
                'Panamanian residency',
                'Foreign-source income only',
            ],
            'tax_savings': '0% on foreign income',
            'countries': ['Panama'],
            'complexity': 'Low',
            'risk': 'Low - clear rules',
        },
    ]
    return jsonify(strategies)

@app.route('/api/calculate-international-tax', methods=['POST'])
def calculate_international_tax():
    """Calculate tax savings from international strategy."""
    data = request.json
    strategy = data.get('strategy')
    annual_income = float(data.get('income', 0))
    current_tax_rate = float(data.get('current_rate', 0.30))
    
    savings_estimates = {
        'expat-exemption': {'rate': 0, 'cap': 120000},
        'foreign-tax-credit': {'rate': 0.10, 'cap': None},  # Varies
        'treaty-planning': {'rate': current_tax_rate - 0.15, 'cap': None},
        'hong-kong-corp': {'rate': 0.07, 'cap': None},
        'singapore-planning': {'rate': current_tax_rate * 0.5, 'cap': None},
        'uae-residency': {'rate': 0, 'cap': None},
        'portugal-nhr': {'rate': 0, 'cap': None},
        'panama-residency': {'rate': 0, 'cap': None},
    }
    
    if strategy not in savings_estimates:
        return jsonify({'success': False, 'error': 'Unknown strategy'}), 400
    
    est = savings_estimates[strategy]
    taxable = min(annual_income, est['cap']) if est['cap'] else annual_income
    annual_savings = taxable * current_tax_rate - taxable * est['rate']
    lifetime_savings = annual_savings * 30  # 30 year projection
    
    return jsonify({
        'success': True,
        'annual_savings': round(annual_savings, 2),
        'lifetime_savings': round(lifetime_savings, 2),
        'effective_rate_after': round(est['rate'] * 100, 1),
    })

@app.route('/api/backdoor-roth-calculation', methods=['POST'])
def backdoor_roth_calculation():
    """Calculate backdoor Roth conversion benefits."""
    data = request.json
    conversion_amount = float(data.get('amount', 0))
    current_tax_rate = float(data.get('tax_rate', 0.30))
    years_to_retirement = int(data.get('years', 30))
    growth_rate = float(data.get('growth', 0.07))
    
    # Tax owed on conversion
    tax_owed = conversion_amount * current_tax_rate
    
    # Growth in Roth (tax-free)
    future_value = conversion_amount * ((1 + growth_rate) ** years_to_retirement)
    
    # Tax saved on growth
    tax_saved_on_growth = (future_value - conversion_amount) * current_tax_rate
    
    # Net benefit
    net_benefit = tax_saved_on_growth - tax_owed
    
    return jsonify({
        'success': True,
        'conversion_amount': round(conversion_amount, 2),
        'tax_owed': round(tax_owed, 2),
        'future_value': round(future_value, 2),
        'tax_saved_on_growth': round(tax_saved_on_growth, 2),
        'net_benefit': round(net_benefit, 2),
        'benefit_percentage': round((net_benefit / conversion_amount * 100) if conversion_amount > 0 else 0, 1),
    })

@app.route('/api/strategy-comparison', methods=['POST'])
def strategy_comparison():
    """Compare multiple tax strategies."""
    data = request.json
    annual_income = float(data.get('income', 0))
    current_rate = float(data.get('rate', 0.30))
    years = int(data.get('years', 30))
    
    strategies = [
        {'name': 'Do Nothing (US Only)', 'annual_tax': annual_income * current_rate, 'rate': current_rate},
        {'name': 'FEIE (Foreign Earned)', 'annual_tax': max(0, (annual_income - 120000) * current_rate), 'rate': (max(0, annual_income - 120000) / annual_income * current_rate) if annual_income > 0 else 0},
        {'name': 'Singapore Residency', 'annual_tax': annual_income * current_rate * 0.5, 'rate': current_rate * 0.5},
        {'name': 'UAE No Income Tax', 'annual_tax': 0, 'rate': 0},
        {'name': 'Portugal NHR', 'annual_tax': 0, 'rate': 0},
    ]
    
    for strategy in strategies:
        strategy['lifetime_tax'] = strategy['annual_tax'] * years
        strategy['annual_savings'] = annual_income * current_rate - strategy['annual_tax']
        strategy['lifetime_savings'] = strategy['annual_savings'] * years
    
    # Sort by savings
    strategies.sort(key=lambda x: x['lifetime_savings'], reverse=True)
    
    return jsonify({
        'success': True,
        'strategies': strategies,
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
