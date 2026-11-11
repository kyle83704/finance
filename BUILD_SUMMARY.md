# Build Summary — Version 2.1.0

## Status

✅ Application working, tested, documented and packaged.

| Item | Result |
|---|---|
| Version | 2.1.0 (Penny edition) |
| Python | 3.13.17 |
| UI | PySimpleGUI 4.60.5.1 |
| Tests | **80/80 passing** |
| Layout smoke | Menu, 5 wizard steps, results, picker, detail |
| Example analysis | Completed successfully |
| Packaged executable | `dist/main.exe` |
| Executable size | 79,952,240 bytes |
| SHA-256 | `b25da1e6421abd2a474dd5e9f93f4f322ec5261c9777c17bb9d0a93f3ac38e45` |
| Frozen launch | Window title `Roth Conversion Simulator` |

## Delivered

### User experience

- Warm cream/teal/coral theme shared by GUI, mascot and reports.
- Penny the planning pig rendered from matplotlib objects; no image assets.
- Five-step wizard with progress chips and friendly copy.
- Tabbed comparison/chart results, detail view and help.
- HTML, Excel and CSV exports.
- JSON project save/load.

### Modeling correctness

- Deep-copied accounts per scenario; scenario order is now irrelevant.
- RMDs withdrawn before conversions, taxed as ordinary income and not counted
  as conversions.
- Incremental conversion tax computed as the difference in total tax.
- Pre-conversion pro-rata basis snapshot; non-deductible basis handled.
- Shared pre-tax/Roth/taxable account groups, including Employer 401(k).
- Distinct policy settings for all six objectives and GUI use of the optimizer
  generator.
- IRMAA charged from 65 and counted per eligible spouse.
- Lifetime total tax includes income tax, conversion tax and IRMAA once.

### Reports

- Self-contained HTML report with embedded CSS, chart, mascot and tables.
- Excel workbook with summary, comparison, year-by-year sheets and chart.
- CSV export for raw annual data.

## Verification commands

```bash
python -m compileall -q main.py src tests
python -m unittest discover tests -v
python example_analysis.py
python -m PyInstaller --noconfirm --clean main.spec
```

The headless layout smoke patches PySimpleGUI's layout-error popup to raise and
constructs each window hidden, so a broken layout fails the smoke instead of
being masked by a popup.

## Dependencies

```text
PySimpleGUI>=4.60,<5
pandas>=2.0
numpy>=1.24
scipy>=1.10
matplotlib>=3.7
openpyxl>=3.0
Pillow>=10
pyyaml>=6.0
```

PySimpleGUI is pinned below 5.0 because 5.x requires a paid runtime license.

## Known limitations

- 2026 federal parameters and simplified flat state taxes.
- Current-year MAGI approximation for IRMAA.
- Expenses are not deducted from account balances.
- No capital gains, NIIT, AMT, QCD, estate, Monte Carlo or spousal RMD model.
- `src/gui_v2.py` and `app.py` are legacy prototypes, not part of the build.

## Next work

- Optional dark-mode theme toggle (the current release deliberately uses one
  readable light theme).
- Native PDF generation (HTML reports already print to PDF via the browser).
- Retirement of the legacy prototypes.
- Optional cash-flow ledger for expenses and taxable withdrawals.
