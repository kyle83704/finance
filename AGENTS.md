# AGENTS.md

## Project

Penny Tax Strategist is a Python desktop Roth-conversion and retirement-tax
planner. The maintained entry point is:

```text
main.py -> src.gui.RothSimulatorGUI
```

Current release: **2.3.0 (Ledger edition)**. Code baseline commit: `8f9e32b`
on `main`. The application is an educational planner, not tax, legal or
investment advice.

## Architecture map

- `main.py` — GUI entry point.
- `src/gui.py` — PySimpleGUI wizard, results, detail and exports.
- `src/simulator.py` — annual engine: RMDs, conversions, spending, tax funding,
  ledger, growth and reconciliation.
- `src/projection_map.py` — fixed-conversion sensitivity grid, sweet-spot logic
  and the 3D PNG surface.
- `src/market_simulation.py` — historical, bootstrap, stress, sensitivity and
  empirical Sobol return paths feeding the normal simulator.
- `src/tax_calculator.py` — 2026 federal/state tax, Social Security, IRMAA,
  RMD, pro-rata conversion tax and capital-gains tax.
- `src/constants.py` — numeric tax tables, IRMAA, RMD divisors and account groups.
- `src/rules.py` — versioned provenance/status registry for rules and assumptions.
- `src/models.py` — dataclasses, ledger entries and JSON project persistence.
- `src/optimizer.py` — objective policies, scenario generation and comparison.
- `src/reports.py`, `src/excel_report.py` — self-contained HTML and Excel reports.
- `tests/` — 119 tests; `tests/test_phase_b.py` covers cash flow and funding and
  `tests/test_projection_map.py` covers the map and added funds.
- `docs/CURRENT_STATE.md` — resumable checkpoint.
- `docs/DECISIONS.md` — architectural/modeling decisions.
- `docs/BUILD_HISTORY.md` — on-demand build archive; do not load by default.

`src/gui_v2.py` and `app.py` are retired prototypes, not entry points.

## Verified commands

```bash
python -m compileall -q main.py src tests
python -m unittest discover tests -v
python example_analysis.py
python -m PyInstaller --noconfirm --clean main.spec
```

Current measured result (2026-11-23): 119 tests, `OK`. Packaging uses
`main.spec`; the artifact is `dist/main.exe` (80,395,787 bytes; SHA-256
`3fcf5934ca79a1826e3490c7fd0c99f04596d01c3d80aeda545aa7d274efc690`). Do not
push without an explicit request.

## Coding and verification requirements

- Preserve `main.py` -> `src.gui.RothSimulatorGUI` and Penny's visual design.
- Preserve the accounting invariants:
  - every asset movement is in the ledger;
  - `ending_assets - beginning_assets == sum(ledger amounts)`;
  - tax liability, tax paid and unpaid tax are distinct;
  - external tax funding is capped, never unlimited;
  - taxes already paid from assets are not subtracted again.
- Keep `ConversionResult.total_tax_paid` as the annual liability compatibility
  field. At strategy level, `total_taxes_paid` is actual payments and
  `total_tax_liability` is liability.
- Do not present assumptions or unsupported years/jurisdictions as current law.
  Use `src/rules.py` statuses: `verified`, `assumption`, `unsupported`.
- Do not implement or recommend concealment, fabricated deductions, sham
  transactions, false residency or misleading filings.
- Add focused tests for changed logic. Run the smallest relevant checks, then
  the full suite when the change affects shared modeling.
- Report failed or unrun checks honestly; do not weaken tests to get a pass.

## Memory workflow

At session start:

1. Read `AGENTS.md` and `docs/CURRENT_STATE.md`.
2. Check `git status --short`, `git log -1 --oneline` and the branch.
3. Read only files relevant to the active task.
4. Verify important claims against source, tests or authoritative sources.

During work:

- Keep one bounded milestone active.
- Record important decisions in `docs/DECISIONS.md`.
- Keep long build logs out of the startup context.

Before ending or compacting:

1. Update `docs/CURRENT_STATE.md` with actual tests, commits, uncommitted files,
   blockers and the next first action.
2. Add durable decisions to `docs/DECISIONS.md`, marking superseded choices.
3. Update `docs/BUILD_HISTORY.md` only for build/release evidence.
4. Re-read the checkpoint against `git status` and test output.

Do not treat memory notes as more current than the repository.
