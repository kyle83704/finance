"""Return-path generators for retirement-plan stress and history analysis.

This module supplies annual paths to the normal ledger simulator.  It does not
contain a second tax, cash-flow, or account engine.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
from scipy.stats import qmc


@dataclass(frozen=True)
class HistoricalObservation:
    year: int
    portfolio_return: float
    inflation_rate: float = 0.0
    interest_rate: Optional[float] = None


@dataclass(frozen=True)
class ReturnPath:
    name: str
    method: str
    returns: List[float]
    inflation_rates: List[float] = field(default_factory=list)
    interest_rates: List[Optional[float]] = field(default_factory=list)
    source_years: List[int] = field(default_factory=list)
    notes: str = ""


@dataclass(frozen=True)
class SimulationMethod:
    key: str
    name: str
    status: str
    scope: str


METHODS: Dict[str, SimulationMethod] = {
    "historical": SimulationMethod(
        "historical", "Historical backtest", "supported",
        "Replays contiguous annual return and inflation observations.",
    ),
    "bootstrap": SimulationMethod(
        "bootstrap", "Block bootstrap", "supported",
        "Resamples blocks of observed years with replacement.",
    ),
    "stress": SimulationMethod(
        "stress", "Scenario stress test", "supported",
        "Applies an explicit, hypothetical annual return/inflation path.",
    ),
    "sensitivity": SimulationMethod(
        "sensitivity", "Sensitivity grid", "supported",
        "Builds deterministic combinations of selected planning inputs.",
    ),
    "quasi_monte_carlo": SimulationMethod(
        "quasi_monte_carlo", "Empirical Sobol paths", "supported",
        "Maps low-discrepancy Sobol points to observed return quantiles.",
    ),
    "agent_based": SimulationMethod(
        "agent_based", "Agent-based modeling", "out_of_scope",
        "Requires calibrated interacting market participants and order rules.",
    ),
    "system_dynamics": SimulationMethod(
        "system_dynamics", "System dynamics", "out_of_scope",
        "Requires a calibrated macroeconomic stock-and-flow model.",
    ),
    "discrete_event": SimulationMethod(
        "discrete_event", "Discrete-event simulation", "out_of_scope",
        "Fits operational event queues, not annual household tax projections.",
    ),
}


def _rate(value: str) -> float:
    """Parse either a decimal rate or a value carrying a percent sign."""
    text = str(value).strip()
    if not text:
        return 0.0
    if text.endswith("%"):
        return float(text[:-1]) / 100.0
    return float(text)


def load_historical_csv(filename: str) -> List[HistoricalObservation]:
    """Load year, portfolio_return, inflation_rate and interest_rate columns."""
    observations: List[HistoricalObservation] = []
    with Path(filename).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"year", "portfolio_return"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "Historical CSV needs year and portfolio_return columns."
            )
        for row in reader:
            interest = (row.get("interest_rate") or "").strip()
            observations.append(HistoricalObservation(
                year=int(row["year"]),
                portfolio_return=_rate(row["portfolio_return"]),
                inflation_rate=_rate(row.get("inflation_rate", "0")),
                interest_rate=_rate(interest) if interest else None,
            ))
    observations.sort(key=lambda item: item.year)
    if len({item.year for item in observations}) != len(observations):
        raise ValueError("Historical CSV contains duplicate years.")
    return observations


def historical_windows(
    observations: Sequence[HistoricalObservation], horizon: int
) -> List[ReturnPath]:
    """Return every contiguous calendar window with the requested horizon."""
    if horizon <= 0:
        raise ValueError("Horizon must be positive.")
    paths: List[ReturnPath] = []
    for start in range(0, len(observations) - horizon + 1):
        window = list(observations[start:start + horizon])
        years = [item.year for item in window]
        if any(right != left + 1 for left, right in zip(years, years[1:])):
            continue
        paths.append(_path_from_observations(
            f"Historical {years[0]}-{years[-1]}", "historical", window
        ))
    return paths


def block_bootstrap_paths(
    observations: Sequence[HistoricalObservation],
    horizon: int,
    count: int,
    block_size: int = 3,
    seed: Optional[int] = None,
) -> List[ReturnPath]:
    """Resample circular blocks, retaining short runs and observed extremes."""
    if not observations or horizon <= 0 or count <= 0 or block_size <= 0:
        raise ValueError("Observations, horizon, count and block size are required.")
    rng = random.Random(seed)
    paths: List[ReturnPath] = []
    for path_index in range(count):
        sampled: List[HistoricalObservation] = []
        while len(sampled) < horizon:
            start = rng.randrange(len(observations))
            sampled.extend(
                observations[(start + offset) % len(observations)]
                for offset in range(block_size)
            )
        paths.append(_path_from_observations(
            f"Bootstrap {path_index + 1}", "bootstrap", sampled[:horizon],
            notes=f"Circular block bootstrap; block size {block_size}; seed {seed}.",
        ))
    return paths


def stress_path(
    name: str,
    returns: Sequence[float],
    inflation_rates: Optional[Sequence[float]] = None,
    notes: str = "Hypothetical planning stress; not a forecast.",
) -> ReturnPath:
    """Create an explicit deterministic stress path."""
    values = [float(value) for value in returns]
    if not values or any(value < -1.0 for value in values):
        raise ValueError("Stress returns must be non-empty and no lower than -100%.")
    inflation = ([float(value) for value in inflation_rates]
                 if inflation_rates is not None else [0.0] * len(values))
    if len(inflation) != len(values):
        raise ValueError("Return and inflation paths must have equal lengths.")
    return ReturnPath(name, "stress", values, inflation, notes=notes)


def sensitivity_grid(**factors: Iterable[float]) -> List[Dict[str, float]]:
    """Create the Cartesian product for one- or multi-factor what-if runs."""
    if not factors:
        return []
    names = list(factors)
    values = [list(factors[name]) for name in names]
    if any(not choices for choices in values):
        raise ValueError("Every sensitivity factor needs at least one value.")
    return [dict(zip(names, combination)) for combination in product(*values)]


def empirical_sobol_paths(
    observations: Sequence[HistoricalObservation],
    horizon: int,
    count: int,
) -> List[ReturnPath]:
    """Map deterministic Sobol points through the empirical return distribution."""
    if not observations or horizon <= 0 or count <= 0:
        raise ValueError("Observations, horizon and count are required.")
    ordered = sorted(item.portfolio_return for item in observations)
    sampler = qmc.Sobol(d=horizon, scramble=False)
    points = sampler.random(count)
    paths: List[ReturnPath] = []
    for index, point in enumerate(points):
        ranks = np.minimum((point * len(ordered)).astype(int), len(ordered) - 1)
        paths.append(ReturnPath(
            name=f"Sobol {index + 1}",
            method="quasi_monte_carlo",
            returns=[ordered[rank] for rank in ranks],
            notes="Low-discrepancy points mapped to empirical annual returns.",
        ))
    return paths


def apply_return_path(scenario, path: ReturnPath):
    """Return a copied ScenarioSettings carrying a generated annual path."""
    from dataclasses import replace

    return replace(
        scenario,
        annual_return_path=list(path.returns),
        annual_inflation_path=list(path.inflation_rates),
        return_method=path.method,
        return_path_label=path.name,
    )


def run_return_paths(
    simulator,
    base_scenario,
    paths: Sequence[ReturnPath],
    accounts,
    income_streams,
    expenses,
):
    """Run each path independently through the normal conversion simulator."""
    return [
        simulator.run_full_simulation(
            apply_return_path(base_scenario, path),
            accounts,
            income_streams,
            expenses,
        )
        for path in paths
    ]


def _path_from_observations(
    name: str,
    method: str,
    observations: Sequence[HistoricalObservation],
    notes: str = "",
) -> ReturnPath:
    return ReturnPath(
        name=name,
        method=method,
        returns=[item.portfolio_return for item in observations],
        inflation_rates=[item.inflation_rate for item in observations],
        interest_rates=[item.interest_rate for item in observations],
        source_years=[item.year for item in observations],
        notes=notes,
    )
