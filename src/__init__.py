"""Roth Conversion Simulator - Financial planning tool for retirement tax optimization."""

__version__ = "2.3.0"
__author__ = "Kyle Fischer"
__description__ = "Comprehensive Roth conversion strategy optimizer"

from src.models import (
    ClientProfile,
    Account,
    IncomeStream,
    Expenses,
    ScenarioSettings,
    ConversionResult,
    ConversionStrategy,
)
from src.tax_calculator import TaxCalculator
from src.simulator import ConversionSimulator
from src.optimizer import ConversionOptimizer

__all__ = [
    "ClientProfile",
    "Account",
    "IncomeStream",
    "Expenses",
    "ScenarioSettings",
    "ConversionResult",
    "ConversionStrategy",
    "TaxCalculator",
    "ConversionSimulator",
    "ConversionOptimizer",
]
