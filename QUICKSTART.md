# Roth Conversion Simulator - Quick Start Guide

## Overview

Your Roth Conversion Simulator is a comprehensive Python application for optimizing retirement Roth conversion strategies. It models your complete financial picture and generates optimal conversion plans until age 100.

## Installation

### Prerequisites
- Python 3.9+ (tested with Python 3.13)
- pip (Python package manager)

### Setup

1. **Navigate to the project directory:**
   ```bash
   cd C:\Users\kyle8\OneDrive\Documents\steve-finance
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   This installs: PySimpleGUI, pandas, numpy, scipy, matplotlib, openpyxl, pyyaml

## Quick Start

### Option 1: Run the Example Analysis (Recommended First)

This demonstrates all features without the GUI:

```bash
python example_analysis.py
```

**What it does:**
- Creates a sample client (married couple, ages 66/64)
- Defines 4 retirement accounts ($1M total)
- Sets up 3 income streams (Social Security, pension)
- Runs 4 different optimization scenarios
- Displays comparison results
- Exports year-by-year details to CSV

**Output:**
- Console comparison table showing all 4 strategies
- Rankings by different metrics (Net Worth, Roth Value, Tax Paid)
- Year-by-year detail for top strategy
- CSV export: `example_strategy_detail.csv`

### Option 2: Run the GUI Application

For interactive analysis:

```bash
python main.py
```

**What it does:**
1. Opens 5-step guided wizard:
   - Step 1: Your profile (name, age, spouse, state)
   - Step 2: Your accounts (IRAs, 401k, taxable)
   - Step 3: Income sources (Social Security, pensions)
   - Step 4: Annual expenses
   - Step 5: Choose optimization objectives

2. Runs simulation for selected scenarios
3. Shows comparison results
4. Allows exporting to CSV

## Running Tests

Verify the installation works correctly:

```bash
# All tax calculation tests
python -m unittest tests.test_tax_calculator -v

# All simulator tests
python -m unittest tests.test_simulator -v

# Run all tests
python -m unittest discover tests -v
```

Expected result: **All tests pass** ✓

## Project Structure

```
steve-finance/
├── src/
│   ├── __init__.py           # Package initialization
│   ├── constants.py          # Tax brackets, IRMAA, RMD tables
│   ├── models.py             # Data classes
│   ├── tax_calculator.py     # Tax & IRMAA calculations
│   ├── simulator.py          # Core simulation engine
│   ├── optimizer.py          # Multi-scenario comparison
│   └── gui.py                # PySimpleGUI interface
├── tests/
│   ├── __init__.py
│   ├── test_tax_calculator.py  # 21 unit tests
│   └── test_simulator.py       # 11 unit tests
├── docs/
│   └── TECHNICAL.md          # Architecture & algorithms
├── data/                     # For future data files
├── main.py                   # GUI application entry point
├── example_analysis.py       # Standalone example
├── requirements.txt          # Python dependencies
├── README.md                 # Full documentation
└── QUICKSTART.md             # This file
```

## Key Features

### 1. Account Types Supported
- Traditional IRA
- Roth IRA
- SEP IRA
- Solo 401(k)
- Employer 401(k)/403(b)
- HSA
- Taxable Brokerage
- Pension

### 2. Income Streams
- W2 Employment Income
- Self-Employment Income
- Social Security
- Pensions
- Investment Dividends

### 3. Tax Calculations
- Federal progressive tax brackets (2026)
- All 50 states + DC tax rates
- IRMAA (Medicare premium adjustments)
- RMD calculations with pro-rata rule
- Marginal tax rate determination

### 4. Optimization Objectives
1. **Maximize Roth Value** - Build tax-free accounts aggressively
2. **Maximize Gross Net Worth** - Highest total value
3. **Minimize Tax Paid** - Lowest lifetime tax burden
4. **Minimize IRMAA** - Avoid Medicare premium increases
5. **Maximize Inheritance** - Best legacy value
6. **Balanced Growth** - Reasonable middle ground

### 5. Analysis Outputs
- Side-by-side strategy comparison
- Year-by-year projections (age 65 to 100)
- Total conversions, taxes, and final values
- CSV export for further analysis
- Breakeven analysis between strategies

## Example Output

Running `example_analysis.py` produces:

```
=== Roth Conversion Analysis for John Smith ===
Current Age: 66, Spouse Age: 64

ACCOUNTS:
  Traditional IRA           Traditional IRA      $        400,000
  Roth IRA                  Roth IRA             $        150,000
  401(k)                    401(k)               $        250,000
  Taxable Brokerage         Taxable Brokerage    $        200,000
  TOTAL                                          $      1,000,000

INCOME STREAMS:
  Social Security (Primary)      $      32,000/year (ages 67-100)
  Social Security (Spouse)       $      28,000/year (ages 67-100)
  Pension                        $      45,000/year (ages 65-100)

ANNUAL EXPENSES: $76,000
MONTHLY EXPENSES: $6,333

ANALYZING 4 SCENARIOS...

========================================================
SCENARIO COMPARISON RESULTS
========================================================

Strategy                         Final Net Worth    Final Roth Value
Maximize Roth Value Strategy     $    4,359,261     $    1,307,499
Minimize Tax Paid Strategy       $   29,776,109     $    8,691,964
Maximize Gross Net Worth Strategy$  214,334,094     $   66,165,447
Minimize IRMAA Impact Strategy   $1,560,752,903     $  503,668,257

...

Detailed results exported to: example_strategy_detail.csv
```

## Using Your Own Data

### To analyze YOUR situation:

1. **Gather your information:**
   - Current age (and spouse's if married)
   - State of residence
   - All account balances (Traditional IRA, 401k, Roth, etc.)
   - Expected growth rates for each account
   - Income sources (Social Security, pensions, etc.)
   - Expected annual expenses

2. **Run the GUI:**
   ```bash
   python main.py
   ```

3. **Follow the 5-step wizard** entering your information

4. **Select which strategies to compare** (or analyze all 6)

5. **Review results** and export to CSV for deeper analysis

### Or modify `example_analysis.py`:

Change the values in the main() function:
- Update `ClientProfile` with your info
- Modify `accounts` list with your actual account values
- Update `income_streams` with your real income
- Adjust `Expenses` to match your budget
- Run: `python example_analysis.py`

## Tax Year Updates

The simulator currently uses **2026 tax brackets and parameters**. To use different years:

1. Update `FEDERAL_TAX_BRACKETS_*` in `src/constants.py`
2. Update `STANDARD_DEDUCTION_*` 
3. Update `IRMAA_BRACKETS_*` for Medicare thresholds
4. Run tests to verify: `python -m unittest tests.test_tax_calculator -v`

## Important Notes

### ⚠️ This is a Planning Tool
- **NOT a substitute for professional advice**
- Always consult a CPA/tax advisor before conversions
- Rules change frequently - verify current tax law
- IRMAA and RMD ages subject to change

### Assumptions Made
- Constant annual growth rates
- No market volatility
- Projection to age 100
- Conversions executed January 1
- 2026 tax rates throughout
- No life expectancy variation

### Not Included
- Backdoor Roth conversions
- Mega Backdoor Roth
- Qualified Charitable Distributions (QCDs)
- Social Security optimization
- Spousal RMD strategies
- Complex estate planning

## Troubleshooting

### Import Error
**Error:** `ModuleNotFoundError: No module named 'PySimpleGUI'`

**Fix:** 
```bash
pip install -r requirements.txt
```

### Can't run GUI
**Error:** `pygame not found` or similar

**Fix:** Try the example first:
```bash
python example_analysis.py
```

### Tests fail
**Error:** `AssertionError` in tests

**Fix:**
1. Verify Python version: `python --version` (need 3.9+)
2. Reinstall packages: `pip install --upgrade -r requirements.txt`
3. Run single test: `python -m unittest tests.test_tax_calculator.TestTaxCalculator.test_federal_tax_single_2026 -v`

## Next Steps

1. **Try the example:** `python example_analysis.py`
2. **Understand the output:** Review results and CSV export
3. **Run the tests:** Verify everything works
4. **Read the docs:** Check `docs/TECHNICAL.md` for deep dive
5. **Modify for your situation:** Update `example_analysis.py` with your data
6. **Launch GUI:** `python main.py` when ready for interactive use

## Getting Help

### Documentation
- **README.md** - Full feature list and documentation
- **docs/TECHNICAL.md** - Architecture, algorithms, and extension points
- **example_analysis.py** - Working code example with inline comments

### Code Comments
- Run tests first to understand expected behavior
- Example output shows what to expect
- CSV export shows year-by-year details

## Advanced Usage

### Programmatic API

Use the simulator in your own Python code:

```python
from src.models import ClientProfile, Account, IncomeStream, Expenses, ScenarioSettings
from src.optimizer import ConversionOptimizer

# Create client
client = ClientProfile(
    first_name="John",
    last_name="Doe",
    birth_year=1960,
    state_residence="ID"
)

# Create accounts, income, expenses (see example_analysis.py)
# ...

# Run optimizer
optimizer = ConversionOptimizer(client)
scenarios = optimizer.generate_scenarios(
    base_scenario=ScenarioSettings(...),
    objectives=["Maximize Roth Value", "Minimize Tax Paid"]
)
strategies = optimizer.run_scenario_comparison(
    scenarios, accounts, income_streams, expenses
)

# Compare
comparison = optimizer.compare_strategies(strategies)
print(comparison)
```

## Version

**Current Version:** 0.1.0 (Initial Release)

**What's Working:**
- Core tax calculations ✓
- Simulation engine ✓
- 6 optimization objectives ✓
- All account types ✓
- IRMAA/RMD handling ✓
- GUI interface ✓
- CSV export ✓
- 32 unit tests (all passing) ✓

**Planned Features:**
- Monte Carlo simulation
- Backdoor Roth strategies
- Charitable planning
- Social Security optimization
- Multi-person scenarios
- Save/load profiles
- Charts and visualization
- Historical data integration

## Support

For issues or questions:
1. Check this file first
2. Review `docs/TECHNICAL.md` for architecture details
3. Look at `example_analysis.py` for code examples
4. Run tests to verify installation: `python -m unittest discover tests -v`

---

**Ready to get started? Try:** `python example_analysis.py`
