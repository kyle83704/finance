# Technical Documentation

## Architecture

```text
PySimpleGUI wizard / results (src/gui.py)
        │
        ├── theme.py + mascot.py + reports.py + excel_report.py
        │
ConversionOptimizer (src/optimizer.py)
  - OBJECTIVE_POLICIES
  - generate_scenarios()
  - run_scenario_comparison()
  - compare_strategies() / ranking / CSV
        │
ConversionSimulator (src/simulator.py)
  - deep-copies accounts per scenario
  - calculates RMDs and withdrawals
  - chooses and executes conversions
  - tracks incremental tax + IRMAA
  - projects account growth
        │
TaxCalculator (src/tax_calculator.py)
  - progressive federal tax
  - simplified flat state tax
  - IRMAA tiers
  - RMD divisors
  - pro-rata conversion tax
        │
models.py / constants.py
  - dataclasses, JSON persistence
  - brackets, deductions, account groups, RMD table
```

## Data flow

1. The wizard creates `ClientProfile`, accounts, income streams and `Expenses`.
2. `ConversionOptimizer.generate_scenarios()` applies `OBJECTIVE_POLICIES` to
   the selected objectives.
3. `ConversionSimulator.run_full_simulation()` runs each scenario.
4. Results are displayed, exported or saved as a JSON project.

## Correctness invariants

These are the rules regression tests protect.

### 1. Scenario isolation

`run_full_simulation()` deep-copies the caller's accounts before simulating.
Running a scenario never mutates the input list, and a later scenario starts
from the original balances rather than the previous scenario's ending state.
`run_scenario_comparison()` also calls the simulator independently for each
scenario, so scenario order does not change results.

### 2. RMDs are not conversions

At age 73+ the simulator calculates each pre-tax account's RMD using the IRS
Uniform Lifetime divisor, withdraws the total pro rata, and records it as
`rmd_required`. That amount is **not** added to `recommended_conversion`.
RMD proceeds move into the taxable bucket to preserve gross net worth. The RMD
is included in ordinary income for tax and IRMAA calculations.

A voluntary conversion can only use the pre-tax balance remaining after the
RMD. If a fixed target exceeds that capacity, it is capped.

### 3. Pre-conversion basis snapshot

Pro-rata taxable amount and conversion tax use balances captured **before** the
conversion withdrawal:

```text
pre-tax portion = max(0, account balance - after-tax basis)
total IRA value = pre-tax portion + after-tax basis
taxable conversion = conversion × (pre-tax portion / total IRA value)
```

Using post-conversion balances makes the ratio zero when a conversion empties
the account—a bug fixed in this release and covered by regression tests.

### 4. Incremental conversion tax

Conversion tax is the difference between total tax with the conversion and
total tax without it:

```text
baseline tax = federal(taxable income without conversion)
              + state(taxable income without conversion)
conversion tax = total tax with conversion - baseline tax
```

This handles standard-deduction sheltering and bracket crossings correctly.
The old top-marginal-rate shortcut is gone.

### 5. Total lifetime tax

Per year:

```text
total_tax_paid = income_tax + conversion_tax + irmaa_impact
```

`income_tax` covers ordinary income streams and RMDs. `ConversionStrategy`
accumulates:

- `total_conversion_taxes` — incremental conversion tax only
- `total_income_taxes` — income tax + conversion tax
- `total_irmaa_costs`
- `total_taxes_paid` — all of the above, including IRMAA

`final_after_tax_net_worth = final_net_worth - total_taxes_paid`. Taxes are
modeled as paid outside tracked accounts so this subtraction is not double
counted.

### 6. Account groups

The simulator uses shared groups from `constants.py`:

- `PRETAX_ACCOUNT_TYPES`: Traditional IRA, SEP IRA, Solo 401(k), Employer
  401(k), 401(k), 403(b)
- `ROTH_ACCOUNT_TYPES`: Roth IRA, Roth 401(k)
- `TAXABLE_ACCOUNT_TYPES`: Taxable Brokerage

This prevents the old mismatch where the GUI offered “Employer 401(k)” but the
simulator only recognized “401(k)”.

### 7. IRMAA timing

The IRMAA policy cap begins at age 63 because the premium uses MAGI from two
years earlier. The annual surcharge is charged at age 65+. For MFJ, the
surcharge is doubled only when the spouse is also 65+ (or no spouse age is
provided). Current-year MAGI is used in the projection; the full two-year
premium replay is not modeled.

## Objective policies

| Objective | Fill bracket | Ceiling | IRMAA cap | Fixed target |
|---|---|---|---|---|
| Maximize Roth Value | yes | 32% | no | none |
| Maximize Inheritance | yes | 24% | no | none |
| Maximize Gross Net Worth | yes | 22% | no | none |
| Balanced Growth | yes | 22% | yes | none |
| Minimize Tax Paid | no | — | yes | $0 |
| Minimize IRMAA Impact | yes | current bracket | yes | none |

A ceiling extends the conversion through lower brackets up to the top of the
highest bracket at or below the ceiling. With no ceiling, only the current
bracket is filled. A fixed target can be constrained by IRMAA and available
pre-tax balance.

## Tax model

### Federal

Progressive 2026 brackets for `single` and `married_filing_jointly`. Taxable
income is gross ordinary income minus the standard deduction. RMDs and
conversions are ordinary income.

### State

A flat rate per state from `STATE_TAX_RATES`. State tax is applied to the same
federal taxable-income base. State deductions, credits and retirement-income
exclusions are not modeled.

### IRMAA

Monthly adjustment from `IRMAA_BRACKETS_2026`, multiplied by 12 and by the
number of Medicare enrollees. IRMAA is a Medicare surcharge; it is not an income
tax.

### RMD

```text
RMD = account balance / IRS Uniform Lifetime divisor(age)
```

Starting age is 73. Roth accounts are excluded.

## Growth and cash flow

- RMD withdrawals and conversions happen before annual growth.
- Remaining balances grow at each account's `growth_rate`.
- Annual contributions are added before growth.
- RMD proceeds are placed in the first taxable account, or a synthetic
  “Taxable RMD Proceeds” account at 4% if none exists.
- A conversion with no Roth account creates a synthetic “Roth Conversion
  Account” at 7%.
- Income and expenses are not used to settle a cash-flow ledger. If income plus
  RMD is below expenses, the year's notes record the shortfall.

## Reports

### HTML

`src/reports.py` builds a self-contained HTML document with embedded CSS,
base64 chart, base64 mascot and escaped user text. It is print-ready; the
browser's Print → Save as PDF produces a PDF.

### Excel

`src/excel_report.py` uses openpyxl and Pillow to build:

- Summary with at-a-glance metrics and method notes
- Comparison table
- One year-by-year sheet per strategy
- Chart sheet with the PNG embedded

Sheet names are sanitized and de-duplicated to Excel's 31-character limit.

## Persistence

`save_project()` writes versioned JSON containing the client, accounts, income
streams and expenses. `load_project()` recomputes ages and returns `None` for
missing, corrupt or invalid files.

## Tests

`python -m unittest discover tests -v` runs **80 tests** covering:

- federal/state tax, deductions, IRMAA, RMDs, pro-rata
- incremental conversion tax
- scenario isolation and order independence
- RMD withdrawal, conversion capacity and Employer 401(k) handling
- objective policy uniqueness
- ranking and after-tax comparison
- project persistence
- HTML/Excel reports, mascot and GUI helpers

Additional verification:

- strict headless layout smoke for the menu, all five wizard steps, results,
  strategy picker and detail window
- `python example_analysis.py`
- PyInstaller build and frozen launch with the expected window title

## Extension points

- Add tax years by extending the constants tables and passing `year` through.
- Add an objective in `OBJECTIVE_POLICIES`; add a policy test.
- Add a report format alongside `reports.py` / `excel_report.py`.
- Add a tax rule in `TaxCalculator` and cover it with focused unit tests.
- Add cash-flow modeling before changing how expenses affect balances.

## Known limitations

- 2026 federal parameters only; no inflation indexing.
- Flat state tax approximation.
- IRMAA projection uses current-year MAGI.
- No capital-gains, NIIT, AMT, QCD or estate modeling.
- No Monte Carlo or market volatility.
- No spousal RMD/IRMAA synchronization beyond the 65+ count.
- Expenses are not deducted from portfolios.
- Taxes are tracked separately from balances.

This is an educational planner, not tax, legal or investment advice.
