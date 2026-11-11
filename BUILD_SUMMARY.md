# Build Summary — Version 2.3.0

## Status

✅ Application working, tested, documented and packaged.

| Item | Result |
|---|---|
| Version | 2.3.0 (Ledger edition) |
| Python | 3.13.17 |
| UI | PySimpleGUI 4.60.5.1 |
| Tests | **98/98 passing** |
| Layout smoke | Menu, 5 wizard panels, results, picker, detail |
| Example analysis | Exit 0 |
| Packaged executable | `dist/main.exe` |
| Executable size | 79,975,385 bytes |
| SHA-256 | `0520b7e5393420df4c25dfa89e3e914bc8ab820a012ad8a5d20e12338a29c1b1` |
| Frozen launch | Window title `Roth Conversion Simulator` |

No push was performed.

## Delivered

### User experience

- Warm cream/teal/coral theme shared by GUI, mascot and reports.
- Five-step wizard with progress chips and friendly copy.
- Tax-funding selection: cash, Roth withholding, taxable sales or capped
  external money.
- Deferred-tax assumption and taxable cost-basis inputs.
- Tabbed comparison/chart results, detail view and help.
- HTML, Excel and CSV exports.
- JSON project save/load.

### Cash-flow and accounting correctness

- Signed ledger for income, RMDs, conversions, spending, tax payments,
  contributions, growth and residual cash.
- Every year reconciles beginning assets to ending assets through the ledger.
- Spending paid from cash, then taxable assets; unfunded shortfalls are
  reported explicitly.
- Tax liability separated from tax actually paid and unpaid tax.
- Tax funding hierarchy is explicit and external funding is capped.
- Roth withholding reduces the Roth balance, not the pre-tax balance.
- Taxable sales use cost basis and realize gains; incremental gain tax is
  included.
- After-tax net worth subtracts unpaid tax and a deferred-tax reserve on
  remaining pre-tax value. Taxes already paid are not subtracted twice.
- Synthetic Roth accounts inherit the pre-tax portfolio's weighted growth rate.

### Tax and auditability

- Actual 2026 IRS brackets and standard deductions, including the 65+ add-on.
- Social Security provisional-income taxation and qualified-dividend rates.
- SECURE 2.0 RMD ages (73 or 75) and 2.5% future indexing assumption.
- Six IRMAA tiers including Part B and Part D, with a two-year MAGI replay.
- Versioned rules registry with official sources, retrieval date, status and
  limitations.
- HTML report includes the registry so verified law, assumptions and
  unsupported areas are visible to a reviewer.
- Unsupported areas are disclosed rather than labeled current law: MFS/HOH
  brackets, OBBBA senior deduction, short-term gains, wash sales, loss
  carryforwards, NIIT, AMT, QCDs and estate tax.

### Reports

- Self-contained HTML with comparison, annual detail and rule registry.
- Excel workbook with summary, comparison, annual sheets and chart.
- CSV export for raw annual data.

## Verification commands

```bash
python -m compileall -q main.py src tests
python -m unittest discover tests -v
python example_analysis.py
python -m PyInstaller --noconfirm --clean main.spec
```

The hidden-window smoke monkeypatches `sg.Window.read()` to close each window
immediately, then constructs the menu, all five wizard panels, results, strategy
picker and detail view. Layout errors fail the smoke rather than being hidden by
a popup.

## Measured verification

- Compile: exit 0.
- Tests: **98 tests, 0 failures**.
- Example: exit 0; 30-year projections completed; CSV written.
- Layout smoke: `LAYOUT_SMOKE_OK`.
- PyInstaller: exit 0.
- Artifact: `dist/main.exe`, 79,975,385 bytes.
- SHA-256: `0520b7e5393420df4c25dfa89e3e914bc8ab820a012ad8a5d20e12338a29c1b1`.
- Frozen launch: child GUI window title `Roth Conversion Simulator`.

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

- 2026 federal parameters with 2.5% indexing after 2026; simplified flat state
  taxes.
- MFS/HOH federal brackets and OBBBA senior deduction are unsupported.
- IRMAA uses prior MAGI when the projection covers the lookback; otherwise it
  falls back to current MAGI.
- Short-term gains, wash sales, loss carryforwards, NIIT, AMT, QCD, estate,
  Monte Carlo and spousal RMD synchronization are not modeled.
- Spending cannot be funded automatically from pre-tax accounts.
- The gain tax created by selling taxable assets to pay tax is computed in one
  additional iteration and disclosed.
- `src/gui_v2.py` and `app.py` are legacy prototypes, not part of the build.
- Educational estimate only; not tax, legal or investment advice.

## Next work

- Add tax-aware pre-tax withdrawals for spending.
- Add a fixed-point calculation for gain taxes caused by tax-funding sales.
- Add state-specific progressive brackets and retirement exclusions.
- Retire the legacy prototypes.
- Native PDF generation (HTML reports already print to PDF).
