# Roth Conversion Simulator — Quick Start

## 1. Install

```bash
cd finance
python -m pip install -r requirements.txt
```

Python 3.9+ is supported; this build was tested with Python 3.13.

## 2. Try the example first

```bash
python example_analysis.py
```

The script builds a sample retired couple, compares four objectives, prints the
comparison and rankings, and writes `example_strategy_detail.csv`.

## 3. Run the desktop app

```bash
python main.py
```

The wizard asks for:

1. **Client** — names, birth year, spouse, state and filing status.
2. **Accounts** — balance, type, basis, growth rate and annual contribution.
3. **Income** — Social Security, pension, work or dividends, with ages and COLA.
4. **Expenses** — annual spending by category; totals update as you type.
5. **Scenarios** — objectives and projection window.

Click **Run Analysis**. The results window shows:

- **Comparison** — conversions, total taxes, IRMAA, final Roth/pre-tax/taxable
  values, final net worth and net after all taxes.
- **Chart** — final net worth by strategy, with Penny's pick in gold.
- **Detail View** — year-by-year RMD, conversion, tax and balance columns.
- **HTML Report**, **Excel Report**, **Export to CSV**, **Save Project**.

## 4. Run the tests

```bash
python -m unittest discover tests -v
```

Expected result: **80 tests, 0 failures**.

The suite covers tax brackets, incremental conversion tax, RMD withdrawal,
pro-rata basis, scenario isolation, objective policies, persistence, the HTML
and Excel reports, the mascot and the GUI helpers.

## 5. Build the executable

```bash
python -m PyInstaller --noconfirm --clean main.spec
```

The Windows app is written to `dist/main.exe`. The build is self-contained and
does not need Python installed on the target machine.

## Choosing an objective

- **Maximize Roth Value** — most aggressive; converts through the 32% bracket.
- **Maximize Inheritance** — converts through the 24% bracket.
- **Maximize Gross Net Worth** — converts through the 22% bracket.
- **Balanced Growth** — 22% bracket while staying below the first IRMAA tier.
- **Minimize Tax Paid** — no voluntary conversions; RMDs only.
- **Minimize IRMAA Impact** — stays in the current bracket and below IRMAA.

Policies intentionally differ. See `README.md` and `docs/TECHNICAL.md` for the
full table and assumptions.

## What the numbers mean

- **Total Taxes Paid** includes income tax on income and RMDs, incremental tax
  on conversions, and IRMAA.
- **Net After All Taxes** subtracts that lifetime tax total from gross final net
  worth once.
- **RMD Required** is a mandatory withdrawal, never a voluntary conversion.
- **Conversion** is the additional amount moved to Roth after the RMD.

## Reports

- **HTML Report** is a single self-contained file. Open it in a browser and use
  Print → Save as PDF for a PDF copy.
- **Excel Report** contains summary, comparison, yearly detail and the chart.
- **CSV** is raw year-by-year data for further analysis.

## Troubleshooting

**`ModuleNotFoundError: PySimpleGUI`**

```bash
python -m pip install -r requirements.txt
```

PySimpleGUI is intentionally pinned below 5.0; version 5.x requires a paid
runtime license.

**GUI does not open**

Run the example first to check the Python environment:

```bash
python example_analysis.py
```

Then run `python main.py` from the project root so `src/` is importable.

**A test fails**

Run the failing test alone with `-v` and check that you are using the project's
virtual environment. Do not weaken assertions to make a failure disappear.

## Important limits

The simulator is an educational estimate. It uses simplified flat state taxes,
2026 federal parameters, current-year IRMAA MAGI, and does not deduct living
expenses from modeled accounts. It is not a substitute for a CPA or financial
adviser.
