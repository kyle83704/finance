# Roth Conversion Simulator

A friendly desktop planner for comparing Roth conversion strategies through
retirement. The app walks through a five-step wizard, projects federal/state
taxes, IRMAA and RMDs year by year, and compares six objective-driven policies
side by side.

Current release: **2.1.0 (Penny edition)**

![Penny, the planning pig](docs/penny.png)

## What's new

- **Warm Penny theme** — cream background, teal/coral/gold accents and a
  hand-drawn piggy-bank mascot rendered with matplotlib (no image asset files).
- **HTML report** — a self-contained, print-ready report with the comparison,
  chart, Penny portrait and year-by-year tables. Use the browser's Print dialog
  to save a PDF.
- **Excel report** — a formatted `.xlsx` with a summary, comparison, one
  year-by-year sheet per strategy and an embedded chart.
- **Correct scenario isolation** — every strategy runs against a deep copy of
  the accounts, so results never depend on scenario order.
- **Correct RMD handling** — RMDs are withdrawn before voluntary conversions,
  taxed as ordinary income and moved into the taxable bucket instead of being
  counted as conversions.
- **Incremental conversion tax** — conversion tax compares total tax with and
  without the conversion; it is not the whole conversion multiplied by the top
  marginal rate.
- **Distinct objective policies** — the six objectives now have explicit tax
  brackets and IRMAA behavior, and the GUI uses those policies.
- **80 automated tests**, a strict headless layout smoke, and a rebuilt Windows
  executable.

## Features

### Planning workflow

- Five-step wizard: client → accounts → income → expenses → scenarios.
- Traditional IRA, Roth IRA, SEP IRA, Solo 401(k), Employer 401(k), 401(k),
  403(b), Roth 401(k), HSA, taxable brokerage and pension account types.
- Multiple income streams with start/end ages, COLA and tax treatment.
- Live expense totals.
- JSON project save/load.
- CSV, HTML and Excel exports from the results window.

### Modeling

- Progressive 2026 federal brackets and standard deductions (single and MFJ).
- Simplified flat state tax rates for all states plus DC.
- RMDs from age 73 using the IRS Uniform Lifetime Table.
- Pro-rata treatment of non-deductible IRA basis.
- IRMAA tiers with the two-year lookback reflected in the policy cap.
- Gross account values plus an after-tax net-worth comparison that subtracts
  lifetime income tax, conversion tax and IRMAA.

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

## Project structure

```text
finance/
├── main.py                     # Desktop entry point
├── src/
│   ├── constants.py            # Tax brackets, IRMAA, RMD table, account groups
│   ├── models.py               # Dataclasses and JSON persistence
│   ├── tax_calculator.py       # Federal/state tax, IRMAA, RMD, pro-rata
│   ├── simulator.py            # Year-by-year projection and conversion policy
│   ├── optimizer.py            # Objective policies and strategy comparison
│   ├── gui.py                  # PySimpleGUI wizard, results and exports
│   ├── theme.py                # Warm palette shared by UI, mascot and reports
│   ├── mascot.py               # Penny rendered to PNG/data URI
│   ├── reports.py              # Self-contained HTML report
│   └── excel_report.py         # Formatted Excel workbook with chart
├── tests/                      # 80 automated tests
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
  chart, mascot and tables. It opens in any browser and prints cleanly to PDF.
- **Excel Report** writes a formatted `.xlsx` with summary, comparison,
  year-by-year sheets and the chart image.
- **Export to CSV** writes one raw year-by-year CSV per strategy.

Reports are generated locally; no data leaves the computer.

## Modeling limits

This is an educational planner, not tax advice.

- Uses 2026 federal brackets and standard deductions throughout the projection.
- State tax is a simplified flat rate; state deductions, credits and retirement
  exclusions are not modeled.
- IRMAA uses current-year MAGI in the simulation rather than replaying the
  actual two-year lookback for each premium year.
- Expenses are planning context; portfolio withdrawals used for spending are
  not deducted from account balances.
- Taxable-account capital gains, QCDs, AMT, NIIT, estate tax, Monte Carlo
  volatility and state-specific retirement rules are not modeled.
- Taxes are modeled as paid from outside the tracked accounts; the after-tax
  metric subtracts them once.
- A conversion with no existing Roth account creates a Roth account with a 7%
  default growth assumption.

Always confirm conversion decisions with a qualified tax professional.

## License

MIT License. See the project license file when present.
