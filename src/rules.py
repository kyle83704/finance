"""Versioned tax-rule and assumption registry.

The calculator still consumes the numeric tables in ``constants.py``; this
module records what each table is, where it came from, and whether it is
verified law or a planning assumption.  It is deliberately conservative: a
rule is marked ``verified`` only for 2026 federal/IRMAA items checked against
the cited official sources.  State support and future-year indexing are marked
as limitations, not law.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

REGISTRY_VERSION = "2026.1"


@dataclass(frozen=True)
class RuleRecord:
    """Provenance and implementation status for one tax rule."""

    rule_id: str
    name: str
    jurisdiction: str
    tax_year: Optional[int]
    filing_status: str
    effective_date: str
    expiration_date: Optional[str]
    source_title: str
    source_url: str
    retrieved_date: str
    reference: str
    status: str  # verified, assumption, unsupported, proposed
    limitations: str = ""


_FEDERAL_URL = (
    "https://www.irs.gov/pub/irs-drop/rp-25-32.pdf"
)
_INFLATION_URL = (
    "https://www.irs.gov/newsroom/irs-releases-tax-inflation-adjustments-"
    "for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill"
)
_CMS_URL = (
    "https://www.cms.gov/newsroom/fact-sheets/"
    "2026-medicare-parts-b-premiums-deductibles"
)
_SS_URL = "https://www.irs.gov/publications/p915"
_RMD_URL = (
    "https://www.irs.gov/retirement-plans/plan-participant-employee/"
    "retirement-topics-required-minimum-distributions-rmds"
)

RETRIEVED = "2026-11-11"


RULE_REGISTRY: List[RuleRecord] = [
    RuleRecord(
        rule_id="federal_brackets_2026_single",
        name="2026 federal ordinary income brackets — single",
        jurisdiction="US",
        tax_year=2026,
        filing_status="single",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_title="IRS Revenue Procedure 2025-32",
        source_url=_FEDERAL_URL,
        retrieved_date=RETRIEVED,
        reference="Section 4.01, Table 1",
        status="verified",
        limitations="2026 only; later years use a planning assumption.",
    ),
    RuleRecord(
        rule_id="federal_brackets_2026_mfj",
        name="2026 federal ordinary income brackets — married filing jointly",
        jurisdiction="US",
        tax_year=2026,
        filing_status="married_filing_jointly",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_title="IRS Revenue Procedure 2025-32",
        source_url=_FEDERAL_URL,
        retrieved_date=RETRIEVED,
        reference="Section 4.01, Table 1",
        status="verified",
        limitations="2026 only; later years use a planning assumption.",
    ),
    RuleRecord(
        rule_id="standard_deduction_2026",
        name="2026 standard deduction and age-65 additional amount",
        jurisdiction="US",
        tax_year=2026,
        filing_status="single, married_filing_jointly",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_title="IRS 2026 inflation adjustments",
        source_url=_INFLATION_URL,
        retrieved_date=RETRIEVED,
        reference="Standard deduction section",
        status="verified",
        limitations=(
            "Additional amount modeled for age 65+; blind status and itemized "
            "deductions are not modeled."
        ),
    ),
    RuleRecord(
        rule_id="ltcg_qualified_dividends_2026",
        name="2026 0/15/20% long-term capital gain and qualified-dividend breakpoints",
        jurisdiction="US",
        tax_year=2026,
        filing_status="single, married_filing_jointly, married_filing_separately, head_of_household",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_title="IRS Revenue Procedure 2025-32",
        source_url=_FEDERAL_URL,
        retrieved_date=RETRIEVED,
        reference="Section 4.03, Maximum Capital Gains Rate",
        status="verified",
        limitations="Only long-term gains/qualified dividends; short-term gains use ordinary rates.",
    ),
    RuleRecord(
        rule_id="irmaa_2026",
        name="2026 Medicare Part B and Part D IRMAA tiers",
        jurisdiction="US",
        tax_year=2026,
        filing_status="single, married_filing_jointly",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_title="CMS 2026 Medicare Parts A & B premiums and deductibles",
        source_url=_CMS_URL,
        retrieved_date=RETRIEVED,
        reference="2026 Part B premium and IRMAA table",
        status="verified",
        limitations=(
            "Combines Part B and Part D surcharges per person; Part D base "
            "premiums and Medicare Advantage costs are not modeled."
        ),
    ),
    RuleRecord(
        rule_id="social_security_provisional_income",
        name="Social Security provisional-income inclusion thresholds",
        jurisdiction="US",
        tax_year=None,
        filing_status="single, head_of_household, married_filing_jointly",
        effective_date="statutory",
        expiration_date=None,
        source_title="IRS Publication 915",
        source_url=_SS_URL,
        retrieved_date=RETRIEVED,
        reference="Social Security benefits worksheet",
        status="verified",
        limitations=(
            "Tax-exempt interest is accepted by the calculator API but the "
            "desktop simulator does not supply it."
        ),
    ),
    RuleRecord(
        rule_id="rmd_secure_2_ages",
        name="SECURE 2.0 RMD start ages and Uniform Lifetime divisors",
        jurisdiction="US",
        tax_year=None,
        filing_status="all",
        effective_date="2023-01-01",
        expiration_date=None,
        source_title="IRS Required Minimum Distributions guidance",
        source_url=_RMD_URL,
        retrieved_date=RETRIEVED,
        reference="SECURE 2.0 RMD age rules; IRS Uniform Lifetime Table",
        status="verified",
        limitations=(
            "Divisor table currently ends at age 100; QCDs and account-specific "
            "aggregation rules are not modeled."
        ),
    ),
    RuleRecord(
        rule_id="state_tax_flat_rate",
        name="Flat state tax approximation",
        jurisdiction="US states and DC",
        tax_year=2026,
        filing_status="all",
        effective_date="implementation-specific",
        expiration_date=None,
        source_title="Not verified against state revenue guidance",
        source_url="",
        retrieved_date=RETRIEVED,
        reference="STATE_TAX_RATES",
        status="assumption",
        limitations=(
            "Flat-rate approximation only. No progressive brackets, state "
            "deductions, credits, retirement exclusions, local taxes or "
            "residency/sourcing rules. Do not present as a state return."
        ),
    ),
    RuleRecord(
        rule_id="post_2026_indexing",
        name="2.5% annual indexing assumption after 2026",
        jurisdiction="US",
        tax_year=None,
        filing_status="all",
        effective_date="2027-01-01",
        expiration_date=None,
        source_title="Planning assumption; future IRS tables are not published",
        source_url="",
        retrieved_date=RETRIEVED,
        reference="TAX_BRACKET_INFLATION_RATE",
        status="assumption",
        limitations="Not a legal forecast; actual indexing will differ by year and provision.",
    ),
    RuleRecord(
        rule_id="obbba_senior_deduction",
        name="Temporary OBBBA senior deduction",
        jurisdiction="US",
        tax_year=2026,
        filing_status="all",
        effective_date="2025-01-01",
        expiration_date="2028-12-31",
        source_title="IRS 2026 inflation adjustments / OBBBA guidance",
        source_url=_INFLATION_URL,
        retrieved_date=RETRIEVED,
        reference="Senior deduction provisions",
        status="unsupported",
        limitations="Not implemented; eligibility, phaseout and interaction with deductions require review.",
    ),
    RuleRecord(
        rule_id="mfs_hoh_federal_brackets",
        name="Married-filing-separately and head-of-household federal brackets",
        jurisdiction="US",
        tax_year=2026,
        filing_status="married_filing_separately, head_of_household",
        effective_date="2026-01-01",
        expiration_date="2026-12-31",
        source_title="IRS Revenue Procedure 2025-32",
        source_url=_FEDERAL_URL,
        retrieved_date=RETRIEVED,
        reference="Section 4.01 tax rate tables",
        status="unsupported",
        limitations=(
            "The maintained GUI exposes only single and MFJ. Direct API use of "
            "MFS or HOH currently returns zero federal ordinary tax."
        ),
    ),
    RuleRecord(
        rule_id="taxable_account_capital_gains",
        name="Taxable-account realized capital gains and basis",
        jurisdiction="US",
        tax_year=None,
        filing_status="all",
        effective_date="implementation-specific",
        expiration_date=None,
        source_title="IRS capital gains guidance",
        source_url=_FEDERAL_URL,
        retrieved_date=RETRIEVED,
        reference="Section 4.03 (rates); basis rules not yet fully modeled",
        status="assumption",
        limitations=(
            "Cost basis is tracked and sales realize gains, but short-term "
            "gains, wash sales, carryforwards, NIIT and state conformity are "
            "not modeled."
        ),
    ),
]


def get_rules(status: Optional[str] = None) -> List[RuleRecord]:
    """Return all rules, optionally filtered by implementation status."""
    if status is None:
        return list(RULE_REGISTRY)
    return [rule for rule in RULE_REGISTRY if rule.status == status]


def get_rule(rule_id: str) -> Optional[RuleRecord]:
    """Return one rule by ID, or ``None``."""
    return next((rule for rule in RULE_REGISTRY if rule.rule_id == rule_id), None)


def registry_summary() -> Dict[str, int]:
    """Count rules by status for diagnostics and reports."""
    summary: Dict[str, int] = {}
    for rule in RULE_REGISTRY:
        summary[rule.status] = summary.get(rule.status, 0) + 1
    return summary
