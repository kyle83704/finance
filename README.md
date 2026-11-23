# Roth Conversion Simulator

A friendly desktop planner for comparing Roth conversion strategies through
retirement. The app walks through a five-step wizard, projects federal/state
taxes, IRMAA, RMDs and cash flow year by year, and compares six objective-driven
policies side by side.

Current release: **2.3.0 (Ledger edition)**

![Penny, the planning pig](docs/penny.png)

## What's new in 2.3

- **Cash-flow ledger** — income, RMDs, conversions, spending, tax payments,
  contributions and growth are posted as signed entries. Each year reconciles
  beginning assets to ending assets.
- **Explicit tax funding** — taxes can be paid from cash, Roth withholding,
  taxable-account sales or a capped amount of external money. Liability, tax
  actually paid and unpaid tax are separate fields.
- **Spending that affects balances** — living expenses are paid from cash first,
  then taxable assets. An unfunded shortfall is reported instead of being
  ignored.
- **Taxable cost basis and realized gains** — taxable sales realize gains and
  the incremental gain tax is included in the year's liability.
- **Honest after-tax math** — after-tax net worth subtracts unpaid tax and a
  deferred-tax reserve on remaining pre-tax balances, not cumulative taxes that
  were already paid from assets.
- **Rule and assumption registry** — 2026 federal, LTCG, Social Security, RMD
  and IRMAA records carry sources, dates, status and limitations. The HTML
  report includes the registry.
- **107 automated tests** covering cash-flow reconciliation, funding sources,
  basis, gains, deferred tax, the projection map, rules, taxes, reports and
  persistence.

## Features

### Planning workflow

- Five-step wizard: client → accounts → income → expenses → scenarios.
- Traditional IRA, Roth IRA, SEP IRA, Solo 401(k), Employer 401(k), 401(k),
  403(b), Roth 401(k), HSA, taxable brokerage and pension account types.
- Multiple income streams with start/end ages, COLA and tax treatment.
- Live expense totals.
- Tax-funding selection and deferred-tax assumption in the scenario step.
- JSON project save/load.
- 3D projection map from the results window, with conversion and added-funds
  controls and Pareto sweet spots.
- CSV, HTML and Excel exports from the results window.

### Modeling

- Actual 2026 federal brackets and standard deductions, including the 65+
  add-on and 2.5% annual indexing after 2026.
- Social Security provisional-income taxation (up to 85% of benefits taxable).
- Qualified dividends and long-term gains at 0/15/20% federal rates.
- Simplified flat state tax rates for all states plus DC.
- RMDs at 73 for birth years 1951–1959 and 75 for 1960 or later.
- Pro-rata treatment of non-deductible IRA basis.
- Six 2026 IRMAA tiers covering Part B and Part D, with a two-year MAGI replay.
- Taxable-account cost basis, realized gains and incremental gain tax.
- Gross account values plus an after-tax measure that subtracts unpaid tax and
  an explicit deferred-tax reserve.

### Objective policies

| Objective | Conversion policy | IRMAA |
|---|---|---|
| Maximize Roth Value | Convert through the 32% federal bracket | Accept surcharges |
| Maximize Inheritance | Convert through the 24% bracket | Accept surcharges |
| Maximize Gross Net Worth | Convert through the 22% bracket | Accept surcharges |
| Balanced Growth | Convert through the 22% bracket | Stay below first tier |
| Minimize Tax Paid | No voluntary conversions; RMDs only | N/A |
| Minimize IRMAA Impact | Stay in the current bracket | Stay below first tier |

`Maximize Roth Value` and the other bracket-based policies fill the selected
bracket, not just the current one. A policy with no explicit ceiling fills only
the bracket the client is already in. The IRMAA cap starts at age 63 because the
premium is based on MAGI from two years earlier; the premium itself is charged
from age 65.

### 3D projection map

Open **3D Map** from the results window to compare a grid of fixed annual Roth
conversions. The map plots projection year, annual conversion and after-tax net
worth; color shows cumulative tax load including IRMAA. **Sweet Spots** marks
paths that are not beaten on both after-tax value and tax cost, with **Best net**
and **Lowest tax** called out in the table. Enter extra annual funds to model
taxable contributions to the first taxable account (a synthetic taxable account
is used when none exists); the contribution adds to cost basis.

After-tax value subtracts unpaid tax and the deferred-tax reserve on remaining
pre-tax assets. Advisory and trading fees are not modeled; enter them as living
expenses if needed. Added funds are taxable contributions, not a deduction.

## Install

```bash
python -m pip install -r requirements.txt
```

Python 3.9+ is supported; this build was tested on Python 3.13.

## Run

```bash
python main.py
```

Run the standalone example without a GUI:

```bash
python example_analysis.py
```

Run the test suite:

```bash
python -m unittest discover tests -v
```

Build the Windows executable (PyInstaller is a development dependency):

```bash
python -m PyInstaller --noconfirm --clean main.spec
```

The packaged app is written to `dist/main.exe`.

## Tax funding and cash flow

The scenario step asks how taxes should be funded:

1. **Cash** — cash left after spending, then Roth withholding if needed.
2. **Withhold from conversion** — reduce the Roth conversion first, then cash.
3. **Sell taxable assets** — sell taxable holdings, realizing gains, then cash.
4. **External funds** — use only the explicitly entered annual amount, then
   fall back to cash or Roth withholding.

Tax liability is the amount owed for the year. Tax paid is the amount actually
funded. Unpaid tax stays visible in the results and reduces after-tax net worth.
External money is never assumed to be unlimited, and the simulator does not
create a hidden bank account.

Living expenses are separate from taxes. They are paid from cash, then taxable
assets; if those are exhausted, the year records a spending shortfall. Voluntary
pre-tax withdrawals for spending are not automatic.

## Project structure

```text
finance/
├── main.py                     # Desktop entry point
├── src/
│   ├── constants.py            # Tax tables, IRMAA, RMD table, account groups
│   ├── rules.py                # Versioned rule and assumption registry
│   ├── models.py               # Dataclasses, ledger entries and JSON persistence
│   ├── tax_calculator.py       # Federal/state tax, IRMAA, RMD, pro-rata, gains
│   ├── simulator.py            # Year-by-year projection, funding and reconciliation
│   ├── projection_map.py       # Conversion-grid sensitivity surface and sweet spots
│   ├── optimizer.py            # Objective policies and strategy comparison
│   ├── gui.py                  # PySimpleGUI wizard, results and exports
│   ├── theme.py                # Warm palette shared by UI, mascot and reports
│   ├── mascot.py               # Penny rendered to PNG/data URI
│   ├── reports.py              # Self-contained HTML report and rule registry
│   └── excel_report.py         # Formatted Excel workbook with chart
├── tests/                      # 107 automated tests
├── docs/TECHNICAL.md           # Algorithms, invariants and limits
├── main.spec                   # PyInstaller build configuration
├── requirements.txt
├── QUICKSTART.md
└── BUILD_LOGS.md
```

`src/gui_v2.py` and `app.py` are legacy prototypes kept for reference. They are
not launched by `main.py`; the Flask prototype is unsupported and Flask is not a
project dependency.

## Reports

From the results window:

- **HTML Report** writes one self-contained `.html` file with embedded CSS,
  chart, mascot, tables and the rule registry. It prints cleanly to PDF.
- **Excel Report** writes a formatted `.xlsx` with summary, comparison,
  year-by-year sheets and the chart image.
- **Export to CSV** writes one raw year-by-year CSV per strategy.

Reports are generated locally; no data leaves the computer.

## Modeling limits

This is an educational planner, not tax, legal or investment advice.

- Uses 2026 verified federal parameters with a 2.5% planning assumption for
  later-year inflation; actual IRS indexing will differ.
- State tax is a simplified flat rate; state deductions, credits, retirement
  exclusions and residency/sourcing rules are not modeled.
- IRMAA replays the two-year MAGI when the projection includes the lookback
  years. If the projection starts at 65 or later, it falls back to current MAGI.
- The temporary OBBBA senior deduction, MFS/HOH federal brackets, QCDs, AMT,
  NIIT, estate tax and payroll/claiming optimization are not modeled.
- Taxable-account sales use supplied cost basis, but short-term gains, wash
  sales, loss carryforwards and state conformity are not modeled.
- Spending is funded from cash and taxable assets only; an unfunded shortfall
  is reported.
- The deferred-tax rate is a planning assumption, not a prediction of future law.
- The 3D projection map does not model advisory or trading fees; added funds are
  taxable contributions and no deduction is assumed.
- No Monte Carlo, market volatility or tax-law change simulation.

Always confirm conversion decisions with a qualified tax professional.
