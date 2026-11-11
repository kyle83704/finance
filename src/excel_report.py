"""Excel workbooks for Roth conversion analyses.

The workbook contains a summary, the strategy comparison, one year-by-year
sheet per strategy and an embedded PNG chart.  openpyxl is already a project
dependency, so this adds no new package.
"""

from datetime import datetime
from io import BytesIO
import re
from typing import Any, List, Optional

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src import theme


TITLE_FONT = Font(size=16, bold=True, color=theme.NAVY.lstrip('#'))
MUTED_FONT = Font(size=10, color=theme.MUTED_TEXT.lstrip('#'))
HEADER_FONT = Font(bold=True, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor=theme.TEAL.lstrip('#'))
SECTION_FILL = PatternFill('solid', fgColor=theme.TEAL_SOFT.lstrip('#'))
MONEY_FORMAT = '$#,##0'


def _money(value: Any) -> str:
    try:
        return f'${float(value):,.0f}'
    except (TypeError, ValueError):
        return '—'


def _comparison_rows(strategies: List[Any], comparison_df: Any):
    if comparison_df is not None:
        return (
            [str(column) for column in comparison_df.columns],
            comparison_df.values.tolist(),
        )

    columns = [
        'Strategy', 'Objective', 'Total Conversions', 'Total Taxes Paid',
        'Total IRMAA Costs', 'Final Roth Value', 'Final Pre-tax Value',
        'Final Taxable Value', 'Final Net Worth', 'Net After All Taxes',
    ]
    rows = []
    for strategy in strategies:
        rows.append([
            strategy.scenario.name,
            strategy.scenario.target_objective,
            _money(strategy.total_conversions),
            _money(strategy.total_taxes_paid),
            _money(strategy.total_irmaa_costs),
            _money(strategy.final_roth_value),
            _money(strategy.final_pretax_value),
            _money(strategy.final_taxable_value),
            _money(strategy.final_net_worth),
            _money(strategy.final_after_tax_net_worth),
        ])
    return columns, rows


def _style_header(sheet, row: int, columns: int) -> None:
    for column in range(1, columns + 1):
        cell = sheet.cell(row=row, column=column)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center')


def _safe_sheet_name(name: str, used: set) -> str:
    cleaned = re.sub(r'[\\/*?:\[\]]', '_', str(name)).strip() or 'Strategy'
    cleaned = cleaned[:31]
    candidate = cleaned
    suffix = 2
    while candidate in used:
        tail = f' ({suffix})'
        candidate = cleaned[:31 - len(tail)] + tail
        suffix += 1
    used.add(candidate)
    return candidate


def _autosize(sheet, widths: dict) -> None:
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width


def build_excel_report(client: Any, strategies: List[Any],
                       comparison_df: Any = None,
                       chart_png: Optional[bytes] = None,
                       generated_at: Any = None) -> bytes:
    """Build an .xlsx workbook and return it as bytes."""
    strategies = list(strategies or [])
    if isinstance(generated_at, datetime):
        date_label = generated_at.strftime('%B %d, %Y')
    elif generated_at:
        date_label = str(generated_at)
    else:
        date_label = datetime.now().strftime('%B %d, %Y')

    client_name = ' '.join(
        part for part in (
            getattr(client, 'first_name', ''),
            getattr(client, 'last_name', ''),
        ) if part
    ) or 'Your plan'

    workbook = Workbook()
    summary = workbook.active
    summary.title = 'Summary'
    summary['A1'] = 'Roth Conversion Plan'
    summary['A1'].font = TITLE_FONT
    summary.merge_cells('A1:D1')
    summary['A3'] = 'Client'
    summary['B3'] = client_name
    summary['A4'] = 'State / filing status'
    summary['B4'] = (
        f"{getattr(client, 'state_residence', '—')} · "
        f"{str(getattr(client, 'filing_status', '—')).replace('_', ' ').title()}"
    )
    summary['A5'] = 'Generated'
    summary['B5'] = date_label
    for row in (3, 4, 5):
        summary.cell(row=row, column=1).font = Font(bold=True)

    best_net = max(strategies, key=lambda s: s.final_net_worth) if strategies else None
    thrifty = min(strategies, key=lambda s: s.total_taxes_paid) if strategies else None
    roth_rich = max(strategies, key=lambda s: s.final_roth_value) if strategies else None

    summary['A7'] = 'At a glance'
    summary['A7'].font = Font(size=12, bold=True, color=theme.NAVY.lstrip('#'))
    summary['A8'] = 'Metric'
    summary['B8'] = 'Strategy'
    summary['C8'] = 'Value'
    _style_header(summary, 8, 3)

    highlights = [
        ('Best final net worth', best_net,
         best_net.final_net_worth if best_net else None),
        ('Lowest lifetime tax', thrifty,
         thrifty.total_taxes_paid if thrifty else None),
        ('Largest Roth cushion', roth_rich,
         roth_rich.final_roth_value if roth_rich else None),
    ]
    row = 9
    for label, strategy, value in highlights:
        summary.cell(row=row, column=1, value=label)
        summary.cell(row=row, column=2, value=(
            strategy.scenario.name if strategy else 'No strategies selected'
        ))
        summary.cell(row=row, column=3, value=value)
        if value is not None:
            summary.cell(row=row, column=3).number_format = MONEY_FORMAT
        row += 1

    summary['A13'] = 'Method notes'
    summary['A13'].font = Font(size=12, bold=True, color=theme.NAVY.lstrip('#'))
    notes = [
        'Taxes combine progressive 2026 federal brackets with a simplified flat state rate.',
        'Conversion tax is the incremental tax caused by the conversion, not the full income tax.',
        'RMDs start at 73 and are withdrawn before any voluntary Roth conversion.',
        'IRMAA is an annual Medicare surcharge and applies at age 65+.',
        'Expenses are planning context; portfolio withdrawals for spending are not modelled.',
        'Educational estimate only—not tax or investment advice.',
    ]
    for index, note in enumerate(notes, start=14):
        summary.cell(row=index, column=1, value=note)
        summary.cell(row=index, column=1).font = MUTED_FONT
        summary.merge_cells(start_row=index, start_column=1,
                            end_row=index, end_column=6)
    _autosize(summary, {'A': 38, 'B': 34, 'C': 18, 'D': 18, 'E': 18, 'F': 18})

    comparison = workbook.create_sheet('Comparison')
    columns, rows = _comparison_rows(strategies, comparison_df)
    comparison.append(columns)
    _style_header(comparison, 1, len(columns))
    for delta_row in rows:
        comparison.append(list(delta_row))
    comparison.freeze_panes = 'A2'
    comparison.auto_filter.ref = comparison.dimensions
    _autosize(comparison, {get_column_letter(i + 1): 24
                           for i in range(len(columns))})

    used_names = {summary.title, comparison.title}
    for strategy in strategies:
        sheet = workbook.create_sheet(
            _safe_sheet_name(strategy.scenario.name, used_names)
        )
        sheet['A1'] = strategy.scenario.name
        sheet['A1'].font = TITLE_FONT
        sheet.merge_cells('A1:D1')
        sheet['A3'] = 'Objective'
        sheet['B3'] = strategy.scenario.target_objective
        sheet['A4'] = 'Period'
        sheet['B4'] = f'{strategy.scenario.start_year}–{strategy.scenario.end_year}'
        sheet['A5'] = 'Final net worth'
        sheet['B5'] = strategy.final_net_worth
        sheet['B5'].number_format = MONEY_FORMAT
        sheet['A6'] = 'Lifetime tax'
        sheet['B6'] = strategy.total_taxes_paid
        sheet['B6'].number_format = MONEY_FORMAT

        headers = [
            'Year', 'Age', 'Start Pre-tax', 'RMD', 'Conversion',
            'Income Tax', 'Conversion Tax', 'IRMAA', 'End Pre-tax',
            'End Roth', 'End Taxable', 'Total Tax',
        ]
        header_row = 8
        for column, header in enumerate(headers, start=1):
            sheet.cell(row=header_row, column=column, value=header)
        _style_header(sheet, header_row, len(headers))

        for offset, year in enumerate(getattr(strategy, 'years', []) or [], start=1):
            values = [
                year.year, year.age, year.start_balance_pretax,
                year.rmd_required, year.recommended_conversion,
                year.income_tax, year.conversion_tax, year.irmaa_impact,
                year.end_balance_pretax, year.end_balance_roth,
                year.end_balance_taxable, year.total_tax_paid,
            ]
            for column, value in enumerate(values, start=1):
                cell = sheet.cell(row=header_row + offset, column=column,
                                  value=value)
                if column >= 3:
                    cell.number_format = MONEY_FORMAT

        sheet.freeze_panes = f'A{header_row + 1}'
        _autosize(sheet, {get_column_letter(i + 1): 17
                          for i in range(len(headers))})

    if chart_png:
        chart_sheet = workbook.create_sheet('Chart')
        image = XLImage(BytesIO(chart_png))
        image.width = 920
        image.height = 390
        chart_sheet.add_image(image, 'A1')

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def write_excel_report(filename: str, payload: bytes) -> None:
    """Write the workbook bytes to ``filename``."""
    with open(filename, 'wb') as handle:
        handle.write(payload)
