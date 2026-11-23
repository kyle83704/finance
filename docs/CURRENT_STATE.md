# Current State

Last checkpoint: **2026-11-23** (taxable-sale tax-funding settlement)
Checkpoint purpose: record the tax-funding upgrade and current verified state.

## Current objective

The 2.3.0 Ledger edition remains intact. Taxable sales used to fund taxes now
settle the additional capital-gains tax to a sub-cent fixed point when permitted
funding remains, rather than leaving that second-order liability unpaid after
one pass. The loop is capped at 20 iterations and preserves source ordering,
the external-funding cap and ledger reconciliation.

## Repository state

- Branch: `main`
- Code baseline commit: `8f9e32b` — `Add reconciled cash-flow ledger and explicit tax funding`
- Working tree is intentionally uncommitted:
  - modified: `BUILD_LOGS.md`, `BUILD_SUMMARY.md`, `docs/penny.png`,
    `src/gui.py`, `src/mascot.py`, `src/simulator.py`,
    `tests/test_gui_helpers.py`, `tests/test_phase_b.py`
  - untracked: `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/DECISIONS.md`,
    `docs/BUILD_HISTORY.md`, `src/projection_map.py`,
    `tests/test_projection_map.py`
- No commit or push was performed for the UI/map/mascot work.
- Current release: `2.3.0` (`src/__init__.py`, GUI footer and docs agree).

## Verified implementation state

- `main.py` launches `src.gui.RothSimulatorGUI`.
- Annual simulation uses a signed ledger covering income, RMDs, conversions,
  spending, tax payments, external funding, cash sweeps, contributions and
  growth. `ending_assets - beginning_assets == sum(ledger amounts)` is tested.
- Spending is paid from cash, then taxable assets; an unfunded shortfall is
  recorded rather than invented.
- Tax payment sources are cash, Roth withholding, taxable sales and capped
  external money. Tax liability, tax actually paid and unpaid tax remain
  distinct.
- Gains created by tax-funding sales are recalculated and settled through the
  same capped sources to a sub-cent fixed point, with a 20-iteration guard.
- `ConversionResult.total_tax_paid` remains the annual liability compatibility
  field. At strategy level, `total_taxes_paid` is actual payments and
  `total_tax_liability` is liability.
- `final_after_tax_net_worth` subtracts unpaid tax and the deferred-tax reserve,
  not cumulative taxes already paid from assets.
- Taxable annual contributions now add to `cost_basis`, preventing later sales
  from overstating realized gains.
- 2026 federal and IRMAA records retain official source links in `src/rules.py`;
  future indexing, flat state tax and other limits remain labeled assumptions or
  unsupported areas.

## 3D projection map delivered

- `src/projection_map.py` runs a fixed annual conversion grid through the normal
  optimizer/simulator. Axes are projection year, annual conversion and after-tax
  net worth; color is cumulative tax load including IRMAA.
- The `Sweet Spots` calculation is a Pareto check: a point must not be beaten on
  both after-tax value and tax cost. The table calls out `Best net` and
  `Lowest tax` and lists the paths with their change versus the no-conversion
  path.
- Results now has a **3D Map** button. The modal has controls for extra annual
  funds, maximum annual conversion and grid size; **Build Map** regenerates both
  the surface and the table.
- Added funds go to the first taxable account, or a synthetic taxable account
  when none exists. They are taxable contributions, not a deduction, and there
  is no assumed advisory or trading fee.
- The surface note states that fees are not modeled; users can enter them as
  expenses if needed. After-tax value subtracts unpaid tax and the deferred-tax
  reserve on remaining pre-tax assets.
- The map window fits its action row, and the existing detail window was raised
  to 700 px so its Close control is fully visible.

## Prior UI pass delivered

- Penny is an anthropomorphic pig farmer in faded bib overalls with a cream
  shirt, shoulder straps, brass buttons, a patched knee and rolled cuffs.
- Her hands and feet are cloven hooves, and her glasses, ears, snout and coin
  slot remain legible at menu, results-card and report sizes.
- Flat buttons and compact two-column account, income and expense forms.
- Short inline context for basis, growth, Social Security, spending and
  tax-funding assumptions.
- Grouped scenario objectives with policy tooltips.
- Results have separate **Comparison** and **Balances** tabs; the detail view has
  tax, spending and reconciliation columns first.

## Checks actually run

- `python -m compileall -q main.py src tests` — exit 0.
- `python -m unittest discover tests -v` — **108 tests, 0 failures, `OK`**
  on 2026-11-23, including the taxable-sale fixed-point regression.
- `python example_analysis.py` — exit 0; 30-year projections and CSV export.
  - Log: `build/example_analysis.txt`
- `python build/capture_ui.py` — exit 0; **eleven** real-window captures:
  - `build/ui_roth_conversion_simulator.png`
  - `build/ui_new_analysis_step_1_5_client_profile.png`
  - `build/ui_new_analysis_step_2_5_accounts.png`
  - `build/ui_new_analysis_step_3_5_income_streams.png`
  - `build/ui_new_analysis_step_4_5_expenses.png`
  - `build/ui_new_analysis_step_5_5_scenarios.png`
  - `build/ui_analysis_results.png`
  - `build/ui_analysis_results_balances.png`
  - `build/ui_projection_map.png`
  - `build/ui_projection_map_sweet_spots.png`
  - `build/ui_strategy_detail.png`
  - Harness log: `build/capture_ui.log`. This is a local visual harness, not part
    of the packaged application or test suite.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0.
  - Log: `build/farmer_penny_build.log`
  - Artifact: `dist/main.exe`
  - Size: **80,388,165 bytes**
  - SHA-256: `961467606955b67cba82d0e27089f0b44dcba3b172f35f0c3b383a9870d5eac3`
- Frozen launch check via `build/launch_check.ps1` — `LAUNCH_OK`; child window
  title `Roth Conversion Simulator`.

## Unresolved issues and known limits

1. The map is a fixed-conversion sensitivity surface, not a global optimizer; it
   does not search every possible conversion schedule.
2. The map does not model advisory or trading fees. Its after-tax value uses the
   scenario's deferred-tax-rate assumption and is not a prediction of future law.
3. Added funds are external taxable contributions; the map does not specify
   which account or income source supplies them.
4. Spending cannot be funded automatically from pre-tax accounts; only cash and
   taxable assets are used.
5. MFS/HOH federal brackets, OBBBA senior deduction, short-term gains, wash
   sales, loss carryforwards, NIIT, AMT, QCDs and estate tax remain unsupported.
6. State tax is a flat approximation; 2.5% future indexing is a planning
   assumption.
7. Persistence has basic load validation but no full schema migration workflow.
8. `build/capture_ui.py` is a local visual harness and is not packaged.

## Exact next steps

1. Review the uncommitted diff, including the taxable-sale settlement change;
   commit only when the user explicitly asks.
2. Do not push without an explicit request.
3. If extending the map, keep each new behavior in `src/projection_map.py` with a
   focused test; do not duplicate tax laws in the renderer.
4. Run `python -m unittest discover tests -v` before changing behavior, and
   rebuild `dist/main.exe` after any source or help-text change.

## Relevant paths

```text
main.py
src/gui.py
src/projection_map.py
src/simulator.py
src/tax_calculator.py
src/constants.py
src/rules.py
src/models.py
src/optimizer.py
src/reports.py
src/excel_report.py
tests/test_projection_map.py
tests/test_gui_helpers.py
tests/test_phase_b.py
tests/test_simulator.py
tests/test_tax_calculator.py
docs/TECHNICAL.md
BUILD_SUMMARY.md
BUILD_LOGS.md
```

## Failed or rejected approaches — do not repeat

- Paying expenses only as a note without reducing assets.
- Treating taxes as paid outside tracked accounts and subtracting cumulative
  taxes from final net worth.
- Hard-coding a 7% growth rate for a newly created Roth account.
- Moving RMD proceeds into a taxable bucket instead of receiving cash and then
  applying spending/tax funding.
- Treating the old strategy-level `total_taxes_paid` as liability after the 2.3
  payment split.
- Presenting the map's deferred-tax rate or added-funds path as current law or a
  guaranteed outcome.
- Adding a second tax engine or a fee estimate that is not in the ledger.
- Using `src/gui_v2.py` or `app.py` as the maintained entry point.
- Trusting historical build/test counts without rerunning the current suite.
