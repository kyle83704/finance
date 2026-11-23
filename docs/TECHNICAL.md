# Technical Documentation

## Architecture

```text
PySimpleGUI wizard / results / 3D map (src/gui.py)
        │
        ├── projection_map.py (fixed-conversion grid, sweet spots, PNG surface)
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
  - receives income and calculates RMDs
  - executes conversions and taxable sales
  - settles spending and taxes
  - posts ledger entries and reconciles assets
  - projects account growth
        │
TaxCalculator (src/tax_calculator.py)
  - 2026 federal brackets + age-65 add-on
  - Social Security provisional-income taxability
  - qualified dividend / LTCG 0/15/20% rates
  - incremental capital-gains tax
  - simplified flat state tax
  - indexed future-year thresholds
  - six IRMAA tiers (Part B + D)
  - SECURE 2.0 RMD ages and IRS divisors
  - pro-rata conversion tax
        │
models.py / constants.py / rules.py
  - dataclasses, ledger entries, JSON persistence
  - brackets, deductions, account groups, RMD table
  - source/status registry for rules and assumptions
```

## Data flow

1. The wizard creates `ClientProfile`, accounts, income streams, `Expenses` and
   tax-funding settings.
2. `ConversionOptimizer.generate_scenarios()` applies `OBJECTIVE_POLICIES` and
   carries the funding/deferred-tax settings into every scenario.
3. `ConversionSimulator.run_full_simulation()` runs each scenario against a
   deep copy of the accounts.
4. Results are displayed, exported or saved as a JSON project.

## Correctness invariants

These are the rules regression tests protect.

### 1. Scenario isolation

`run_full_simulation()` deep-copies the caller's accounts before simulating.
Running a scenario never mutates the input list, and a later scenario starts
from the original balances rather than the previous scenario's ending state.
`run_scenario_comparison()` calls the simulator independently for each scenario.

### 2. RMDs are not conversions

At the client's SECURE 2.0 RMD age (73 for birth years 1951–1959, 75 for
1960+), the simulator calculates each pre-tax account's RMD using the IRS
Uniform Lifetime divisor, withdraws the total pro rata, and records it as
`rmd_required`. It is **not** added to `recommended_conversion`. The proceeds
are received as cash and taxed as ordinary income. A voluntary conversion can
only use the pre-tax balance remaining after the RMD.

### 3. Pre-conversion basis snapshot

Pro-rata taxable amount and conversion tax use balances captured **before** the
conversion withdrawal:

```text
pre-tax portion = max(0, account balance - after-tax basis)
total IRA value = pre-tax portion + after-tax basis
taxable conversion = conversion × (pre-tax portion / total IRA value)
```

Using post-conversion balances makes the ratio zero when a conversion empties
the account; the snapshot prevents that bug.

### 4. Incremental conversion tax

Conversion tax is the difference between total tax with the conversion and
total tax without it:

```text
baseline tax = federal(taxable income without conversion)
              + state(taxable income without conversion)
conversion tax = total tax with conversion - baseline tax
```

This handles standard-deduction sheltering and bracket crossings. It is not the
top marginal rate multiplied by the conversion.

### 5. Tax liability is not tax paid

Per year:

```text
tax_liability = income_tax + conversion_tax + irmaa_impact + gain_tax
taxes_paid    = amount actually funded
taxes_unpaid  = max(0, tax_liability - taxes_paid)
```

`ConversionResult.total_tax_paid` is retained as the annual **liability** field
for compatibility. The actual payment fields are `taxes_paid`,
`taxes_paid_from_assets`, `taxes_paid_external`, `withholding_from_conversion`
and `taxes_unpaid`.

At the strategy level:

- `total_conversion_taxes` — incremental conversion tax liability
- `total_income_taxes` — income tax + conversion tax
- `total_irmaa_costs` — Medicare surcharge liability
- `total_taxes_paid` — actual payments made
- `total_tax_liability` — annual liabilities, paid or unpaid
- `total_taxes_unpaid` — unpaid liabilities

### 6. Cash-flow ledger and reconciliation

Every tracked asset movement is a signed `LedgerEntry`:

- income received
- RMD withdrawal and cash receipt (offsetting)
- Roth conversion out of pre-tax and into Roth (offsetting)
- spending paid from cash or taxable assets
- tax paid from cash, Roth, taxable assets or external money
- explicit external funding (offsetting with the tax payment)
- residual cash sweep into a taxable account (offsetting)
- contributions and investment growth

For each year:

```text
ending_assets - beginning_assets = sum(ledger amounts)
```

`reconciliation_difference` records any residual. Tests assert it is effectively
zero, so an unexplained balance change cannot hide in a note.

### 7. Funding hierarchy

The scenario's `tax_payment_source` determines the order:

| Source | Order |
|---|---|
| `cash` | cash → Roth withholding → external → unpaid |
| `withhold` | Roth withholding → cash → external → unpaid |
| `taxable` | taxable sales → cash → Roth withholding → external → unpaid |
| `external` | explicit external funds → cash → Roth withholding → unpaid |

External funding is capped at `external_tax_funding`. The simulator never
assumes unlimited outside cash. A taxable sale used for taxes realizes gains;
the additional incremental gain tax is added to the liability (one extra
iteration, disclosed in the year's notes).

Living expenses are paid from cash first, then taxable assets. If neither is
sufficient, `spending_shortfall` is recorded. Pre-tax withdrawals for spending
are not automatic.

### 8. Deferred tax and after-tax net worth

```text
final_deferred_tax_liability =
    remaining pre-tax balance × scenario.deferred_tax_rate

final_after_tax_net_worth =
    final_net_worth - total_taxes_unpaid - final_deferred_tax_liability
```

Taxes paid during the projection already reduced account balances, so they are
not subtracted again. The deferred rate defaults to 22% and is an explicit
planning assumption, not a claim about future law.

### 9. Account groups

The simulator uses shared groups from `constants.py`:

- `PRETAX_ACCOUNT_TYPES`: Traditional IRA, SEP IRA, Solo 401(k), Employer
  401(k), 401(k), 403(b)
- `ROTH_ACCOUNT_TYPES`: Roth IRA, Roth 401(k)
- `TAXABLE_ACCOUNT_TYPES`: Taxable Brokerage

A synthetic Roth account created by a conversion inherits the
balance-weighted growth rate of the pre-tax accounts, rather than a hard-coded
default.

### 10. IRMAA timing

The IRMAA policy cap begins at age 63 because the premium uses MAGI from two
years earlier. The annual surcharge is charged at age 65+. For MFJ, the
surcharge is doubled only when the spouse is also 65+ (or no spouse age is
provided). `run_full_simulation()` keeps a MAGI history and passes the value
from year−2 into each premium year. If the projection begins at 65 or later,
current-year MAGI is the documented fallback.

The 2026 table combines Part B and Part D per person, with six tiers. The top
tier starts at $500k single / $750k MFJ; a MAGI exactly at that threshold is in
the top tier.

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

Actual 2026 brackets from IRS Rev. Proc. 2025-32 for `single` and
`married_filing_jointly`. Taxable income is gross income minus the standard
deduction. The standard deduction is $16,100 single / $32,200 MFJ, plus $2,050
single or $1,650 per eligible spouse at 65+. Brackets, deductions, LTCG
thresholds and IRMAA thresholds are indexed at 2.5% after 2026 as a planning
assumption.

Social Security uses the provisional-income formula and the statutory
$25k/$34k (single/HOH) or $32k/$44k (MFJ) thresholds, which are not indexed.
Up to 85% of benefits can be taxable. Qualified dividends/LTCG use the 2026
0/15/20% breakpoints. RMDs and conversions are ordinary income.

### State

A flat rate per state from `STATE_TAX_RATES`, applied to the same federal
taxable-income base. State deductions, credits, retirement-income exclusions,
local taxes and residency/sourcing rules are not modeled. This is an
assumption, not a state return.

### IRMAA

Monthly adjustment from `IRMAA_BRACKETS_2026`, multiplied by 12 and by the
number of Medicare enrollees. IRMAA is a Medicare surcharge, not an income tax.

### Capital gains

Taxable-account sales use `cost_basis`. Gains are treated as long-term and
stacked on ordinary/qualified income; `calculate_capital_gains_tax()` returns
the incremental federal + state tax. Short-term gains, wash sales, loss
carryforwards, NIIT and state conformity are not modeled.

### RMD

```text
RMD = account balance / IRS Uniform Lifetime divisor(age)
```

Starting age is 73 for birth years 1951–1959 and 75 for 1960 or later. Roth
accounts are excluded.

## Rules and assumptions registry

`src/rules.py` records the identity, scope, effective dates, official source,
retrieval date, reference, status and limitations of each implemented rule.
Statuses are:

- `verified` — checked for the stated year against the cited official source.
- `assumption` — a planning choice, such as 2.5% future indexing or the flat
  state rate.
- `unsupported` — known law/model area not implemented, such as the OBBBA
  senior deduction or MFS/HOH brackets.

The HTML report renders the registry. Numeric tables remain in `constants.py`;
the registry is the provenance layer, not a second set of numbers.

## Growth and cash flow

- Income and RMD cash are received before spending and tax settlement.
- Spending is paid before taxes.
- Remaining cash is swept into the first taxable account, or a synthetic
  “Cash Reserve” account at 0% growth.
- Annual contributions are added before growth.
- Remaining balances grow at each account's `growth_rate`.
- A conversion with no Roth account creates a synthetic “Roth Conversion
  Account” using the weighted pre-tax growth rate.

## 3D projection map

`src/projection_map.py` is a sensitivity layer over the normal optimizer and
simulator. Each requested annual conversion target is run as its own scenario
with a fixed conversion, optional taxable added funds, and the base scenario's
tax-funding and deferred-tax assumptions. A target above the available pre-tax
balance is capped by the normal conversion policy; the map does not invent
assets or tax payments.

The surface coordinates are projection year, annual conversion and after-tax
net worth. Color is cumulative tax liability including IRMAA. After-tax value
for each year is:

```text
gross ending assets
  - cumulative unpaid tax
  - remaining pre-tax balance × deferred_tax_rate
```

Taxes already paid are already reflected in ending balances. Sweet spots are
non-dominated points: no other grid point has both at least as much after-tax
value and no more tax cost. Added funds go to the first taxable account, or a
synthetic taxable account when none exists; they add to cost basis. Advisory
and trading fees are not modeled.

## Reports

### HTML

`src/reports.py` builds a self-contained HTML document with embedded CSS,
base64 chart, base64 mascot, escaped user text, comparison, annual detail and
the rule/assumption registry.

### Excel

`src/excel_report.py` uses openpyxl and Pillow to build:

- Summary with at-a-glance metrics and method notes
- Comparison table with liability, paid, unpaid, deferred reserve and after-tax
  net worth
- One year-by-year sheet per strategy with spending, funding and reconciliation
  columns
- Chart sheet with the PNG embedded

Sheet names are sanitized and de-duplicated to Excel's 31-character limit.

## Persistence

`save_project()` writes versioned JSON containing the client, accounts, income
streams and expenses. `load_project()` recomputes ages and returns `None` for
missing, corrupt or invalid files. Unknown account fields are not invented;
dataclass defaults cover older files.

## Tests

`python -m unittest discover tests -v` runs **107 tests** covering:

- 2026 federal/state tax, age-65 deductions, IRMAA boundaries, RMDs, pro-rata
- Social Security provisional-income taxability
- qualified-dividend rates and future-year indexing
- incremental conversion and capital-gains tax
- scenario isolation and order independence
- SECURE 2.0 RMD ages, conversion capacity and Employer 401(k) handling
- two-year IRMAA lookback replay
- spending, tax funding, withholding, external caps and unpaid tax
- taxable cost basis and realized gains
- ledger reconciliation and deferred-tax after-tax net worth
- projection-map grid, Pareto sweet spots, taxable added funds and PNG rendering
- rule registry status/coverage
- objective policy uniqueness
- ranking and after-tax comparison
- project persistence
- HTML/Excel reports, mascot and GUI helpers

Additional verification:

- local visual capture of the menu, five wizard panels, results, 3D surface,
  sweet-spot table and detail window (`python build/capture_ui.py`)
- `python example_analysis.py`
- PyInstaller build and frozen launch with the expected window title

## Extension points

- Add tax years by extending the constants tables and registry records.
- Add an objective in `OBJECTIVE_POLICIES` and a policy test.
- Add a report format alongside `reports.py` / `excel_report.py`.
- Add a tax rule in `TaxCalculator` and cover it with a focused unit test and a
  registry entry.
- Add a funding source in `simulate_year` and test its hierarchy explicitly.

## Known limitations

- 2026 federal parameters indexed at a 2.5% planning assumption; actual IRS
  inflation adjustments will differ.
- Flat state tax approximation.
- MFS/HOH federal brackets and OBBBA senior deduction are unsupported.
- IRMAA uses current-year MAGI only when the two-year lookback history is not
  available.
- Short-term gains, wash sales, loss carryforwards, NIIT, AMT, QCD and estate
  modeling are absent.
- The 3D map is a fixed-conversion sensitivity view; advisory/trading fees are
  not modeled and added funds are taxable contributions.
- No Monte Carlo or market volatility.
- No spousal RMD/IRMAA synchronization beyond the 65+ count.
- Spending cannot be funded automatically from pre-tax accounts.
- The extra gain tax created by selling taxable assets to pay tax is computed
  in one additional iteration and disclosed rather than solved to a fixed point.

This is an educational planner, not tax, legal or investment advice.
