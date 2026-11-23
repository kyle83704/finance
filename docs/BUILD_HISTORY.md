# Build History

**Do not load this file at session startup.** Read it only when build/release
history, earlier artifacts or past verification claims are relevant. The full
raw log remains in [`../BUILD_LOGS.md`](../BUILD_LOGS.md); this file is the
compact archive index.

## Taxable-sale settlement revalidation (2026-11-23)

**Basis:** `8f9e32b` plus the existing uncommitted UI/map/mascot work and the
taxable-sale fixed-point settlement change.

- Compile check passed.
- Full suite: 108/108 passing.
- `example_analysis.py` completed successfully.
- PyInstaller build completed successfully.
- `dist/main.exe`: 80,388,165 bytes; SHA-256
  `961467606955b67cba82d0e27089f0b44dcba3b172f35f0c3b383a9870d5eac3`.
- Frozen launch: `LAUNCH_OK`; title `Roth Conversion Simulator`.
- No commit or push performed.

## 2.3.0 — Ledger edition (2026-11-11)

**Code baseline:** `8f9e32b` — `Add reconciled cash-flow ledger and explicit tax
funding`

**Scope:** Reconciled annual ledger; spending from cash/taxable assets; explicit
tax funding (cash, Roth withholding, taxable sales, capped external); taxable
cost basis and gains; liability/paid/unpaid split; deferred-tax after-tax
metric; versioned rule registry; report/UI updates.

**Verification recorded at release:**

- `python -m compileall -q main.py src tests` — exit 0.
- `python -m unittest discover tests -v` — 98/98 passing.
- `python example_analysis.py` — exit 0; 30-year projections and CSV export.
- Hidden-window smoke — menu, five wizard panels, results, picker and detail;
  `LAYOUT_SMOKE_OK`.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0.
- `dist/main.exe` — 79,975,385 bytes.
- SHA-256 — `0520b7e5393420df4c25dfa89e3e914bc8ab820a012ad8a5d20e12338a29c1b1`.
- Frozen launch — child GUI window title `Roth Conversion Simulator`.

**Revalidated at memory checkpoint (2026-11-11):** 98/98 tests passed; artifact
exists and size/hash match. The package was not rebuilt in that checkpoint.

**Known release limits:** MFS/HOH and OBBBA senior deduction unsupported;
short-term gains/wash sales/loss carryforwards/NIIT/AMT/QCD/estate unsupported;
flat state tax and 2.5% future indexing are assumptions; pre-tax spending
withdrawals are not automatic; gain tax from tax-funding sales uses one
additional iteration.

## 2.3.0 UI polish (2026-11-11)

**Basis:** `8f9e32b` plus uncommitted UI changes.

**Scope:** Integrated Penny's ears and coin slot into the silhouette; flattened
buttons; compacted account, income and expense forms; added field context;
grouped scenario objectives; split results into Comparison and Balances tabs;
reordered detail columns and removed the `-$0.00` display artifact.

**Verification recorded for this pass:**

- `python -m compileall -q main.py src tests` — exit 0.
- `python -m unittest discover tests -v` — **99/99 passing**;
  log `build/ui_fix_tests.txt`.
- `python example_analysis.py` — exit 0;
  log `build/ui_fix_example.txt`.
- `python build/capture_ui.py` — exit 0; real-window screenshots for the menu,
  five wizard panels, comparison, balances and detail. Local harness only.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0;
  log `build/ui_fix_build.log`.
- `dist/main.exe` — **79,977,765 bytes**;
  SHA-256 `6b15b9ccb4a9ae723c11189897602e97bf36929de6cd9387a80cf6bab78ec3e4`.
- Frozen launch — `LAUNCH_OK`; title `Roth Conversion Simulator`.

**Status:** Working-tree UI changes are uncommitted; no push was performed.
These figures supersede the 98-test/older-artifact figures for the working tree,
but the historical 2.3.0 release entry above remains the release record.

## Penny farmer redesign (2026-11-11)

**Basis:** `8f9e32b` plus the UI, map and mascot changes.

**Scope:** Replaced Penny's round piggy-bank body with an anthropomorphic pig
farmer: cream shirt, faded bib overalls with straps, brass buttons, a bib
pocket, patched knee, rolled cuffs, hoof hands and cloven hoof feet. The pig
head keeps the glasses, ears, snout and coin slot. Regenerated `docs/penny.png`
and all real-window UI captures.

**Verification recorded for this pass:**

- `python -m compileall -q main.py src tests` — exit 0.
- `python -m unittest discover tests -v` — **107/107 passing**;
  log `build/farmer_penny_suite.txt`.
- `python build/capture_ui.py` — exit 0; eleven fresh real-window screenshots;
  log `build/capture_ui.log`.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0;
  log `build/farmer_penny_build.log`.
- `dist/main.exe` — **79,997,579 bytes**;
  SHA-256 `5e2bc98ba46c716bae4fcd13765eb973028cf1d357ca6f650e3f5e54aa65fa2a`.
- Frozen launch — `LAUNCH_OK`; title `Roth Conversion Simulator`.

**Status:** Working-tree changes are uncommitted; no push was performed.

## Penny anatomy fix (2026-11-11)

**Basis:** `8f9e32b` plus the UI, map and mascot changes.

**Scope:** Completed Penny's glasses with a matching left temple arm; raised
and centered the four trotters so their roots sit under the belly; regenerated
`docs/penny.png` and the real-window UI captures.

**Verification recorded for this pass:**

- `python -m compileall -q main.py src tests` — exit 0.
- `python -m unittest discover tests -v` — **107/107 passing**;
  log `build/mascot_fix_suite.txt`.
- `python build/capture_ui.py` — exit 0; eleven fresh real-window screenshots;
  log `build/capture_ui.log`.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0;
  log `build/mascot_fix_build.log`.
- `dist/main.exe` — **79,994,827 bytes**;
  SHA-256 `58ab92ff1ca7287887e5e3945ee3bac82e2c5048097bb7f71d9eb74380fcb427`.
- Frozen launch — `LAUNCH_OK`; title `Roth Conversion Simulator`.

**Status:** Working-tree changes are uncommitted; no push was performed.

## 2.3.0 3D projection map (2026-11-11)

**Basis:** `8f9e32b` plus the UI-pass and projection-map changes.

**Scope:** Added `src/projection_map.py`, focused map tests, taxable-contribution
cost-basis handling, and the results-window **3D Map** modal with conversion and
added-funds controls, 3D surface, Pareto sweet spots and a comparison table. The
detail window height was corrected so its action row is fully visible.

**Verification recorded for this pass:**

- `python -m compileall -q main.py src tests` — exit 0.
- `python -m unittest discover tests -v` — **107/107 passing**;
  log `build/projection_map_suite.txt`.
- `python example_analysis.py` — exit 0;
  log `build/example_analysis.txt`.
- `python build/capture_ui.py` — exit 0; eleven real-window screenshots,
  including the map surface and sweet-spot table; log `build/capture_ui.log`.
  Local harness only.
- `python -m PyInstaller --noconfirm --clean main.spec` — exit 0;
  log `build/projection_map_build.log`.
- `dist/main.exe` — **79,993,698 bytes**;
  SHA-256 `58ffca4ed57d44957b0f998b37c86baf00654c5fddc28ed52afcc84a087d213f`.
- Frozen launch — `LAUNCH_OK`; title `Roth Conversion Simulator`.

**Status:** Working-tree changes are uncommitted; no push was performed. These
figures supersede the 99-test/older-artifact figures for the current working
tree, while the historical release entries below remain release records.

## 2.2.0 — Tax Pro edition (2026-11-11)

**Scope:** 2026 federal brackets and standard deductions, age-65 add-on, Social
Security provisional-income taxation, qualified-dividend/LTCG rates, SECURE 2.0
RMD ages, six IRMAA tiers, two-year MAGI replay, theme contrast fixes and
expanded reports.

**Recorded verification:** 90/90 tests; example exit 0; PyInstaller exit 0;
`dist/main.exe` 79,960,171 bytes;
SHA-256 `88bbd42df87a969a5138a1050263aeae9c7b6611bb221a13395e17de6b3fbcb5`;
frozen title `Roth Conversion Simulator`.

**Status:** Historical. Counts and artifact are not current; see 2.3.0.

## 2.1.0 — Penny edition (2026-11-11)

**Scope:** Warm Penny theme and mascot, HTML/Excel reporting, scenario isolation,
correct RMD handling, incremental conversion tax, pre-conversion pro-rata basis,
shared account groups, distinct objective policies and IRMAA lookback.

**Recorded verification:** 80/80 tests; layout smoke; example exit 0;
PyInstaller exit 0; `dist/main.exe` 79,952,240 bytes;
SHA-256 `b25da1e6421abd2a474dd5e9f93f4f322ec5261c9777c17bb9d0a93f3ac38e45`.

**Status:** Historical. Some 2.1 semantics were superseded by 2.3 (expenses,
tax payments, RMD proceeds and synthetic Roth growth).

## 1.0 and earlier (2026-11-08 to 2026-11-09)

- Initial release with basic simulation, tax calculation, simple GUI and 32
  tests.
- Earlier development builds included a dark theme and early optimizer work.
- Full narrative is retained in `../BUILD_LOGS.md`.

## Historical claims requiring care

- Test counts and artifact hashes above belong to their release, not the current
  working tree.
- Older logs describe a layout smoke that patched a PySimpleGUI layout-error
  popup. The latest recorded smoke used a patched `sg.Window.read()` and did not
  reconfirm that older technique.
- Older logs describe expenses as notes only, taxes as outside-account payments,
  RMD proceeds as taxable-bucket transfers and a 7% synthetic Roth default.
  Those choices are superseded by 2.3; do not use them as current behavior.
- `src/gui_v2.py` and Flask `app.py` are legacy prototypes, not build targets.
