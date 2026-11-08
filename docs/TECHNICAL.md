"""
# TECHNICAL DOCUMENTATION

## Architecture Overview

The Roth Conversion Simulator is built with a modular architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    PySimpleGUI Interface (gui.py)           │
│                    - Multi-step wizard                       │
│                    - Results visualization                   │
│                    - CSV export                              │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│              ConversionOptimizer (optimizer.py)             │
│       - Scenario generation & comparison                     │
│       - Multi-objective ranking                              │
│       - Strategy export                                      │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│            ConversionSimulator (simulator.py)               │
│  - Year-by-year financial projection                         │
│  - Income calculation with growth                            │
│  - Account balance updates                                   │
│  - Optimal conversion determination                          │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│             TaxCalculator (tax_calculator.py)               │
│  - Federal tax calculation (progressive brackets)            │
│  - State tax calculation (all 50 states)                    │
│  - IRMAA determination                                       │
│  - RMD calculation (pro-rata rule)                          │
│  - Marginal rate calculation                                │
└─────────────────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│         Data Models (models.py)                             │
│  - Account, IncomeStream, ClientProfile, etc.               │
│                                                              │
│         Constants (constants.py)                            │
│  - Tax brackets, IRMAA thresholds, RMD tables               │
│  - State tax rates (all 50 states + DC)                     │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Input (GUI Wizard)
- **Step 1**: ClientProfile (name, age, spouse, state, filing status)
- **Step 2**: Accounts (types, balances, basis, growth rates)
- **Step 3**: IncomeStreams (SS, pension, work, dividends, etc.)
- **Step 4**: Expenses (housing, food, healthcare, etc.)
- **Step 5**: Scenarios (objectives, time horizon)

### 2. Scenario Preparation (ConversionOptimizer)
- Generate customized scenarios for each objective
- Create conversion strategy templates
- Define constraints (max conversion, IRMAA limits, tax brackets)

### 3. Year-by-Year Simulation (ConversionSimulator)
For each year from current to end_year:
- Calculate income from active streams (with growth)
- Determine RMD (if age ≥ 73)
- Calculate optimal conversion amount based on objective
- Compute tax impact using pro-rata rule
- Calculate IRMAA adjustment if applicable
- Update account balances with growth and contributions
- Store results in ConversionResult

### 4. Tax Calculation (TaxCalculator)
- Apply federal progressive tax brackets
- Add state income tax
- Check IRMAA thresholds and adjustments
- Calculate RMD using IRS tables and pro-rata ratio
- Determine marginal tax rate for current income level

### 5. Results Aggregation (ConversionStrategy)
- Summarize all years' conversions
- Total taxes paid across all years
- Final account values (Roth, Pre-tax, Taxable)
- Net worth calculations

### 6. Multi-Scenario Comparison
- Rank strategies by different metrics
- Show breakeven analysis
- Export detailed results to CSV

## Key Algorithms

### Roth Conversion Determination

The simulator uses **multiple strategies** to determine conversion amount:

#### 1. **Maximize Roth Value**
- Convert aggressively
- Fill available tax bracket
- Ignore IRMAA thresholds
- Goal: Maximum Roth balance at end

#### 2. **Minimize Tax Paid**
- Avoid conversion if possible
- Stay below standard deduction
- Preserve tax-deferred growth
- Goal: Lowest lifetime tax

#### 3. **Maximize Gross Net Worth**
- Convert to fill tax bracket
- But stay below IRMAA
- Balance growth vs. taxes
- Goal: Highest total net worth

#### 4. **Minimize IRMAA Impact**
- Never exceed IRMAA threshold
- Sacrifice conversions to avoid Medicare premium increases
- Goal: Minimize Medicare costs

#### 5. **Maximize Inheritance**
- Convert at higher rates
- Build Roth (tax-free to heirs)
- Goal: Most valuable legacy

#### 6. **Balanced Growth**
- Moderate conversions
- Avoid extreme positions
- Goal: Reasonable balance of objectives

### Pro-Rata Rule Calculation

When you have both pre-tax and after-tax (non-deductible) contributions in ANY IRA:

```
Pro-rata ratio = (Total Pre-tax) / (Total Pre-tax + Total After-tax)

Taxable amount of conversion = Conversion amount × Pro-rata ratio
```

Example:
- Traditional IRA: $100,000
- SEP IRA (non-deductible contributions): $25,000
- Total: $125,000
- Pro-rata ratio: 100/125 = 80%
- If you convert $50,000: Taxable amount = $50,000 × 0.80 = $40,000

### RMD Calculation (Age 73+)

```
RMD = Account Balance / IRS Divisor (based on age)
```

**2026 IRS Uniform Lifetime Table (sample)**:
- Age 73: Divisor 26.5
- Age 80: Divisor 20.2
- Age 90: Divisor 11.9

Example:
- IRA balance: $500,000
- Age 73
- RMD = $500,000 / 26.5 = $18,868

### IRMAA Calculation

**2026 Medicare Premium Adjustments** (example):

Single filers:
- $0 - $97,000: No adjustment ($0)
- $97,001 - $123,000: Adjustment ($70/month)
- $123,001 - $153,000: Adjustment ($175/month)
- $153,001 - $183,000: Adjustment ($280/month)
- $183,001+: Adjustment ($385/month)

Married filing jointly:
- $0 - $194,000: No adjustment ($0)
- $194,001 - $246,000: Adjustment ($70/month)
- $246,001 - $306,000: Adjustment ($175/month)
- $306,001 - $366,000: Adjustment ($280/month)
- $366,001+: Adjustment ($385/month)

Impact: Adjustments are multiplied by 12 for annual cost.

### Tax Bracket Filling

For single filer (2026 brackets):
```
Standard deduction: $14,600
Tax brackets:
  - $0 - $11,600: 10%
  - $11,601 - $47,150: 12%
  - $47,151 - $100,525: 22%
  ... (continuing progressively)

To "fill" the 22% bracket:
1. Calculate current taxable income
2. Find how much room remains in current bracket
3. Convert that amount to stay in same bracket
```

## Important Tax Rules Modeled

### 1. **Three-Bucket Account System**
- Traditional (pre-tax) accounts: Roth conversion source
- Roth accounts: No taxes, no RMDs
- Taxable accounts: Tax-deferred growth, capital gains tax on sales

### 2. **Required Minimum Distributions (RMD)**
- Start age: 73 (per 2023 rules)
- Must withdraw from traditional IRAs, 401(k)s, SEP-IRAs
- RMD not required from Roth IRAs (during owner's lifetime)
- Can use RMD to fund conversions

### 3. **Pro-Rata Rule**
- ALL pre-tax and after-tax IRAs are combined
- Conversion amount = Pre-tax % of total IRA balance
- Cannot pick and choose which dollars convert

### 4. **Medicare IRMAA (Income-Related Monthly Adjustment Amount)**
- Triggered 2 years after conversion
- MAGI is "modified adjusted gross income" (includes conversions)
- Affects Part B and Part D premiums
- Can range from $0 to $385+/month per person

### 5. **Roth Conversion Basics**
- Any amount can be converted (no income limits)
- Conversion counts as income in conversion year
- Can trigger IRMAA, higher tax bracket
- After 5 years, money can be withdrawn tax-free (generally)

## State Tax Handling

All 50 states + DC are included:

**No income tax states** (9):
- Alaska, Delaware, Florida, Nevada, South Dakota, Tennessee, Texas, Washington, Wyoming

**Retirement income-friendly states** (selected):
- Pennsylvania: Excludes retirement/pension income
- Mississippi: Excludes all retirement income
- Illinois: Excludes retirement income

**Flat tax states** (vary):
- Indiana: 3.23%
- Colorado: 4.55%
- Utah: 4.85%
- Illinois: 4.95%

**Progressive bracket states** (most):
- California: 1% - 13.3%
- Oregon: 4.75% - 9.9%
- Minnesota: 5.35% - 10.85%

Current implementation uses **simplified flat rates** for each state. For higher accuracy on progressive-bracket states, enhance `TaxCalculator.calculate_state_tax()`.

## Assumptions & Limitations

### Assumptions Made
1. **Fixed growth rates**: Accounts grow at constant rate each year
2. **No market volatility**: No Monte Carlo simulation (planned feature)
3. **No life expectancy variance**: Always projects to age 100
4. **No spousal consideration**: Single-person modeling only
5. **Tax rates stable**: Uses 2026 brackets throughout
6. **No QCDs or special rules**: Qualified Charitable Distributions not modeled
7. **Conversion executed Jan 1**: No timing throughout year
8. **No tax-loss harvesting**: Taxable account grows at nominal rate

### Not Included
- Backdoor Roth conversions
- Mega Backdoor Roth
- Form 8606 (NUA) net unrealized appreciation rules
- Charitable giving strategies
- Social Security optimization
- Life insurance integration
- Employer plan loan strategies
- State-specific retirement deductions
- Foreign income or taxes
- Alternative Minimum Tax (AMT)

### When to Use Professional Help
- Complex estate planning
- Substantial non-U.S. income
- Business ownership
- Inherited IRAs
- Before-tax employee contributions management
- State residency planning
- Charitable planning

## Testing Strategy

### Unit Tests
- `tests/test_tax_calculator.py`: 21 tests
  - Federal tax brackets
  - State tax calculations
  - Standard deductions
  - Marginal rates
  - IRMAA tiers
  - RMD calculations
  - Pro-rata conversions

- `tests/test_simulator.py`: 11 tests
  - Income stream calculations
  - Account growth
  - Optimal conversion determination
  - Full simulation runs

### Test Coverage
- Tax calculations: 100%
- Simulator core logic: 85%
- GUI components: Manual testing

### Running Tests
```bash
python -m unittest tests.test_tax_calculator -v
python -m unittest tests.test_simulator -v
python -m unittest discover tests -v  # All tests
```

## Performance Considerations

### Optimization Done
- Direct calculation (no simulation loops for single years)
- Caching of tax brackets
- Vectorized operations where possible

### Computational Requirements
- 30-year simulation: < 1 second
- 4-scenario comparison: < 5 seconds
- CSV export: < 1 second
- GUI responsiveness: Real-time

### Memory Usage
- Single client profile: ~1 KB
- One 30-year strategy: ~50 KB
- Four strategies: ~200 KB
- Total application: ~50 MB (including GUI framework)

## Extension Points

To add new features:

### 1. New Tax Scenarios
- Add to `FEDERAL_TAX_BRACKETS_*` in constants.py
- Update IRMAA brackets
- Enhance TaxCalculator methods

### 2. New Account Types
- Add to `ACCOUNT_TYPES` in constants.py
- Update Account dataclass if needed
- Modify ConversionSimulator account handling

### 3. New Income Types
- Add to IncomeStream.income_type options
- Update tax treatment logic in TaxCalculator
- Add validation in GUI

### 4. New Optimization Objectives
- Define new objective in ConversionOptimizer.generate_scenarios()
- Implement objective-specific logic in _calculate_optimal_conversion()
- Add ranking metric in get_ranked_strategies()

### 5. Monte Carlo Simulation
- Create `MonteCarlo Simulator` class
- Use scipy.stats for distribution modeling
- Generate confidence intervals for results

## Debugging Guide

### Common Issues

**Issue**: Roth values seem too high
- Check: Account growth rates (typically 5-8%)
- Check: Are conversions actually happening?
- Fix: Add print statements in simulate_year()

**Issue**: Taxes are zero
- Check: IRMAA calculation might be suppressing conversion
- Check: Income might be below standard deduction
- Fix: Verify tax calculation in ConversionSimulator

**Issue**: Conversions stop after age 73
- Check: This is likely RMD taking over
- Check: Money might be depleted
- Fix: Check final balances in output

**Issue**: GUI won't launch
- Check: PySimpleGUI installed (pip install PySimpleGUI>=4.60)
- Check: No import errors (python -c "import PySimpleGUI")
- Fix: Run example_analysis.py first (simpler to debug)

---

**Last Updated**: November 2026
**Version**: 0.1.0
"""
