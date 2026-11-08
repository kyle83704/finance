"""Constants for Roth conversion simulator."""

# Federal tax brackets for 2026 (example - will be parameterized)
FEDERAL_TAX_BRACKETS_2026 = {
    "single": [
        (0, 11600, 0.10),
        (11600, 47150, 0.12),
        (47150, 100525, 0.22),
        (100525, 191950, 0.24),
        (191950, 243725, 0.32),
        (243725, 609350, 0.35),
        (609350, float('inf'), 0.37),
    ],
    "married_filing_jointly": [
        (0, 23200, 0.10),
        (23200, 94300, 0.12),
        (94300, 201050, 0.22),
        (201050, 383900, 0.24),
        (383900, 487450, 0.32),
        (487450, 731200, 0.35),
        (731200, float('inf'), 0.37),
    ],
}

# 2026 Standard deductions
STANDARD_DEDUCTION_2026 = {
    "single": 14600,
    "married_filing_jointly": 29200,
    "married_filing_separately": 14600,
    "head_of_household": 21900,
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

# IRMAA brackets for 2026 (Medicare Part B/D premiums)
# Format: (income_threshold, monthly_adjustment)
IRMAA_BRACKETS_2026 = {
    "single": [
        (0, 0),           # Tier 1: MAGI $0-$97k
        (97000, 70),      # Tier 2: MAGI $97k-$123k
        (123000, 175),    # Tier 3: MAGI $123k-$153k
        (153000, 280),    # Tier 4: MAGI $153k-$183k
        (183000, 385),    # Tier 5: MAGI $183k+
    ],
    "married_filing_jointly": [
        (0, 0),           # Tier 1: MAGI $0-$194k
        (194000, 70),     # Tier 2: MAGI $194k-$246k
        (246000, 175),    # Tier 3: MAGI $246k-$306k
        (306000, 280),    # Tier 4: MAGI $306k-$366k
        (366000, 385),    # Tier 5: MAGI $366k+
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

# RMD age threshold
RMD_START_AGE = 73  # As of 2023 (was 72 before)

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
    "403(b)",
    "Taxable Brokerage",
    "HSA",
    "Pension",
]

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
