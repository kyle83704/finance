"""Tests for the self-contained HTML report builder."""

import base64
import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace

from src.reports import build_html_report, write_html_report


def _client(first='Ada', last='Lovelace'):
    return SimpleNamespace(
        first_name=first,
        last_name=last,
        state_residence='OR',
        filing_status='married_filing_jointly',
    )


def _year(year=2026, age=66):
    return SimpleNamespace(
        year=year,
        age=age,
        start_balance_pretax=500000.0,
        rmd_required=0.0,
        recommended_conversion=50000.0,
        income_tax=3000.0,
        conversion_tax=12000.0,
        irmaa_impact=500.0,
        end_balance_roth=400000.0,
        total_tax_paid=12500.0,
    )


def _strategy(name, net_worth, taxes, irmaa, roth,
              objective='Balanced Growth'):
    return SimpleNamespace(
        scenario=SimpleNamespace(name=name, target_objective=objective),
        final_net_worth=net_worth,
        total_taxes_paid=taxes,
        total_irmaa_costs=irmaa,
        final_roth_value=roth,
        final_pretax_value=100000.0,
        final_taxable_value=50000.0,
        total_conversions=75000.0,
        years=[_year(), _year(2027, 67)],
    )


class TestHtmlReport(unittest.TestCase):

    def setUp(self):
        self.strategies = [
            _strategy('Steady Saver', 2_000_000, 40_000, 2_000, 900_000),
            _strategy('Bold Converter', 2_400_000, 90_000, 8_000, 1_300_000,
                      objective='Maximize Roth Value'),
        ]

    def test_contains_client_strategies_and_yearly_detail(self):
        html = build_html_report(
            _client(), self.strategies,
            generated_at=datetime(2026, 11, 11),
        )
        self.assertIn('Ada Lovelace', html)
        self.assertIn('Steady Saver', html)
        self.assertIn('Bold Converter', html)
        self.assertIn('November 11, 2026', html)
        self.assertIn('2027', html)
        self.assertIn('$2,400,000', html)
        self.assertIn('Year-by-year detail', html)

    def test_metric_cards_pick_the_right_strategies(self):
        html = build_html_report(_client(), self.strategies,
                                 generated_at='test day')
        lowest_tax_section = html.split('Lowest lifetime tax', 1)[1][:500]
        self.assertIn('Steady Saver', lowest_tax_section)
        best_net_section = html.split('Best final net worth', 1)[1][:500]
        self.assertIn('Bold Converter', best_net_section)
        roth_section = html.split('Largest Roth cushion', 1)[1][:500]
        self.assertIn('Bold Converter', roth_section)

    def test_lifetime_tax_card_uses_total_taxes_paid_once(self):
        html = build_html_report(_client(), self.strategies,
                                 generated_at='today')
        lowest_tax_section = html.split('Lowest lifetime tax', 1)[1][:500]
        self.assertIn('$40,000', lowest_tax_section)
        self.assertNotIn('$42,000', lowest_tax_section)

    def test_rules_registry_is_in_the_audit_trail(self):
        html = build_html_report(_client(), self.strategies,
                                 generated_at='today')
        self.assertIn('Rules and assumptions', html)
        self.assertIn('Registry 2026.1', html)
        self.assertIn('2026 federal ordinary income brackets', html)
        self.assertIn('assumption', html)
        self.assertIn('unsupported', html)

    def test_untrusted_names_are_html_escaped(self):
        strategies = [
            _strategy('<script>alert(1)</script>', 1_000_000, 1_000, 0, 1),
        ]
        html = build_html_report(_client('<b>Ada</b>', 'Lovelace'), strategies,
                                 generated_at='today')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;b&gt;Ada&lt;/b&gt;', html)

    def test_chart_and_mascot_are_embedded(self):
        chart_png = b'\x89PNG\r\n\x1a\nfake'
        html = build_html_report(
            _client(), self.strategies,
            chart_png=chart_png,
            mascot_data_uri='data:image/png;base64,AAAA',
            generated_at='today',
        )
        expected = base64.b64encode(chart_png).decode('ascii')
        self.assertIn(f'data:image/png;base64,{expected}', html)
        self.assertIn('src="data:image/png;base64,AAAA"', html)
        self.assertIn('The picture', html)

    def test_chart_and_mascot_are_optional(self):
        html = build_html_report(_client(), self.strategies,
                                 generated_at='today')
        self.assertNotIn('The picture', html)
        self.assertNotIn('class="mascot"', html)

    def test_empty_strategy_list_is_still_valid_report(self):
        html = build_html_report(_client(), [], generated_at='today')
        self.assertIn('No strategies were selected.', html)
        self.assertIn('At a glance', html)

    def test_write_html_report_round_trips_utf8(self):
        html = build_html_report(_client(), self.strategies,
                                 generated_at='today')
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'report.html')
            write_html_report(path, html)
            with open(path, 'r', encoding='utf-8') as handle:
                written = handle.read()
        self.assertEqual(written, html)
        self.assertIn('Penny’s Roth conversion plan', written)


if __name__ == '__main__':
    unittest.main()
