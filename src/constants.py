"""Constants for Roth conversion simulator."""

# Federal tax brackets for 2026 (IRS Rev. Proc. 2025-32)
FEDERAL_TAX_BRACKETS_2026 = {
    "single": [
        (0, 12400, 0.10),
        (12400, 50400, 0.12),
        (50400, 105700, 0.22),
        (105700, 201775, 0.24),
        (201775, 256225, 0.32),
        (256225, 640600, 0.35),
        (640600, float('inf'), 0.37),
    ],
    "married_filing_jointly": [
        (0, 24800, 0.10),
        (24800, 100800, 0.12),
        (100800, 211400, 0.22),
        (211400, 403550, 0.24),
        (403550, 512450, 0.32),
        (512450, 768700, 0.35),
        (768700, float('inf'), 0.37),
    ],
}

# 2026 standard deductions
STANDARD_DEDUCTION_2026 = {
    "single": 16100,
    "married_filing_jointly": 32200,
    "married_filing_separately": 16100,
    "head_of_household": 24150,
}

# Additional standard deduction for taxpayers 65 or older (2026).  For MFJ
# this is per qualifying spouse, so a couple where both are 65+ gets twice the
# married amount.
ADDITIONAL_STANDARD_DEDUCTION_2026 = {
    "single": 2050,
    "married_filing_jointly": 1650,
    "married_filing_separately": 1650,
    "head_of_household": 2050,
}

# Planning assumption used to index brackets, deductions, LTCG thresholds and
# IRMAA thresholds after 2026.  The IRS does not publish future-year tables.
TAX_BRACKET_INFLATION_RATE = 0.025

# 2026 maximum 0% and 15% rates for long-term capital gains and qualified
# dividends (IRS Rev. Proc. 2025-32, section 4.03).
LTCG_BRACKETS_2026 = {
    "single": [
        (0, 49450, 0.00),
        (49450, 545500, 0.15),
        (545500, float('inf'), 0.20),
    ],
    "married_filing_jointly": [
        (0, 98900, 0.00),
        (98900, 613700, 0.15),
        (613700, float('inf'), 0.20),
    ],
    "married_filing_separately": [
        (0, 49450, 0.00),
        (49450, 306850, 0.15),
        (306850, float('inf'), 0.20),
    ],
    "head_of_household": [
        (0, 66200, 0.00),
        (66200, 579600, 0.15),
        (579600, float('inf'), 0.20),
    ],
}

# State income tax rates (simplified - single rate, not progressive)
STATE_TAX_RATES = {
    "AL": 0.00, "AK": 0.00, "AZ": 0.04, "AR": 0.00,
    "CA": 0.093, "CO": 0.04, "CT": 0.06, "DE": 0.065,
    "FL": 0.00, "GA": 0.055, "HI": 0.085, "ID": 0.05,
    "IL": 0.04, "IN": 0.03, "IA": 0.057, "KS": 0.057,
    "KY": 0.05, "LA": 0.055, "ME": 0.075, "MD": 0.0575,
    "MA": 0.05, "MI": 0.04, "MN": 0.0985, "MS": 0.05,
    "MO": 0.055, "MT": 0.065, "NE": 0.06, "NV": 0.00,
    "NH": 0.00, "NJ": 0.0875, "NM": 0.049, "NY": 0.0685,
    "NC": 0.04, "ND": 0.029, "OH": 0.04, "OK": 0.05,
    "OR": 0.099, "PA": 0.0307, "RI": 0.063, "SC": 0.07,
    "SD": 0.00, "TN": 0.00, "TX": 0.00, "UT": 0.04,
    "VT": 0.065, "VA": 0.0575, "WA": 0.00, "WV": 0.065,
    "WI": 0.0685, "WY": 0.00, "DC": 0.08,
}

# 2026 IRMAA brackets, combining Part B and Part D surcharges per person.
# Format: (income_threshold, monthly_adjustment).  The threshold is the top of
# the no-surcharge tier; higher tiers run through the next threshold.  At the
# top tier the threshold is inclusive, matching CMS ($500k single/$750k MFJ).
IRMAA_BRACKETS_2026 = {
    "single": [
        (0, 0.00),          # up to $109k
        (109000, 95.70),    # Part B $81.20 + Part D $14.50
        (137000, 240.40),   # Part B $202.90 + Part D $37.50
        (171000, 385.00),   # Part B $324.60 + Part D $60.40
        (205000, 529.60),   # Part B $446.30 + Part D $83.30
        (500000, 578.00),   # Part B $487.00 + Part D $91.00
    ],
    "married_filing_jointly": [
        (0, 0.00),          # up to $218k
        (218000, 95.70),
        (274000, 240.40),
        (342000, 385.00),
        (410000, 529.60),
        (750000, 578.00),
    ],
}

# RMD multipliers by age (IRS Uniform Lifetime Table)
RMD_AGE_MULTIPLIERS = {
    72: 27.4, 73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9,
    78: 22.0, 79: 21.1, 80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7,
    84: 16.8, 85: 16.0, 86: 15.1, 87: 14.3, 88: 13.4, 89: 12.7,
    90: 11.9, 91: 11.1, 92: 10.4, 93: 9.6, 94: 8.9, 95: 8.2,
    96: 7.6, 97: 7.1, 98: 6.5, 99: 6.0, 100: 5.5,
}

# RMD age thresholds (SECURE 2.0)
RMD_START_AGE = 73  # Born 1951-1959; also the legacy default
RMD_START_AGE_1960_PLUS = 75  # Born 1960 or later

# Roth conversion rules
ROTH_CONVERSION_RULES = {
    "pro_rata_rule": True,  # Mix of pre-tax and after-tax contributions in denominator
    "five_year_rule": True,  # Each conversion has its own 5-year holding period
    "death_exception": True, # No 10% penalty if converted amount needed before 59.5
}

# Account types
ACCOUNT_TYPES = [
    "Traditional IRA",
    "Roth IRA",
    "SEP IRA",
    "Solo 401(k)",
    "Employer 401(k)",
    "401(k)",
    "403(b)",
    "Roth 401(k)",
    "Taxable Brokerage",
    "HSA",
    "Pension",
]

# Account groups used consistently by the simulator.  Keeping these here stops
# the GUI, simulator and reporting layers from disagreeing about what counts
# as a pre-tax or Roth account (for example "Employer 401(k)" vs "401(k)").
PRETAX_ACCOUNT_TYPES = (
    "Traditional IRA",
    "SEP IRA",
    "Solo 401(k)",
    "Employer 401(k)",
    "401(k)",
    "403(b)",
)
ROTH_ACCOUNT_TYPES = ("Roth IRA", "Roth 401(k)")
TAXABLE_ACCOUNT_TYPES = ("Taxable Brokerage",)

# Medicare / IRMAA timing
MEDICARE_AGE = 65
IRMAA_LOOKBACK_YEARS = 2

# Optimization objectives
OBJECTIVES = [
    "Maximize Inheritance",
    "Maximize Gross Net Worth",
    "Maximize Roth Value",
    "Minimize Tax Paid",
    "Minimize IRMAA Impact",
    "Balanced Growth",
]

# Social Security claiming strategies
SS_CLAIM_AGES = [62, 63, 64, 65, 66, 67, 68, 69, 70]
