"""Project documentation and README."""

# ROTH CONVERSION SIMULATOR

A comprehensive financial planning tool for optimizing Roth conversion strategies from now through age 100+.

## Features

### Core Functionality
- **Multi-account tracking**: Traditional IRA, Roth IRA, SEP IRA, Solo 401(k), Employer 401(k), 403(b), HSA, Taxable Brokerage, Pensions
- **Income streams**: Multiple income sources with independent growth rates and tax treatment
- **Detailed tax calculations**: Federal + state income tax with all-state support
- **IRMAA analysis**: Medicare premium adjustments based on income level
- **RMD calculations**: Required Minimum Distributions with pro-rata rule support
- **Pro-rata conversions**: Automatic blending of pre-tax and after-tax contributions

### Optimization
- **Multiple objectives**:
  - Maximize Roth Value
  - Maximize Gross Net Worth
  - Minimize Tax Paid
  - Minimize IRMAA Impact
  - Maximize Inheritance
  - Balanced Growth
- **Scenario comparison**: Run all objectives simultaneously
- **Breakeven analysis**: Identify when strategies cross over
- **CSV export**: Year-by-year details for all scenarios

### User Interface
- **PySimpleGUI**: Cross-platform desktop application
- **Interactive wizard**: 5-step guided setup (Client → Accounts → Income → Expenses → Scenarios)
- **Results dashboard**: Compare strategies side-by-side
- **Detail views**: Drill down into year-by-year projections

## Installation

```bash
# Clone or download the repository
cd steve-finance

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run the application
python main.py
```

The app will guide you through:
1. **Client Profile** - Your age, spouse age, state residence, filing status
2. **Accounts** - All retirement accounts with current balances and projected growth
3. **Income Streams** - Social Security, pensions, employment income, etc.
4. **Expenses** - Annual living costs by category
5. **Scenarios** - Choose which optimization objectives to analyze

After running, you'll see:
- Side-by-side comparison of all strategies
- Total conversions, taxes paid, IRMAA costs, final account values
- Detailed year-by-year breakdown for each scenario
- Option to export results to CSV

## Project Structure

```
steve-finance/
├── src/
│   ├── __init__.py
│   ├── constants.py           # Tax brackets, IRMAA, RMD tables, state rates
│   ├── models.py              # Data classes for accounts, income, scenarios
│   ├── tax_calculator.py      # Tax, IRMAA, RMD calculations
│   ├── simulator.py           # Core simulation engine
│   ├── optimizer.py           # Multi-scenario comparison
│   └── gui.py                 # PySimpleGUI interface
├── data/
│   ├── sample_client.yaml     # Example client profile
│   └── tax_brackets_*.json    # Historical/projected tax brackets
├── tests/
│   ├── test_tax_calculator.py
│   ├── test_simulator.py
│   └── test_optimizer.py
├── docs/
│   └── TECHNICAL.md           # Architecture and algorithm details
├── main.py                    # Application entry point
└── requirements.txt           # Python dependencies
```

## Key Algorithms

### Tax Calculation
- Determines taxable income after standard deduction
- Applies progressive federal tax brackets
- Adds state income tax (varies by state)
- Handles qualified dividend rates (0%/15%/20%)

### IRMAA Calculation
- Determines Medicare Part B/D premium tiers
- Checks if conversion would trigger IRMAA
- Calculates monthly adjustment amounts (up to $385+/month per person)

### RMD Calculation
- Uses IRS Uniform Lifetime Table (age 73+ required)
- Applies pro-rata rule: (pre-tax basis / total basis) × withdrawal = taxable portion
- Tracks pro-rata ratio across all IRA accounts

### Roth Conversion Strategy
- **Fill Tax Bracket**: Convert up to the top of current tax bracket
- **Avoid IRMAA**: Don't exceed Medicare premium thresholds
- **Balance**: Convert aggressively but stay tax-efficient
- **Fixed Amount**: Convert specified $ amount annually

## Tax Year Parameters

The simulator includes 2026 tax brackets and parameters. To use other years:
1. Update `FEDERAL_TAX_BRACKETS_*` in `constants.py`
2. Update `STANDARD_DEDUCTION_*` in `constants.py`
3. Update `IRMAA_BRACKETS_*` for Medicare thresholds
4. Update `STATE_TAX_RATES` for state-specific changes

## Advanced Features (Roadmap)

- [ ] Save/load client profiles
- [ ] Multiple scenario comparison charts
- [ ] Sensitivity analysis (what if growth rates change?)
- [ ] Backdoor Roth conversions
- [ ] Qualified Charitable Distributions (QCDs)
- [ ] Social Security optimization
- [ ] Withdrawing strategically from taxable accounts (tax-loss harvesting awareness)
- [ ] Spouse synchronization (dual-person scenarios)
- [ ] Historical performance data integration
- [ ] Monte Carlo simulation for uncertainty

## Important Disclaimers

This tool is for **educational and planning purposes only** and does not constitute financial, tax, or legal advice. 

- Always consult with a qualified tax professional before making conversion decisions
- State tax treatment varies significantly (some states exempt retirement income)
- Federal law changes frequently; verify current rules
- IRMAA brackets and RMD ages subject to change
- Your specific situation may have unique factors this tool doesn't model

## Contributing

To improve the tool:
1. Test scenarios against real client data
2. Add missing account types or income sources
3. Update tax brackets for new years
4. Improve UI/UX
5. Add visualization/charting

## License

MIT License - See LICENSE.txt

## Support

For questions, issues, or feature requests, please create an issue in the repository.

## Version

v0.1.0 - Initial release
- Core simulator with 6 optimization objectives
- All major account types and income sources
- Federal + state tax calculations
- IRMAA and RMD handling
- PySimpleGUI interface
- CSV export

---

**Last Updated**: November 2026
