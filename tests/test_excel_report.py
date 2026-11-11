"""Tests for the Excel report export."""

from datetime import datetime
from io import BytesIO
import os
import tempfile
import unittest
from types import SimpleNamespace

from openpyxl import load_workbook

from src.excel_report import build_excel_report, write_excel_report
from src.mascot import mascot_png


def _client():
    return SimpleNamespace(
        first_name='Ada', last_name='Lovelace', state_residence='OR',
        filing_status='married_filing_jointly',
    )


def _year(year=2026, age=66):
    return SimpleNamespace(
        year=year, age=age,
        start_balance_pretax=500000.0,
        rmd_required=0.0,
        recommended_conversion=50000.0,
        income_tax=3000.0,
        conversion_tax=12000.0,
        irmaa_impact=500.0,
        end_balance_pretax=450000.0,
        end_balance_roth=400000.0,
        end_balance_taxable=50000.0,
        total_tax_paid=15500.0,
    )


def _strategy(name='Steady Saver'):
    return SimpleNamespace(
        scenario=SimpleNamespace(
            name=name, target_objective='Balanced Growth',
            start_year=2026, end_year=2027,
        ),
        final_net_worth=2_000_000.0,
        final_roth_value=900_000.0,
        final_pretax_value=100_000.0,
        final_taxable_value=50_000.0,
        total_conversions=75_000.0,
        total_taxes_paid=40_000.0,
        total_irmaa_costs=2_000.0,
        final_after_tax_net_worth=1_960_000.0,
        years=[_year(), _year(2027, 67)],
    )


class TestExcelReport(unittest.TestCase):

    def test_workbook_has_summary_comparison_and_yearly_sheets(self):
        payload = build_excel_report(
            _client(), [_strategy()],
            generated_at=datetime(2026, 11, 11),
        )
        workbook = load_workbook(BytesIO(payload))

        self.assertIn('Summary', workbook.sheetnames)
        self.assertIn('Comparison', workbook.sheetnames)
        self.assertIn('Steady Saver', workbook.sheetnames)
        self.assertEqual(workbook['Summary']['B3'].value, 'Ada Lovelace')
        self.assertEqual(
            workbook['Comparison']['A2'].value, 'Steady Saver'
        )
        yearly = workbook['Steady Saver']
        self.assertEqual(yearly['A1'].value, 'Steady Saver')
        self.assertEqual(yearly['A9'].value, 2026)
        self.assertEqual(yearly['D9'].value, 0.0)

    def test_chart_is_embedded_when_supplied(self):
        payload = build_excel_report(
            _client(), [_strategy()],
            chart_png=mascot_png(80),
        )
        workbook = load_workbook(BytesIO(payload))
        self.assertIn('Chart', workbook.sheetnames)
        self.assertEqual(len(workbook['Chart']._images), 1)

    def test_empty_strategy_list_still_produces_workbook(self):
        payload = build_excel_report(_client(), [], generated_at='today')
        workbook = load_workbook(BytesIO(payload))
        self.assertIn('Summary', workbook.sheetnames)
        self.assertEqual(len(workbook.sheetnames), 2)

    def test_long_duplicate_names_get_unique_sheet_names(self):
        long_name = 'A very long strategy name that exceeds Excel limits ' * 2
        payload = build_excel_report(
            _client(), [_strategy(long_name), _strategy(long_name)]
        )
        workbook = load_workbook(BytesIO(payload))
        self.assertEqual(len(workbook.sheetnames), 4)
        self.assertTrue(all(len(name) <= 31 for name in workbook.sheetnames))

    def test_write_excel_report_round_trips_bytes(self):
        payload = build_excel_report(_client(), [_strategy()])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'report.xlsx')
            write_excel_report(path, payload)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 1000)
            workbook = load_workbook(path)
            self.assertIn('Summary', workbook.sheetnames)


if __name__ == '__main__':
    unittest.main()
