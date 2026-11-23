"""Grid data and 3D rendering for the projection-map view.

The map is a sensitivity surface, not a new tax model.  Each point is a normal
full simulation with a fixed annual Roth conversion target and, optionally, an
extra annual contribution to the first taxable account.  The surface shows the
planning value after unpaid tax and a deferred-tax reserve on remaining pre-tax
assets.  Tax load includes income tax, conversion tax, gain tax and IRMAA;
advisory/trading fees are not modeled.

This module is deliberately separate from the GUI so the grid, the sweet-spot
logic and the chart can be tested without opening a window.
"""

from dataclasses import dataclass, field
import copy
import io
from typing import Iterable, List, Optional

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from src import theme
from src.constants import TAXABLE_ACCOUNT_TYPES
from src.models import (
    Account,
    ClientProfile,
    ConversionStrategy,
    Expenses,
    IncomeStream,
    ScenarioSettings,
)
from src.optimizer import ConversionOptimizer


@dataclass
class ProjectionMapPoint:
    """One fixed-conversion path in the projection grid."""

    conversion_target: float
    strategy: ConversionStrategy
    after_tax_by_year: List[float] = field(default_factory=list)
    cumulative_tax_by_year: List[float] = field(default_factory=list)
    final_after_tax_net_worth: float = 0.0
    tax_load: float = 0.0
    incremental_net: float = 0.0
    incremental_tax: float = 0.0
    value_per_extra_tax: Optional[float] = None
    is_sweet_spot: bool = False
    is_best_net: bool = False
    is_lowest_tax: bool = False
    is_best_value: bool = False

    @property
    def year_count(self) -> int:
        return len(self.after_tax_by_year)


@dataclass
class ProjectionMap:
    """Completed sensitivity grid and its interpretation."""

    points: List[ProjectionMapPoint]
    conversion_targets: List[float]
    years: List[int]
    extra_annual_funds: float
    added_funds_account: str
    deferred_tax_rate: float
    notes: List[str] = field(default_factory=list)

    @property
    def sweet_spots(self) -> List[ProjectionMapPoint]:
        return [point for point in self.points if point.is_sweet_spot]


def conversion_grid(max_conversion: float, steps: int = 7) -> List[float]:
    """Build a rounded, de-duplicated conversion grid that includes zero."""
    maximum = max(0.0, float(max_conversion))
    if maximum == 0:
        return [0.0]

    count = max(3, min(12, int(steps)))
    values = {0.0, round(maximum, 2)}
    for index in range(1, count - 1):
        values.add(round(maximum * index / (count - 1), -3))
    return sorted(value for value in values if value <= maximum)


def _weighted_growth(accounts: Iterable[Account]) -> float:
    """Weighted average growth, with a documented fallback for empty plans."""
    accounts = list(accounts)
    weights = [max(0.0, account.current_balance) for account in accounts]
    total = sum(weights)
    if total > 0:
        return sum(weight * account.growth_rate
                   for weight, account in zip(weights, accounts)) / total
    if accounts:
        return sum(account.growth_rate for account in accounts) / len(accounts)
    return 0.05


def _accounts_with_extra_funds(
    accounts: Iterable[Account],
    extra_annual_funds: float,
) -> tuple[List[Account], str]:
    """Copy accounts and add extra annual money to the first taxable account.

    If the plan has no taxable account, a synthetic taxable account is created
    with the portfolio's weighted growth rate.  Extra funds are treated as
    taxable contributions; no deduction or advisory fee is assumed.
    """
    run_accounts = copy.deepcopy(list(accounts))
    extra = max(0.0, float(extra_annual_funds))
    target = next(
        (account for account in run_accounts
         if account.account_type in TAXABLE_ACCOUNT_TYPES),
        None,
    )

    if target is None and extra > 0:
        target = Account(
            name="Added Funds (taxable)",
            account_type="Taxable Brokerage",
            current_balance=0.0,
            growth_rate=_weighted_growth(run_accounts),
            annual_contribution=0.0,
        )
        run_accounts.append(target)

    if target is not None:
        target.annual_contribution = (
            max(0.0, target.annual_contribution or 0.0) + extra
        )
        return run_accounts, target.name

    return run_accounts, "No taxable account"


def _after_tax_path(strategy: ConversionStrategy) -> tuple[List[float], List[float]]:
    """Return annual after-tax value and cumulative tax load for a strategy.

    Taxes already paid have already reduced asset balances, so the planning
    value subtracts only cumulative unpaid tax and the deferred-tax reserve on
    the remaining pre-tax balance.
    """
    deferred_rate = max(0.0, min(1.0, float(strategy.scenario.deferred_tax_rate)))
    after_tax: List[float] = []
    cumulative_tax: List[float] = []
    unpaid_to_date = 0.0
    tax_to_date = 0.0

    for year in strategy.years:
        unpaid_to_date += year.taxes_unpaid
        tax_to_date += year.total_tax_paid
        gross = (
            year.end_balance_pretax
            + year.end_balance_roth
            + year.end_balance_taxable
        )
        deferred = max(0.0, year.end_balance_pretax) * deferred_rate
        after_tax.append(gross - unpaid_to_date - deferred)
        cumulative_tax.append(tax_to_date)

    return after_tax, cumulative_tax


def build_projection_map(
    client: ClientProfile,
    base_scenario: ScenarioSettings,
    accounts: Iterable[Account],
    income_streams: Iterable[IncomeStream],
    expenses: Expenses,
    conversion_targets: Iterable[float],
    extra_annual_funds: float = 0.0,
) -> ProjectionMap:
    """Run a fixed-conversion grid and identify non-dominated choices."""
    targets = sorted({
        max(0.0, round(float(target), 2))
        for target in conversion_targets
    })
    if 0.0 not in targets:
        targets.insert(0, 0.0)
    if len(targets) < 2:
        raise ValueError("Projection map needs at least two conversion targets.")

    optimizer = ConversionOptimizer(client)
    extra = max(0.0, float(extra_annual_funds))
    points: List[ProjectionMapPoint] = []
    added_account = "No taxable account"
    years: List[int] = []

    for target in targets:
        run_accounts, added_account = _accounts_with_extra_funds(accounts, extra)
        scenario = ScenarioSettings(
            name=f"Map: ${target:,.0f}/yr",
            description=(
                f"Fixed ${target:,.0f}/year Roth conversion with "
                f"${extra:,.0f}/year added taxable funds."
            ),
            start_year=base_scenario.start_year,
            end_year=base_scenario.end_year,
            target_objective="Fixed Amount",
            annual_conversion_target=target,
            max_conversion_allowed=target,
            avoid_irmaa=False,
            fill_tax_bracket=False,
            constraint_tax_rate=None,
            tax_payment_source=base_scenario.tax_payment_source,
            external_tax_funding=base_scenario.external_tax_funding,
            deferred_tax_rate=base_scenario.deferred_tax_rate,
        )
        strategy = optimizer.run_scenario_comparison(
            [scenario],
            run_accounts,
            list(income_streams),
            expenses,
        )[0]
        after_tax, cumulative_tax = _after_tax_path(strategy)
        if not years:
            years = [year.year for year in strategy.years]

        points.append(ProjectionMapPoint(
            conversion_target=target,
            strategy=strategy,
            after_tax_by_year=after_tax,
            cumulative_tax_by_year=cumulative_tax,
            final_after_tax_net_worth=(
                after_tax[-1] if after_tax else strategy.final_after_tax_net_worth
            ),
            tax_load=strategy.total_tax_liability,
        ))

    baseline = min(points, key=lambda point: point.conversion_target)
    for point in points:
        point.incremental_net = (
            point.final_after_tax_net_worth - baseline.final_after_tax_net_worth
        )
        point.incremental_tax = point.tax_load - baseline.tax_load
        if point.incremental_tax > 1.0:
            point.value_per_extra_tax = (
                point.incremental_net / point.incremental_tax
            )

    for point in points:
        point.is_sweet_spot = not any(
            other is not point
            and other.final_after_tax_net_worth >= point.final_after_tax_net_worth - 1.0
            and other.tax_load <= point.tax_load + 1.0
            and (
                other.final_after_tax_net_worth > point.final_after_tax_net_worth + 1.0
                or other.tax_load < point.tax_load - 1.0
            )
            for other in points
        )

    best_net = max(points, key=lambda point: point.final_after_tax_net_worth)
    best_net.is_best_net = True
    min(points, key=lambda point: point.tax_load).is_lowest_tax = True
    value_candidates = [
        point for point in points if point.value_per_extra_tax is not None
    ]
    if value_candidates:
        best_value = max(
            value_candidates, key=lambda point: point.value_per_extra_tax
        )
        best_value.is_best_value = True

    if not any(point.is_sweet_spot for point in points):
        best_net.is_sweet_spot = True
        min(points, key=lambda point: point.tax_load).is_sweet_spot = True

    notes = [
        "After-tax value subtracts cumulative unpaid tax and a deferred-tax "
        "reserve on remaining pre-tax assets; taxes already paid are reflected "
        "in balances.",
        "Tax load includes income, conversion, gain and IRMAA costs. Advisory "
        "and trading fees are not modeled.",
    ]
    if extra > 0:
        notes.append(
            f"Added funds are taxable contributions to {added_account}; no "
            "deduction or advisory fee is assumed."
        )

    return ProjectionMap(
        points=points,
        conversion_targets=targets,
        years=years,
        extra_annual_funds=extra,
        added_funds_account=added_account,
        deferred_tax_rate=max(
            0.0, min(1.0, float(base_scenario.deferred_tax_rate))
        ),
        notes=notes,
    )


def render_projection_map(map_result: ProjectionMap) -> bytes:
    """Render the map and sweet-spot markers as a PNG for the GUI."""
    if len(map_result.points) < 2:
        raise ValueError("Projection map needs at least two paths.")
    if len(map_result.years) < 2:
        raise ValueError("Projection map needs at least two projection years.")

    years = np.array(map_result.years, dtype=float)
    conversions = np.array(
        [point.conversion_target for point in map_result.points], dtype=float
    )
    after_tax = np.array(
        [point.after_tax_by_year for point in map_result.points], dtype=float
    )
    cumulative_tax = np.array(
        [point.cumulative_tax_by_year for point in map_result.points], dtype=float
    )
    year_grid, conversion_grid_values = np.meshgrid(years, conversions)

    cmap = LinearSegmentedColormap.from_list(
        "penny_tax", [theme.TEAL_SOFT, theme.GOLD, theme.CORAL]
    )
    vmin = float(np.min(cumulative_tax))
    vmax = float(np.max(cumulative_tax))
    if vmax - vmin < 1.0:
        vmax = vmin + 1.0
    norm = Normalize(vmin=vmin, vmax=vmax)

    figure = Figure(figsize=(9.7, 4.0), dpi=110, facecolor=theme.SURFACE)
    FigureCanvasAgg(figure)
    ax = figure.add_subplot(111, projection="3d")
    ax.set_facecolor(theme.CHART_BG)

    ax.plot_surface(
        year_grid,
        conversion_grid_values,
        after_tax,
        facecolors=cmap(norm(cumulative_tax)),
        rstride=1,
        cstride=1,
        linewidth=0.15,
        edgecolor=theme.SURFACE,
        antialiased=True,
        shade=False,
    )

    sweet_spots = map_result.sweet_spots
    if sweet_spots:
        ax.scatter(
            [years[-1]] * len(sweet_spots),
            [point.conversion_target for point in sweet_spots],
            [point.after_tax_by_year[-1] for point in sweet_spots],
            color=theme.NAVY,
            marker="*",
            s=150,
            depthshade=False,
            label="Sweet spot",
        )
        ax.legend(loc="upper left", fontsize=7, frameon=False)

    step = max(1, len(years) // 5)
    ax.set_xticks(years[::step])
    ax.set_yticks(conversions)
    ax.set_yticklabels([f"${value / 1000:,.0f}k" for value in conversions])
    ax.zaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"${value / 1_000_000:,.1f}M")
    )
    ax.set_xlabel("Projection year", labelpad=8, color=theme.MUTED_TEXT)
    ax.set_ylabel("Annual conversion", labelpad=8, color=theme.MUTED_TEXT)
    ax.set_zlabel("After-tax net worth", labelpad=8, color=theme.MUTED_TEXT)
    ax.tick_params(colors=theme.MUTED_TEXT, labelsize=7)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor(theme.SURFACE)
        axis.pane.set_edgecolor(theme.BORDER)
        axis.pane.set_alpha(0.55)
    ax.grid(True, alpha=0.25)
    ax.set_box_aspect((1.7, 1.0, 0.9))
    ax.view_init(elev=24, azim=-58)

    added_label = (
        f"${map_result.extra_annual_funds:,.0f}/yr added to "
        f"{map_result.added_funds_account}"
        if map_result.extra_annual_funds > 0
        else "No added funds"
    )
    figure.suptitle(
        "3D projection map · after-tax value and tax cost",
        color=theme.NAVY,
        fontsize=12,
        fontweight="bold",
    )
    ax.set_title(added_label, color=theme.MUTED_TEXT, fontsize=8, pad=2)

    scalar_mappable = cm.ScalarMappable(norm=norm, cmap=cmap)
    scalar_mappable.set_array(cumulative_tax)
    colorbar = figure.colorbar(
        scalar_mappable,
        ax=ax,
        shrink=0.58,
        pad=0.08,
        aspect=18,
    )
    colorbar.set_label(
        "Cumulative tax load incl. IRMAA",
        color=theme.MUTED_TEXT,
        fontsize=8,
    )
    colorbar.ax.tick_params(colors=theme.MUTED_TEXT, labelsize=7)
    colorbar.ax.yaxis.set_major_formatter(
        FuncFormatter(lambda value, _: f"${value / 1000:,.0f}k")
    )

    figure.subplots_adjust(left=0.0, right=0.86, top=0.80, bottom=0.14)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=110, facecolor=figure.get_facecolor())
    return buffer.getvalue()
