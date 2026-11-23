"""Tests for the non-window helpers of the modernized GUI.

These cover layout/analysis helpers only; no windows are created or shown.
"""

import unittest
from types import SimpleNamespace

import PySimpleGUI as sg

from src import theme
from src.gui import (
    EXPENSE_KEYS,
    RothSimulatorGUI,
    _amount,
    _button,
    _expense_totals,
    _recon_display,
    _section,
    _stepper,
    _title,
)


class TestExpenseHelpers(unittest.TestCase):

    def test_blank_amount_is_zero(self):
        self.assertEqual(_amount({}, 'housing'), 0.0)
        self.assertEqual(_amount({'housing': ''}, 'housing'), 0.0)
        self.assertEqual(_amount({'housing': '   '}, 'housing'), 0.0)

    def test_amount_parses_numeric_text(self):
        self.assertAlmostEqual(_amount({'housing': '1200'}, 'housing'), 1200.0)
        self.assertAlmostEqual(_amount({'housing': ' 1200.50 '}, 'housing'), 1200.5)

    def test_totals_sum_every_category(self):
        values = {key: '1000' for key in EXPENSE_KEYS}
        annual, monthly = _expense_totals(values)
        self.assertAlmostEqual(annual, 1000.0 * len(EXPENSE_KEYS))
        self.assertAlmostEqual(monthly, annual / 12)

    def test_totals_skip_unparseable_values(self):
        values = {key: '' for key in EXPENSE_KEYS}
        values['housing'] = '24000'
        values['food'] = 'oops'
        annual, monthly = _expense_totals(values)
        self.assertAlmostEqual(annual, 24000.0)
        self.assertAlmostEqual(monthly, 2000.0)

    def test_totals_empty_values_are_zero(self):
        self.assertEqual(_expense_totals({}), (0.0, 0.0))


class TestLayoutHelpers(unittest.TestCase):

    def test_stepper_has_a_chip_per_step(self):
        chips = _stepper(3)
        self.assertEqual(len(chips), 5)
        self.assertTrue(all(isinstance(chip, sg.Text) for chip in chips))

    def test_title_rows_start_with_heading(self):
        rows = _title('Client Profile', 'Step 1', step=1)
        self.assertGreaterEqual(len(rows), 3)
        self.assertIsInstance(rows[0][0], sg.Text)

    def test_section_returns_a_complete_row(self):
        # _section() is concatenated into layouts, so it must return rows,
        # not a bare element (which PySimpleGUI rejects as a non-iterable row).
        rows = _section('Household')
        self.assertEqual(len(rows), 1)
        self.assertIsInstance(rows[0], list)
        self.assertEqual(len(rows[0]), 1)
        self.assertIsInstance(rows[0][0], sg.Text)

    def test_buttons_are_built_with_brand_colors(self):
        button = _button('Go', color='#123456')
        self.assertIsInstance(button, sg.Button)
        self.assertEqual(button.ButtonColor, ('white', '#123456'))

    def test_reconciliation_display_hides_negative_zero(self):
        self.assertEqual(_recon_display(-0.0004), '$0.00')
        self.assertEqual(_recon_display(-1.25), '-$1.25')
        self.assertEqual(_recon_display(12.5), '$12.50')


class TestThemeBackgrounds(unittest.TestCase):

    def test_text_and_input_backgrounds_use_the_warm_palette(self):
        # Constructor configures PySimpleGUI's global theme state.
        RothSimulatorGUI()
        text = sg.Text('Readable text')
        input_element = sg.Input()

        self.assertEqual(text.BackgroundColor, theme.BG)
        self.assertEqual(input_element.BackgroundColor, theme.SURFACE)
        self.assertEqual(text.TextColor, theme.TEXT)


class TestComparisonChart(unittest.TestCase):

    def setUp(self):
        # Constructor only configures the theme; it opens no window.
        self.gui = RothSimulatorGUI()

    def test_no_strategies_returns_none(self):
        self.gui.strategies = []
        self.assertIsNone(self.gui._comparison_chart())

    def test_chart_is_png_bytes(self):
        self.gui.strategies = [
            SimpleNamespace(scenario=SimpleNamespace(name='Alpha Strategy'),
                            final_net_worth=1_500_000.0),
            SimpleNamespace(scenario=SimpleNamespace(name='Beta Strategy'),
                            final_net_worth=2_250_000.0),
        ]
        chart = self.gui._comparison_chart()
        self.assertIsNotNone(chart)
        self.assertTrue(chart.startswith(b'\x89PNG'))


if __name__ == '__main__':
    unittest.main()
