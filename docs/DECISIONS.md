# Decisions

This is a decision log, not a chronological transcript. Mark superseded
decisions explicitly.

## D-001 — Keep the maintained PySimpleGUI application

**Decision:** Keep `main.py` -> `src.gui.RothSimulatorGUI` and Penny's existing
visual design.

**Why:** The GUI is the working product surface; replacing it would add risk
without improving the tax model.

**Alternatives:** Promote `src/gui_v2.py` or the Flask `app.py`.

**Tradeoff:** Legacy prototypes remain in the tree and must not be confused with
the maintained entry point.

**Status:** Active.

## D-002 — Use a signed cash-flow ledger, not explanatory notes

**Decision:** Post every asset movement as a signed `LedgerEntry` and reconcile
beginning assets to ending assets each year.

**Why:** Auditable cash flow is a prerequisite for trustworthy optimization.
Notes cannot prove that spending and taxes were actually funded.

**Alternatives:** Keep expense as context only; track taxes outside accounts.

**Tradeoff:** More fields, more UI/report columns and more tests; some historical
tests had to be rewritten to the new semantics.

**Status:** Active. The note-only and outside-account approaches are superseded.

## D-003 — Separate tax liability, tax paid and unpaid tax

**Decision:** Annual `total_tax_paid` remains the liability compatibility field.
`taxes_paid` is funded tax; `taxes_unpaid` is the remainder. At strategy level,
`total_taxes_paid` is actual payments and `total_tax_liability` is liability.

**Why:** A low “tax paid” number can simply mean tax was not funded. Reporting it
as tax cost would mislead the user.

**Alternatives:** Keep one cumulative “taxes paid” number and subtract it from
final net worth.

**Tradeoff:** More fields and labels; reports must explain the distinction.

**Status:** Active.

## D-004 — Explicit, capped tax-funding hierarchy

**Decision:** Fund taxes from the selected source in this order:

- `cash`: cash → Roth withholding → external → unpaid
- `withhold`: Roth withholding → cash → external → unpaid
- `taxable`: taxable sales → cash → Roth withholding → external → unpaid
- `external`: explicit external funds → cash → Roth withholding → unpaid

External funding is capped at `external_tax_funding`.

**Why:** Taxes must have a real source. Unlimited external cash silently makes
every conversion look affordable.

**Alternatives:** Assume taxes are always paid from outside; allow unlimited
external funding.

**Tradeoff:** Some scenarios show unpaid tax or spending shortfalls. That is
intentional.

**Status:** Active.

## D-005 — Spending from cash and taxable assets only

**Decision:** Pay living expenses from cash first, then taxable assets. If those
are exhausted, record `spending_shortfall` rather than making an automatic
pre-tax withdrawal.

**Why:** A pre-tax withdrawal creates additional taxable income, possible
withholding, and ordering interactions. It needs a deliberate tax-aware design.

**Alternatives:** Automatically sell pre-tax assets for spending.

**Tradeoff:** A retiree with only an IRA can show a spending shortfall even
though gross assets exist. This is the preferred next milestone.

**Status:** Active; a future tax-aware pre-tax spending decision may supersede it.

## D-006 — Taxable basis and long-term gains

**Decision:** Track `cost_basis` on taxable accounts, realize gains pro rata on
sales, and calculate incremental long-term gain tax using the existing tax
engine.

**Why:** Selling taxable assets to fund spending or taxes is not tax-free.

**Alternatives:** Ignore gains; assume all sales are basis-only.

**Tradeoff:** Short-term gains, wash sales, loss carryforwards, NIIT and state
conformity remain unmodeled. Gain tax from tax-funding sales is one extra
iteration, not a fixed point.

**Status:** Active.

## D-007 — Deferred-tax reserve for remaining pre-tax value

**Decision:** `final_after_tax_net_worth = final_net_worth -
total_taxes_unpaid - final_deferred_tax_liability`, where the deferred reserve is
the remaining pre-tax balance times `deferred_tax_rate`.

**Why:** Remaining pre-tax money is not tax-free, while taxes already paid from
assets are already reflected in balances. Subtracting cumulative taxes again
double-counts them.

**Alternatives:** Treat pre-tax balances as fully after-tax; subtract lifetime
taxes paid again.

**Tradeoff:** The deferred rate (default 22%) is a planning assumption, not a
prediction of future law.

**Status:** Active.

## D-008 — RMD proceeds are cash, then follow funding rules

**Decision:** Withdraw RMDs pro rata, receive the proceeds as cash, and let
spending/tax settlement consume them.

**Why:** An RMD is a taxable withdrawal, not an automatic reinvestment. Holding
cash makes the ledger and funding order explicit.

**Alternatives:** Move RMD proceeds directly into a taxable account.

**Tradeoff:** Residual cash is swept to a taxable account at year end.

**Status:** Active. Direct-to-taxable RMD handling is superseded.

## D-009 — Synthetic Roth inherits pre-tax growth

**Decision:** When a conversion creates a new Roth account, use the
balance-weighted growth rate of the pre-tax accounts.

**Why:** The converted assets should retain the portfolio's expected return, not
an unrelated hard-coded assumption.

**Alternatives:** Hard-code 7% growth.

**Tradeoff:** A user who expects a different Roth allocation must model that
account separately.

**Status:** Active. The 7% default is superseded.

## D-010 — Versioned rule provenance separate from numeric tables

**Decision:** Keep numeric tables in `src/constants.py`; record identity, scope,
official source, date, status and limitations in `src/rules.py`.

**Why:** The audit trail needs to distinguish verified 2026 law from assumptions
and unsupported areas without duplicating the arithmetic tables.

**Alternatives:** Put source comments in constants; rely on README claims.

**Tradeoff:** Registry and implementation can drift; tests check key statuses,
but future rule changes must update both.

**Status:** Active.

## D-011 — Mark state tax and future indexing as assumptions

**Decision:** Use a flat state rate and 2.5% future indexing, explicitly labeled
as assumptions/limitations.

**Why:** The project does not maintain authoritative state or future-year tables.
Labeling them as current law would be misleading.

**Alternatives:** Omit state tax; present future indexing as verified.

**Tradeoff:** State results are directional only; future-year results are
planning estimates.

**Status:** Active.

## D-012 — Keep reports local and self-contained

**Decision:** HTML and Excel reports are generated locally, with the HTML report
embedding CSS, chart, mascot and the rule registry.

**Why:** User financial data should not leave the computer, and a reviewer needs
a portable audit artifact.

**Alternatives:** Hosted reports; dependencies on external assets.

**Tradeoff:** Report code carries styling and embedding complexity.

**Status:** Active.

## D-013 — Simple repository memory, no database

**Decision:** Use `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/DECISIONS.md` and
`docs/BUILD_HISTORY.md` as plain files; do not build a memory service.

**Why:** Repository search and small checkpoints are sufficient for this project.

**Alternatives:** Memory database or automatic summarization service.

**Tradeoff:** The checkpoint must be maintained manually and kept honest against
the repository; long history belongs in the on-demand archive.

**Status:** Active.

## D-014 — Compact, contextual UI with separated results views

**Decision:** Keep wizard forms compact with two-column layouts and short
muted context notes where a field needs an assumption or consequence. Use flat
button fills. Keep the comparison table to decision metrics and move asset
balances and deferred tax to a **Balances** tab. Put tax, spending and
reconciliation columns first in the detail view, with balances to the right.

**Why:** The previous account and income windows were unnecessarily tall, the
results table clipped its right-most columns, and the detail window exceeded
common screen widths. Splitting the results avoids hiding the after-tax view
while preserving the full asset breakdown.

**Alternatives:** Widen windows beyond common screens; keep every metric in one
table and rely on horizontal scrolling.

**Tradeoff:** The default comparison omits account balances; users must open
the Balances tab to see them. The visual capture harness is a build-only tool,
not a packaged feature.

**Status:** Active.

## D-015 — 3D projection map is a sensitivity surface

**Decision:** Keep the 3D map in `src/projection_map.py` and run every grid point
through the normal simulator with a fixed annual Roth conversion. Optional added
funds are taxable contributions to the first taxable account (synthetic if none
exists). The surface axes are projection year, annual conversion and after-tax
net worth; color is cumulative tax liability including IRMAA. Sweet spots are
non-dominated points on after-tax value and tax cost.

**Why:** Users need to see the trade-off between moving more money to Roth and
paying more tax now, including where added funds change the shape of the plan.
Keeping the grid outside the tax engine avoids a second, drifting model.

**Alternatives:** Add many more optimizer objectives; render a static chart with
no tax axis; treat the map as a fee optimizer.

**Tradeoff:** Fixed conversion amounts are not a full optimization, and advisory
and trading fees are explicitly not modeled. The after-tax value inherits the
scenario's deferred-tax-rate assumption. Added funds are treated as external
taxable contributions, not as a deduction or a transfer from another account.

**Status:** Active.

## D-016 — Penny is a pig farmer, not a piggy-bank body

**Decision:** Draw Penny as an anthropomorphic pig farmer with a cream shirt
and faded bib overalls, including shoulder straps, brass buttons, a patched
knee, rolled cuffs and cloven hooves. Keep the pig head, glasses, ears, snout
and coin slot so she remains recognizably Penny.

**Why:** The old round body left the trotters visually detached and made the
mascot read as a bank rather than a person. A humanoid farmer silhouette gives
her arms, legs and a clear place for the overalls while keeping the warm visual
identity.

**Alternatives:** Keep repairing the four floating trotters; use a human body
without hooves; replace the coin slot with a hat or tool.

**Tradeoff:** This is a visual-only change. The mascot is still rendered by
matplotlib, cached as PNG bytes and embedded in the GUI and HTML reports; no tax
or projection behavior changes.

**Status:** Active.

## D-017 — Settle tax-funding sale gains to a fixed point

**Decision:** When taxable assets fund a tax payment, recalculate and pay the
incremental capital-gains tax through the scenario's existing ordered and
capped sources until the added liability is below one cent. Stop after 20
iterations and disclose that guard if it is ever reached.

**Why:** A taxable sale can create its own tax liability. Leaving that amount
unpaid after one extra calculation understated payments even when permitted
funding remained available.

**Alternatives:** Leave the second-order tax unpaid; estimate it once; solve
with a closed-form rate that would duplicate the progressive tax calculator.

**Tradeoff:** Settlement can add several small ledger entries. The bounded
iteration uses the authoritative calculator and keeps external funding capped.

**Status:** Active.

## D-018 — Return paths feed the existing annual ledger engine

**Decision:** Implement historical windows, circular block bootstrap, explicit
stress paths, sensitivity grids and empirical Sobol paths in
`src/market_simulation.py`. Carry annual returns and inflation on
`ScenarioSettings`; run every path through `ConversionSimulator` rather than
creating a second cash-flow or tax model.

Historical data is user-supplied CSV. Interest-rate observations are preserved
as metadata until an account-level rate mapping exists. Agent-based modeling,
system dynamics and discrete-event simulation are registered as out of scope.

**Why:** Annual return paths are directly relevant to retirement sequence risk
and can reuse all accounting invariants. ABM, system dynamics and DES require
calibrated behavioral, feedback or event models absent from this household tax
planner; a label without those models would be misleading.

**Alternatives:** Embed a static market dataset; silently fetch data; build a
parallel simulator; claim all requested method families as implemented.

**Tradeoff:** The engine and import API are available before GUI controls and
result distributions. A common return currently applies to every investment
account for a path year, and interest rates do not drive account-specific
returns.

**Status:** Active.

## D-019 — Use the current full Uniform Lifetime Table

**Decision:** Use IRS Publication 590-B Table III divisors through age 120 and
apply the 120+ divisor of 2.0 above that age. Keep the younger-spouse Joint and
Last Survivor exception explicitly unsupported.

**Why:** The prior constants switched to outdated divisors at age 86 and ended
at age 100, after which the calculator defaulted to 1.0 and overstated RMDs.

**Alternatives:** Stop projections at age 100; retain the fallback; implement
the spouse-beneficiary exception without collecting beneficiary facts.

**Tradeoff:** Table III is correct for the modeled default population, but a
sole-beneficiary spouse more than ten years younger requires Table II and is
not yet supported.

**Status:** Active.

## Superseded decision summary

| Superseded choice | Replacement |
|---|---|
| Expenses are notes only | Signed ledger and funded spending |
| Taxes paid outside tracked accounts | Explicit funding from cash/Roth/taxable/external |
| Cumulative taxes subtracted from final net worth | Unpaid tax + deferred reserve |
| Strategy `total_taxes_paid` = liability | Actual payments; separate liability field |
| RMD proceeds moved to taxable bucket | RMD proceeds held as cash, then spent/funded |
| Synthetic Roth at hard-coded 7% | Weighted pre-tax growth rate |
| Layout smoke patched a PySimpleGUI popup | Last smoke closed windows through patched `read()`; verify before relying on the old claim |
