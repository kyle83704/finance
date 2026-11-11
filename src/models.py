"""Data models for Roth conversion simulator."""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import json
import os


@dataclass
class Account:
    """Represents a single account (IRA, 401k, brokerage, etc.)."""
    name: str
    account_type: str  # "Traditional IRA", "Roth IRA", "401(k)", etc.
    current_balance: float
    pretax_basis: float = 0.0  # For pro-rata Roth conversion calculations
    aftertax_basis: float = 0.0  # Non-deductible contributions
    cost_basis: float = 0.0  # For taxable brokerage accounts
    unrealized_gains: float = 0.0  # For taxable accounts
    annual_contribution: float = 0.0  # Expected annual additions
    contribution_type: str = "pretax"  # "pretax", "aftertax", "roth"
    growth_rate: float = 0.07  # Expected annual growth %


@dataclass
class IncomeStream:
    """Represents a source of income."""
    name: str
    income_type: str  # "W2", "Self-Employment", "Social Security", "Pension", "Dividends"
    annual_amount: float
    start_age: int = 0  # Age when income starts
    end_age: int = 100  # Age when income stops
    growth_rate: float = 0.03  # Annual growth %
    tax_treatment: str = "ordinary"  # "ordinary", "qualified_dividends", "tax_free" (SS, HSA)
    ss_claim_age: Optional[int] = None  # For Social Security only


@dataclass
class ClientProfile:
    """Represents the client's personal information and situation."""
    first_name: str
    last_name: str
    birth_year: int
    spouse_birth_year: Optional[int] = None
    state_residence: str = "ID"  # Default to Idaho
    filing_status: str = "married_filing_jointly"  # or "single", "married_filing_separately"
    current_age: int = field(init=False)
    spouse_current_age: Optional[int] = field(init=False)
    
    def __post_init__(self):
        current_year = datetime.now().year
        self.current_age = current_year - self.birth_year
        if self.spouse_birth_year:
            self.spouse_current_age = current_year - self.spouse_birth_year
        else:
            self.spouse_current_age = None


@dataclass
class Expenses:
    """Represents annual living expenses."""
    housing: float = 0.0
    utilities: float = 0.0
    food: float = 0.0
    transportation: float = 0.0
    healthcare: float = 0.0
    insurance: float = 0.0  # Health, auto, home, life
    discretionary: float = 0.0
    other: float = 0.0
    
    @property
    def total_annual(self) -> float:
        return (self.housing + self.utilities + self.food + self.transportation +
                self.healthcare + self.insurance + self.discretionary + self.other)
    
    @property
    def total_monthly(self) -> float:
        return self.total_annual / 12


@dataclass
class ScenarioSettings:
    """Settings for a conversion scenario."""
    name: str
    description: str = ""
    start_year: int = 2026
    end_year: int = 2055
    target_objective: str = "Maximize Roth Value"  # From OBJECTIVES list
    annual_conversion_target: Optional[float] = None  # $ amount to convert each year
    max_conversion_allowed: float = float('inf')  # Don't exceed this amount
    avoid_irmaa: bool = True  # Try to stay below IRMAA thresholds
    fill_tax_bracket: bool = True  # Convert up to top of current bracket
    constraint_tax_rate: Optional[float] = None  # Don't let marginal rate exceed this


@dataclass
class ConversionResult:
    """Result of a single year's conversion analysis."""
    year: int
    age: int
    start_balance_pretax: float
    start_balance_roth: float
    start_balance_taxable: float
    
    rmd_required: float = 0.0
    rmd_source: str = ""  # Which account to take RMD from
    
    recommended_conversion: float = 0.0
    conversion_tax: float = 0.0  # Incremental tax caused by the conversion
    income_tax: float = 0.0  # Tax on income streams + RMD, before conversion
    irmaa_impact: float = 0.0  # Additional Medicare costs for the year
    
    end_balance_pretax: float = 0.0
    end_balance_roth: float = 0.0
    end_balance_taxable: float = 0.0
    total_tax_paid: float = 0.0
    
    notes: List[str] = field(default_factory=list)


@dataclass
class ConversionStrategy:
    """A complete conversion strategy from now until target age."""
    scenario: ScenarioSettings
    client: ClientProfile
    accounts: List[Account]
    income_streams: List[IncomeStream]
    expenses: Expenses
    
    years: List[ConversionResult] = field(default_factory=list)
    total_conversions: float = 0.0
    total_conversion_taxes: float = 0.0  # Incremental tax from conversions only
    total_income_taxes: float = 0.0  # Income tax + conversion tax
    total_taxes_paid: float = 0.0  # Income + conversion tax + IRMAA
    total_irmaa_costs: float = 0.0
    final_roth_value: float = 0.0
    final_pretax_value: float = 0.0
    final_taxable_value: float = 0.0
    final_net_worth: float = 0.0

    @property
    def final_after_tax_net_worth(self) -> float:
        """Gross final net worth less the taxes and IRMAA paid along the way.

        Taxes are modelled as being paid from outside the tracked accounts, so
        this is the comparable after-tax figure across scenarios.
        """
        return self.final_net_worth - self.total_taxes_paid
    
    @property
    def total_end_age(self) -> int:
        """Age at end of strategy."""
        return self.client.current_age + (self.scenario.end_year - self.scenario.start_year)


# ---------------------------------------------------------------------------
# Project persistence (save / load)
# ---------------------------------------------------------------------------

def save_project(client: ClientProfile, accounts: List[Account],
                 income_streams: List[IncomeStream], expenses: Expenses,
                 filename: str) -> None:
    """Serialize the full analysis state to a JSON project file."""
    data = {
        "version": 1,
        "saved_at": datetime.now().isoformat(),
        "client": asdict(client),
        "accounts": [asdict(a) for a in accounts],
        "income_streams": [asdict(i) for i in income_streams],
        "expenses": asdict(expenses),
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)


def load_project(filename: str):
    """Load a project file. Returns (client, accounts, income_streams, expenses) or None on failure."""
    if not os.path.exists(filename):
        return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    try:
        client_data = data["client"]
        # current_age/spouse_current_age are computed in __post_init__; strip them
        client_data.pop("current_age", None)
        client_data.pop("spouse_current_age", None)
        client = ClientProfile(**client_data)

        accounts = [Account(**a) for a in data.get("accounts", [])]
        income_streams = [IncomeStream(**i) for i in data.get("income_streams", [])]
        expenses = Expenses(**data.get("expenses", {}))
    except (KeyError, TypeError, ValueError):
        return None

    return client, accounts, income_streams, expenses
