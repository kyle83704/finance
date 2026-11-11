# Roth Conversion Simulator - Build Logs

## Penny UI + Correctness Overhaul (2026-11-11) - Complete

- **Status**: Complete
- **Version**: 2.1.0 (Penny edition)
- **Scope**: friendly UI, mascot, reporting, scenario logic, tax correctness,
  packaging and documentation.

### UI and reporting
- Added `src/theme.py` (warm cream/teal/coral/gold palette) and `src/mascot.py`
  (Penny rendered with matplotlib objects to transparent PNG and data URI).
- Reworked the main menu, five wizard steps, results tabs, tables, listboxes,
  detail picker and detail view around the shared palette.
- Added `src/reports.py`: self-contained HTML report with embedded CSS, chart,
  mascot and escaped year-by-year tables. The browser Print dialog provides
  PDF output.
- Added `src/excel_report.py`: formatted `.xlsx` with summary, comparison,
  year-by-year sheets and an embedded chart. Added the Excel Report button to
  the results window.
- Added a documentation mascot image at `docs/penny.png`.

### Correctness fixes
- **Scenario isolation**: `run_full_simulation()` deep-copies accounts; the
  optimizer no longer lets one strategy start from another's ending balances.
- **RMD handling**: RMDs are withdrawn pro rata before conversions, taxed as
  ordinary income, moved to taxable accounts, and never counted as voluntary
  conversions. Conversions are capped by the post-RMD pre-tax balance.
- **Incremental conversion tax**: tax is the difference between total tax with
  and without the conversion, not top marginal rate × conversion.
- **Pre-conversion basis**: pro-rata taxable amount and tax use balances
  snapshotted before the withdrawal; non-deductible basis is not counted twice.
- **Account groups**: shared `PRETAX_ACCOUNT_TYPES`, `ROTH_ACCOUNT_TYPES` and
  `TAXABLE_ACCOUNT_TYPES`; `Employer 401(k)` is now recognized.
- **Objective policies**: six distinct policies in `OBJECTIVE_POLICIES`; the GUI
  now calls `ConversionOptimizer.generate_scenarios()` instead of constructing
  identical default scenarios.
- **Tax totals**: `total_taxes_paid` includes income tax, conversion tax and
  IRMAA exactly once; `final_after_tax_net_worth` subtracts it once.
- **IRMAA**: charged from 65, capped in conversion policy from 63 for the
  two-year lookback, and multiplied for a spouse only when 65+.

### Verification
- `python -m compileall -q main.py src tests` — clean.
- `python -m unittest discover tests -v` — **80/80 passing**.
- Headless layout smoke with layout-error popup made fatal — menu, all five
  wizard steps, chart, results, strategy picker and detail view passed.
- `python example_analysis.py` — exit 0; full 30-year projections completed.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0.
- `dist/main.exe` — 79,952,240 bytes.
- SHA-256 — `b25da1e6421abd2a474dd5e9f93f4f322ec5261c9777c17bb9d0a93f3ac38e45`.
- Frozen launch — window title `Roth Conversion Simulator`, no layout error.

### Follow-ups
- Optional dark-mode toggle; the current release intentionally uses one warm,
  high-contrast light theme.
- Native PDF export; HTML printing already covers PDF creation.
- Retire the legacy `src/gui_v2.py` and Flask `app.py` prototypes.
- Optional cash-flow ledger for expenses and taxable withdrawals.
- The model still treats state tax as a flat rate and does not deduct expenses
  from account balances; see README and `docs/TECHNICAL.md` for limits.

## UI Modernization (2026-11-11) - Complete

- **Status**: Complete
- **Entry point**: `main.py` now launches `src.gui.RothSimulatorGUI` (the maintained
  GUI) instead of `src.gui_v2`, whose Analyze action was still a "coming soon" stub.
- **Changes Made**:
  - Added shared design tokens (palette, fonts, separators) and reusable
    `_title` / `_section` / `_field` / `_primary` / `_secondary` / `_neutral` /
    `_danger` helpers so all five wizard steps, the menu, results and detail
    windows share one look.
  - Added a step chip indicator (1 Client -> 5 Scenarios) plus "Step X of 5"
    headers on every wizard window.
  - Modernized main menu (New Analysis / Open Project / Help / Exit) with
    tooltips and a version footer.
  - Expenses step now recalculates monthly and annual totals live as values are
    typed, and the redundant "Calculate Total" button was replaced by "Clear".
  - Scenario selection builds its checkboxes from `OBJECTIVES` instead of a
    hardcoded list, and defaults the projection window to the current year +29.
  - Replaced the blocking animated loading GIF with `sg.one_line_progress_meter`
    that advances per scenario and supports cancellation.
  - Results window is now tabbed: **Comparison** (strategy table plus a
    "best final net worth" summary line) and **Chart** (dark-themed matplotlib
    bar chart of final net worth per strategy).
  - Fixed the broken Detail View strategy picker: `sg.popup_get_choice` does not
    exist in PySimpleGUI; it is now a styled modal `Listbox` window.
  - CSV export now uses `os.path.join` and sanitizes strategy names.
- **Verified**:
  - `python -m py_compile` clean for `main.py`, `src/gui.py`, `src/gui_v2.py`,
    `app.py`, `src/models.py`.
  - `python -m unittest discover tests -v` -> 32/32 passing.
  - End-to-end simulation of 4 accounts / 2 income streams / 2 objectives,
    chart generation (valid PNG bytes), and project save/load round-trip.
  - All windows constructed hidden to validate layouts, then closed.
  - Note: the GUI was smoke-tested programmatically, not visually reviewed on
    screen.

### Project Save/Load (2026-11-10) - Complete
- `save_project` / `load_project` in `src/models.py` serialize the full analysis
  state to JSON (client, accounts, income streams, expenses).
- Main menu "Open Project" resumes at scenario selection; results window
  "Save Project" writes the current state.

### Previous Work

#### UI Modernization (2026-11-09)
- DarkAmber theme, Segoe UI font, brand colors, larger window/layout. This pass
  only reached the main menu and results shell; the wizard steps were completed
  on 2026-11-11 above.

#### Build 2026-11-09 (Version 1.0)
- Initial release
- Basic Roth conversion simulation
- Tax calculation engine
- Simple GUI interface
- Unit tests (32 tests passing)
- All dependencies verified

#### Build 2026-11-08 (Development)
- Core simulator implementation
- Tax calculator with state tax support
- Basic optimization algorithms
- Initial GUI framework

## Technical Notes

### Current Architecture
- **Frontend**: PySimpleGUI 4.60 (pinned `<5` in `requirements.txt` because 5.x
  requires a paid license key at runtime)
- **Backend**: Python with pandas, numpy, scipy
- **Data Processing**: Custom simulator and optimizer classes
- **Tax Engine**: State-specific tax calculations
- **Charts**: matplotlib (Agg backend, rendered into the results window)
- **Persistence**: JSON project files via `src/models.py`

### Known Issues
- `src/gui_v2.py` is an unfinished single-page prototype (search/ML stub,
  Analyze is a no-op) and is no longer the entry point; either finish or retire it.
- `app.py` (Flask web UI) still targets an older model API
  (`expected_growth_rate`, `source_type`, `annual_amount` on `Expenses`) and
  Flask is not in `requirements.txt`; it needs a real pass before use.
- `dist/main.exe` is current for 2.1.0; rebuild after future UI changes.
- Limited error handling in some edge cases.
- Performance could be improved for large datasets.

### Dependencies
- Python 3.9+
- PySimpleGUI>=4.60,<5
- pandas
- numpy
- scipy
- matplotlib
- openpyxl
- Pillow
- pyyaml

## How to Continue Work

1. **To add new features**:
   - Create a new branch for each feature
   - Update requirements.txt as needed
   - Add unit tests for new functionality
   - Document changes in this file

2. **To build executable** (install PyInstaller first):
   ```bash
   python -m PyInstaller --onefile --windowed main.py
   ```

---

**Last Updated**: 2026-11-11
**Next Update**: When new work begins

## START HERE - Next Steps

1. **Optional UI**: dark-mode theme toggle; keep the current light theme as default
2. **Short-term**: retire or finish `src/gui_v2.py`; repair `app.py`
3. **Modeling**: add a cash-flow ledger for expenses and taxable withdrawals
4. **Reporting**: native PDF output; HTML printing already works
5. **Long-term**: Monte Carlo / sensitivity analysis

---

**Note**: This file serves as a central location for tracking all build-related activities. Update it frequently to maintain context across sessions.

## Test Build Fix (2026-11-11)
- **Bug fixed**: `_section()` returned a single row (`[Text]`), but the wizard
  layouts concatenate it as rows. That placed bare `Text` elements at the top
  level, so PySimpleGUI rejected them as non-iterable rows and raised its
  layout-error popup (the PySimpleGUI.py line 20899 path).
- `_section()` now returns `[[Text]]`; added a regression test for the row shape.
- Full suite: 48 tests passing. Rebuilt `dist/main.exe` and launched it: window
  opens with no layout error.
