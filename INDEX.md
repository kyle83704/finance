# Roth Conversion Simulator — Documentation Index

Version **2.3.0 (Ledger edition)** · 98 automated tests passing

## Start here

1. [QUICKSTART.md](QUICKSTART.md) — install, run, export, build.
2. [README.md](README.md) — features, tax funding, objective policies and limits.
3. [BUILD_SUMMARY.md](BUILD_SUMMARY.md) — current build and verification.
4. [docs/TECHNICAL.md](docs/TECHNICAL.md) — architecture, ledger, tax model and invariants.
5. [BUILD_LOGS.md](BUILD_LOGS.md) — work history and build evidence.

## Commands

```bash
# Install
python -m pip install -r requirements.txt

# Run the desktop app
python main.py

# Run the standalone example
python example_analysis.py

# Run all tests
python -m unittest discover tests -v

# Build the Windows executable
python -m PyInstaller --noconfirm --clean main.spec
```

## What it does

- Five-step retirement and Roth conversion wizard.
- Six objective-driven conversion policies.
- Year-by-year federal/state tax, RMD, IRMAA, spending, funding and account
  projection.
- Explicit tax liability versus tax actually paid.
- Taxable cost basis and realized gains.
- Scenario comparison with correct isolation between runs.
- HTML, Excel and CSV exports.
- JSON project save/load.
- Penny mascot and warm cream/teal/coral visual theme.

## Correctness highlights

- Accounts are deep-copied for every scenario; order cannot contaminate results.
- RMDs are mandatory withdrawals, not conversions; proceeds are received as cash.
- Conversion tax is incremental, not top-marginal-rate × conversion.
- Pro-rata basis is captured before the conversion withdrawal.
- Social Security is taxed under provisional-income rules; qualified
  dividends use 0/15/20% federal rates.
- RMD age is 73 for birth years 1951–1959 and 75 for 1960+.
- IRMAA starts at 65, uses MAGI from two years earlier, and combines Part B and
  Part D; the policy cap starts at 63 for the lookback.
- Every asset movement is posted to a ledger; ending assets reconcile to
  beginning assets plus entries.
- Taxes are funded from cash, Roth withholding, taxable sales or explicitly
  capped external money. Unpaid tax is never hidden.
- After-tax net worth subtracts unpaid tax and a deferred-tax reserve, not
  cumulative taxes already paid from assets.
- The HTML report includes the versioned rule/assumption registry.

## Project map

```text
main.py                  Desktop entry point
src/gui.py               Wizard, results, detail and export UI
src/simulator.py         Year-by-year ledger, funding and conversion engine
src/optimizer.py         Objective policies, comparison and ranking
src/tax_calculator.py    Federal/state tax, IRMAA, RMD, pro-rata, gain tax
src/rules.py             Versioned rule and assumption registry
src/models.py            Dataclasses, ledger entries and JSON persistence
src/constants.py         Tax tables and account groups
src/theme.py             Shared warm palette
src/mascot.py            Penny renderer
src/reports.py           HTML report and rule registry
src/excel_report.py      Excel workbook report
tests/                   98 automated tests
docs/TECHNICAL.md        Detailed technical reference
```

## Important limits

- 2026 federal tax parameters with 2.5% indexing after 2026; simplified flat
  state tax.
- MFS/HOH brackets and the OBBBA senior deduction are unsupported.
- IRMAA replays prior MAGI when the lookback years are in the projection;
  otherwise current MAGI is the documented fallback.
- Spending is funded from cash and taxable assets only; unfunded shortfalls are
  reported.
- No market volatility, short-term gains, wash sales, QCD, AMT, NIIT or estate
  modeling.
- Educational estimate only; confirm decisions with a qualified professional.

## Legacy

`src/gui_v2.py` and `app.py` are retired prototypes and are not launched by
`main.py`. The Flask app is unsupported and Flask is not in `requirements.txt`.
