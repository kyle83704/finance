"""Self-contained HTML reports for Roth conversion analyses.

The report is a single HTML file with all styling, Penny's portrait and the
comparison chart embedded, so it can be emailed or opened offline without any
extra assets.
"""

from datetime import datetime
from html import escape
from typing import Any, List, Optional

from src import theme

YEAR_HEADINGS = (
    'Year', 'Age', 'Start pre-tax', 'RMD', 'Taxable SS', 'Conversion',
    'Income tax', 'Conversion tax', 'IRMAA', 'MAGI', 'IRMAA MAGI',
    'End Roth', 'Total tax',
)

_CSS = """
* { box-sizing: border-box; }
body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: "Segoe UI", "Aptos", "Helvetica Neue", Arial, sans-serif;
    line-height: 1.55;
}
.page { max-width: 1080px; margin: 0 auto; padding: 40px 28px 56px; }
.hero {
    display: flex; align-items: center; gap: 28px;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 24px; padding: 28px 32px;
    box-shadow: 0 12px 30px rgba(38, 70, 83, 0.07);
}
.mascot { width: 156px; height: 156px; flex: 0 0 auto; }
.eyebrow {
    margin: 0 0 6px; color: var(--teal); text-transform: uppercase;
    letter-spacing: 0.14em; font-size: 12px; font-weight: 800;
}
h1 { margin: 0; color: var(--navy); font-size: 34px; line-height: 1.2; }
.meta { margin: 8px 0 0; color: var(--muted); font-size: 14px; }
.lede { margin: 12px 0 0; max-width: 660px; font-size: 15px; }
h2 { margin: 38px 0 6px; color: var(--navy); font-size: 22px; }
.sub { margin: 0 0 16px; color: var(--muted); font-size: 14px; }
.cards {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
}
.card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 18px; padding: 18px 20px;
}
.card-label {
    margin: 0; color: var(--muted); font-size: 11px; font-weight: 800;
    letter-spacing: 0.08em; text-transform: uppercase;
}
.card-value { margin: 6px 0 2px; font-size: 26px; font-weight: 800; color: var(--teal); }
.card-name { margin: 0; color: var(--muted); font-size: 13px; }
.table-wrap {
    overflow-x: auto; background: var(--surface);
    border: 1px solid var(--border); border-radius: 16px;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
    background: var(--teal-soft); color: var(--navy); text-align: right;
    padding: 10px 12px; font-size: 11px; letter-spacing: 0.04em;
    text-transform: uppercase; white-space: nowrap;
}
th:first-child, th:nth-child(2) { text-align: left; }
td {
    padding: 9px 12px; text-align: right; white-space: nowrap;
    border-top: 1px solid var(--border);
}
td:first-child, td:nth-child(2) { text-align: left; white-space: normal; }
tbody tr:nth-child(even) { background: var(--stripe); }
.chart {
    display: block; width: 100%; max-width: 900px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 16px;
}
.strategy {
    margin: 12px 0; padding: 0 18px; background: var(--surface);
    border: 1px solid var(--border); border-radius: 16px;
}
summary {
    cursor: pointer; padding: 16px 0; color: var(--navy);
    font-weight: 700; font-size: 15px;
}
.strategy-meta { margin: 0 0 12px; color: var(--muted); font-size: 13px; }
.strategy .table-wrap { margin-bottom: 16px; }
.empty { color: var(--muted); font-style: italic; }
footer {
    margin-top: 42px; padding-top: 18px; border-top: 1px solid var(--border);
    color: var(--muted); font-size: 12px;
}
footer strong { color: var(--navy); }
@media print {
    body { background: #fff; }
    .page { max-width: none; padding: 0; }
    .hero, .card, .chart { box-shadow: none; }
    .strategy { break-inside: avoid; }
}
"""


def _money(value: Any) -> str:
    """Format a number as whole dollars, or an em dash when unavailable."""
    try:
        return f'${float(value):,.0f}'
    except (TypeError, ValueError):
        return '—'


def _filing_status_label(value: Any) -> str:
    return str(value or '—').replace('_', ' ').title()


def _metric_card(label: str, strategy: Any, accent: str) -> str:
    if label == 'Lowest lifetime tax':
        value = _money(strategy.total_taxes_paid)
    elif label == 'Largest Roth cushion':
        value = _money(strategy.final_roth_value)
    else:
        value = _money(strategy.final_net_worth)

    return (
        '<div class="card">'
        f'<p class="card-label">{escape(label)}</p>'
        f'<p class="card-value" style="color:{accent}">{value}</p>'
        f'<p class="card-name">{escape(str(strategy.scenario.name))}</p>'
        '</div>'
    )


def _comparison_from_strategies(strategies: List[Any]):
    columns = [
        'Strategy', 'Objective', 'Total conversions', 'Total taxes paid',
        'Total IRMAA costs', 'Final Roth value', 'Final pre-tax value',
        'Final taxable value', 'Final net worth',
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
        ])
    return columns, rows


def _comparison_table(strategies: List[Any], comparison_df: Any) -> str:
    if comparison_df is not None:
        columns = [str(column) for column in comparison_df.columns]
        rows = comparison_df.values.tolist()
    elif strategies:
        columns, rows = _comparison_from_strategies(strategies)
    else:
        columns, rows = ['Strategy'], []

    header = ''.join(f'<th>{escape(column)}</th>' for column in columns)
    if rows:
        body = ''.join(
            '<tr>' + ''.join(f'<td>{escape(str(cell))}</td>' for cell in row) + '</tr>'
            for row in rows
        )
    else:
        body = (f'<tr><td class="empty" colspan="{max(1, len(columns))}">'
                'No strategies were selected.</td></tr>')

    return (f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def _year_table(strategy: Any) -> str:
    rows = []
    for year in getattr(strategy, 'years', []) or []:
        rows.append([
            escape(str(getattr(year, 'year', ''))),
            escape(str(getattr(year, 'age', ''))),
            _money(getattr(year, 'start_balance_pretax', 0)),
            _money(getattr(year, 'rmd_required', 0)),
            _money(getattr(year, 'taxable_social_security', 0)),
            _money(getattr(year, 'recommended_conversion', 0)),
            _money(getattr(year, 'income_tax', 0)),
            _money(getattr(year, 'conversion_tax', 0)),
            _money(getattr(year, 'irmaa_impact', 0)),
            _money(getattr(year, 'magi', 0)),
            _money(getattr(year, 'irmaa_magi', 0)),
            _money(getattr(year, 'end_balance_roth', 0)),
            _money(getattr(year, 'total_tax_paid', 0)),
        ])

    if not rows:
        return '<p class="empty">No yearly detail was recorded.</p>'

    header = ''.join(f'<th>{label}</th>' for label in YEAR_HEADINGS)
    body = ''.join(
        '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
        for row in rows
    )
    return (f'<div class="table-wrap"><table><thead><tr>{header}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def build_html_report(client: Any, strategies: List[Any], comparison_df: Any = None,
                      chart_png: Optional[bytes] = None,
                      mascot_data_uri: Optional[str] = None,
                      generated_at: Any = None) -> str:
    """Build a complete, self-contained HTML report.

    ``comparison_df`` is optional; when omitted the comparison table is built
    from the strategy objects.  ``generated_at`` may be a datetime or a string
    (useful for deterministic tests).
    """
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

    best_net = max(strategies, key=lambda s: s.final_net_worth) if strategies else None
    thrifty = min(
        strategies,
        key=lambda s: s.total_taxes_paid,
    ) if strategies else None
    roth_rich = max(strategies, key=lambda s: s.final_roth_value) if strategies else None

    cards = []
    if best_net is not None:
        cards.append(_metric_card('Best final net worth', best_net, theme.TEAL))
    if thrifty is not None:
        cards.append(_metric_card('Lowest lifetime tax', thrifty, theme.CORAL))
    if roth_rich is not None:
        cards.append(_metric_card('Largest Roth cushion', roth_rich, theme.BLUE))

    details = []
    for index, strategy in enumerate(strategies):
        years = getattr(strategy, 'years', []) or []
        span = ''
        if years:
            span = f'{years[0].year}–{years[-1].year} · '
        details.append(
            f'<details{" open" if index == 0 else ""}>'
            f'<summary>{escape(str(strategy.scenario.name))}</summary>'
            f'<p class="strategy-meta">'
            f'{escape(str(strategy.scenario.target_objective))} · {span}'
            f'Final net worth {_money(strategy.final_net_worth)} · '
            f'Lifetime tax {_money(strategy.total_taxes_paid)}'
            f'</p>'
            f'{_year_table(strategy)}'
            f'</details>'
        )

    chart_html = ''
    if chart_png:
        import base64
        encoded = base64.b64encode(chart_png).decode('ascii')
        chart_html = (
            '<h2>The picture</h2>'
            '<p class="sub">Final net worth by strategy. The gold bar is '
            'Penny’s pick.</p>'
            f'<img class="chart" src="data:image/png;base64,{encoded}" '
            'alt="Bar chart comparing final net worth by strategy">'
        )

    mascot_html = (
        f'<img class="mascot" src="{mascot_data_uri}" '
        'alt="Penny the planning pig">'
        if mascot_data_uri else ''
    )

    plural = 'strategy' if len(strategies) == 1 else 'strategies'
    at_a_glance = ''.join(cards) or (
        '<p class="empty">No strategies were selected.</p>'
    )
    detail_html = ''.join(details) or (
        '<p class="empty">No yearly detail was recorded.</p>'
    )

    return f"""<!doctype html>
<html lang="en" style="--bg: {theme.BG}; --surface: {theme.SURFACE}; --text: {theme.TEXT}; --muted: {theme.MUTED_TEXT}; --navy: {theme.NAVY}; --teal: {theme.TEAL}; --teal-soft: {theme.TEAL_SOFT}; --coral: {theme.CORAL}; --border: {theme.BORDER}; --stripe: #FFFBF5;">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(client_name)} · Roth Conversion Plan</title>
<style>{_CSS}</style>
</head>
<body>
<main class="page">
<header class="hero">
{mascot_html}
<div>
<p class="eyebrow">Penny’s Roth conversion plan</p>
<h1>{escape(client_name)}</h1>
<p class="meta">{escape(str(getattr(client, 'state_residence', '—')))} · {escape(_filing_status_label(getattr(client, 'filing_status', '')))} · Generated {escape(date_label)}</p>
<p class="lede">A friendly look at {len(strategies)} conversion {plural}, with the trade-offs, taxes and year-by-year balances laid out side by side.</p>
</div>
</header>

<h2>At a glance</h2>
<p class="sub">Three ways to judge the plan: growth, tax cost and Roth cushion.</p>
<div class="cards">{at_a_glance}</div>

<h2>Strategy comparison</h2>
<p class="sub">Every objective you selected, compared on the same inputs.</p>
{_comparison_table(strategies, comparison_df)}

{chart_html}

<h2>Year-by-year detail</h2>
<p class="sub">Open a strategy to see the annual conversion, tax and balance path.</p>
{detail_html}

<footer>
<p><strong>Educational estimate, not tax advice.</strong> This report models a simplified set of federal and state rules, assumes steady growth and does not account for market volatility or future law changes. Confirm any conversion with a qualified tax professional.</p>
<p>Made with care by Penny · Roth Conversion Simulator</p>
</footer>
</main>
</body>
</html>
"""


def write_html_report(filename: str, html_text: str) -> None:
    """Write a report as UTF-8 so names and punctuation survive."""
    with open(filename, 'w', encoding='utf-8') as handle:
        handle.write(html_text)
