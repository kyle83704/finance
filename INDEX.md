# Roth Conversion Simulator — Documentation Index

Version **2.1.0 (Penny edition)** · 80 automated tests passing

## Start here

1. [QUICKSTART.md](QUICKSTART.md) — install, run, export, build.
2. [README.md](README.md) — features, objective policies and limits.
3. [BUILD_SUMMARY.md](BUILD_SUMMARY.md) — current build and verification.
4. [docs/TECHNICAL.md](docs/TECHNICAL.md) — architecture, tax model and invariants.
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
- Year-by-year federal/state tax, RMD, IRMAA and account projection.
- Scenario comparison with correct isolation between runs.
- HTML, Excel and CSV exports.
- JSON project save/load.
- Penny mascot and warm cream/teal/coral visual theme.

## Correctness highlights

- Accounts are deep-copied for every scenario; order cannot contaminate results.
- RMDs are mandatory withdrawals, not conversions.
- Conversion tax is incremental, not top-marginal-rate × conversion.
- Pro-rata basis is captured before the conversion withdrawal.
- IRMAA starts at 65; the policy cap starts at 63 for the lookback.
- `Employer 401(k)` and `401(k)` are both treated as pre-tax.
- Total lifetime tax includes income tax, conversion tax and IRMAA exactly once.

## Project map

```text
main.py                  Desktop entry point
src/gui.py               Wizard, results, detail and export UI
src/simulator.py         Year-by-year engine and conversion policy
src/optimizer.py         Objective policies, comparison and ranking
src/tax_calculator.py    Federal/state tax, IRMAA, RMD, pro-rata
src/models.py            Dataclasses and JSON persistence
src/constants.py         Tax tables and account groups
src/theme.py             Shared warm palette
src/mascot.py            Penny renderer
src/reports.py           HTML report
src/excel_report.py      Excel workbook report
tests/                   80 automated tests
docs/TECHNICAL.md        Detailed technical reference
```

## Important limits

- 2026 federal tax parameters; simplified flat state tax.
- Current-year MAGI approximation for IRMAA.
- Expenses are not deducted from modeled portfolios.
- No market volatility, capital gains, QCD, AMT, NIIT or estate modeling.
- Educational estimate only; confirm decisions with a qualified professional.

## Legacy

`src/gui_v2.py` and `app.py` are retired prototypes and are not launched by
`main.py`. The Flask app is unsupported and Flask is not in `requirements.txt`.
