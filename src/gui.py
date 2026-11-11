"""Modern PySimpleGUI interface for the Roth conversion simulator."""

import io
import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import PySimpleGUI as sg

from src import theme
from src.constants import ACCOUNT_TYPES, OBJECTIVES, STATE_TAX_RATES
from src.excel_report import build_excel_report, write_excel_report
from src.mascot import mascot_data_uri, mascot_png
from src.models import (
    Account,
    ClientProfile,
    Expenses,
    IncomeStream,
    ScenarioSettings,
    load_project,
    save_project,
)
from src.optimizer import ConversionOptimizer
from src.reports import build_html_report, write_html_report

# ---------------------------------------------------------------------------
# Design tokens - Penny's warm palette (defined in src/theme.py)
# ---------------------------------------------------------------------------
BRAND_GREEN = theme.TEAL
BRAND_BLUE = theme.BLUE
BRAND_RED = theme.CORAL
BRAND_GREY = theme.MUTED_TEXT
MUTED_TEXT = theme.MUTED_TEXT
FAINT_TEXT = theme.FAINT_TEXT
PANEL_BG = theme.BG
CHART_BG = theme.CHART_BG
SEPARATOR_COLOR = theme.SEPARATOR_COLOR
NAVY = theme.NAVY
GOLD = theme.GOLD

HEADER_FONT = ('Segoe UI', 18, 'bold')
SECTION_FONT = ('Segoe UI', 12, 'bold')
BODY_FONT = ('Segoe UI', 10)
SMALL_FONT = ('Segoe UI', 9)
BUTTON_FONT = ('Segoe UI', 10, 'bold')

WIZARD_STEPS = ('Client', 'Accounts', 'Income', 'Expenses', 'Scenarios')

EXPENSE_KEYS = (
    'housing', 'utilities', 'food', 'transportation',
    'healthcare', 'insurance', 'discretionary', 'other',
)


# ---------------------------------------------------------------------------
# Reusable layout helpers
# ---------------------------------------------------------------------------
def _button(text: str, color: str = BRAND_GREEN, size: Tuple[int, int] = (15, 1),
            key: Optional[str] = None, tooltip: Optional[str] = None,
            bold: bool = True, text_color: str = 'white') -> sg.Button:
    """Build a button that follows the app palette."""
    params = {
        'size': size,
        'button_color': (text_color, color),
        'font': BUTTON_FONT if bold else BODY_FONT,
    }
    if key:
        params['key'] = key
    if tooltip:
        params['tooltip'] = tooltip
    return sg.Button(text, **params)


def _primary(text: str, **kwargs) -> sg.Button:
    return _button(text, color=BRAND_GREEN, **kwargs)


def _secondary(text: str, **kwargs) -> sg.Button:
    return _button(text, color=GOLD, text_color=NAVY, **kwargs)


def _neutral(text: str, **kwargs) -> sg.Button:
    return _button(text, color=theme.TEAL_SOFT, text_color=NAVY,
                   bold=False, **kwargs)


def _danger(text: str, **kwargs) -> sg.Button:
    return _button(text, color=BRAND_RED, **kwargs)


def _stepper(current: int) -> List[sg.Text]:
    """Row of step chips showing progress through the wizard."""
    chips = []
    for index, name in enumerate(WIZARD_STEPS, start=1):
        active = index == current
        done = index < current
        if active:
            label, background, foreground = f' {index} {name} ', BRAND_GREEN, 'white'
        elif done:
            label, background, foreground = f' ✓ {name} ', theme.TEAL_SOFT, theme.TEAL_DARK
        else:
            label, background, foreground = f' {index} {name} ', '#F3EAE0', MUTED_TEXT
        chips.append(sg.Text(
            label,
            font=('Segoe UI', 9, 'bold' if active or done else 'normal'),
            text_color=foreground,
            background_color=background,
            pad=(2, 0),
        ))
    return chips


def _title(heading: str, subtitle: str = '', step: Optional[int] = None) -> List[List]:
    """Standard window heading with optional subtitle and wizard progress."""
    rows: List[List] = [[sg.Text(heading.upper(), font=HEADER_FONT, text_color=NAVY)]]
    if subtitle:
        rows.append([sg.Text(subtitle, font=BODY_FONT, text_color=MUTED_TEXT)])
    if step is not None:
        rows.append(_stepper(step))
    rows.append([sg.HorizontalSeparator(color=SEPARATOR_COLOR, pad=(0, (8, 8)))])
    return rows


def _section(text: str) -> List[List[sg.Text]]:
    """Section heading as a complete row (so it can be concatenated into a layout)."""
    return [[sg.Text(text.upper(), font=SECTION_FONT, text_color=BRAND_BLUE, pad=(0, (8, 2)))]]


def _field(label: str, element, width: int = 17) -> List:
    return [sg.Text(label, size=(width,), font=BODY_FONT), element]


def _amount(values: Dict, key: str) -> float:
    """Parse a currency field, treating blanks as zero."""
    raw = (values.get(key) or '').strip()
    return float(raw) if raw else 0.0


def _expense_totals(values: Dict) -> Tuple[float, float]:
    annual = 0.0
    for key in EXPENSE_KEYS:
        try:
            annual += _amount(values, key)
        except (TypeError, ValueError):
            continue
    return annual, annual / 12


def _mascot_image(size: int = 200) -> Optional[bytes]:
    """Render Penny, falling back to text-only UI if rendering is unavailable."""
    try:
        return mascot_png(size)
    except Exception:
        return None


class RothSimulatorGUI:
    """Modern PySimpleGUI interface for Roth conversion simulator."""

    def __init__(self):
        sg.theme('LightBlue2')  # Light base so native controls match the palette
        sg.set_options(
            font=BODY_FONT,
            element_padding=(6, 6),
            button_color=('white', BRAND_GREEN),
            input_text_color=theme.TEXT,
            text_color=theme.TEXT,
            background_color=PANEL_BG,
            element_background_color=PANEL_BG,
            border_width=1,
        )
        # PySimpleGUI keeps Text/Input backgrounds in theme state separately
        # from the Window background.  Without these overrides every Text
        # element renders as a lavender block on top of the cream window.
        sg.theme_background_color(PANEL_BG)
        sg.theme_element_background_color(PANEL_BG)
        sg.theme_text_element_background_color(PANEL_BG)
        sg.theme_text_color(theme.TEXT)
        sg.theme_element_text_color(theme.TEXT)
        sg.theme_input_background_color(theme.SURFACE)
        sg.theme_input_text_color(theme.TEXT)
        sg.theme_button_color(('white', BRAND_GREEN))
        self.icon = 'icon.ico' if os.path.exists('icon.ico') else None
        self.client = None
        self.accounts = []
        self.income_streams = []
        self.expenses = None
        self.current_scenario = None
        self.strategies = []
        self.current_strategy_index = 0

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def run(self):
        """Main application loop."""
        self.show_main_menu()

    def show_main_menu(self):
        """Display the modern main menu."""
        mascot = _mascot_image(200)
        hero = []
        if mascot:
            hero.append(sg.Image(data=mascot, pad=(0, 0)))
        hero.append(sg.Column([
            [sg.Text('Hi, I’m Penny!', font=('Segoe UI', 22, 'bold'),
                      text_color=NAVY)],
            [sg.Text('Your friendly planning pig.', font=('Segoe UI', 11, 'bold'),
                      text_color=BRAND_GREEN)],
            [sg.Text('Let’s turn tax headaches into a clear, year-by-year plan\n'
                      'you can actually feel good about.',
                      font=BODY_FONT, text_color=MUTED_TEXT)],
        ], pad=(18, 0), vertical_alignment='center'))

        layout = _title(
            'Roth Conversion Simulator',
            'A friendlier way to plan tax-smart conversions, from today through age 100+.',
        ) + [
            [sg.Column([hero], pad=(0, (4, 10)), element_justification='center')],
            [sg.Text('Start a new plan or reopen one you saved earlier.',
                     font=BODY_FONT, text_color=MUTED_TEXT)],
            [sg.Text('')],
            [_primary('New Analysis', size=(24, 2), key='new_analysis',
                      tooltip='Walk through the five-step planning wizard'),
             _neutral('Open Project', size=(20, 2), key='open_project',
                      tooltip='Reload an analysis saved as JSON')],
            [_secondary('Help', size=(14, 1), key='help',
                        tooltip='Explain Roth conversions, IRMAA and RMDs'),
             _danger('Exit', size=(14, 1), key='exit')],
            [sg.Text('')],
            [sg.Text('Version 2.3 · Ledger edition · cash-flow accounting, tax funding and 2026 law',
                     font=SMALL_FONT, text_color=FAINT_TEXT)],
        ]

        window = sg.Window('Roth Conversion Simulator', layout, finalize=True,
                           size=(760, 560), element_justification='center',
                           icon=self.icon)

        while True:
            event, _ = window.read()

            if event in (sg.WINDOW_CLOSED, 'exit'):
                window.close()
                return
            if event == 'new_analysis':
                window.close()
                self.wizard_new_analysis()
                return
            if event == 'open_project':
                self.open_project()
            elif event == 'help':
                self.show_help()

    def wizard_new_analysis(self):
        """Multi-step wizard for creating a new analysis."""
        # Step 1: Client Profile
        self.client = self.step_client_profile()
        if self.client is None:
            self.show_main_menu()
            return

        # Step 2: Accounts
        self.accounts = self.step_accounts()
        if self.accounts is None:
            self.show_main_menu()
            return

        # Step 3: Income Streams
        self.income_streams = self.step_income_streams()
        if self.income_streams is None:
            self.show_main_menu()
            return

        # Step 4: Expenses
        self.expenses = self.step_expenses()
        if self.expenses is None:
            self.show_main_menu()
            return

        # Step 5: Scenario Selection
        scenarios = self.step_scenario_selection()
        if scenarios is None:
            self.show_main_menu()
            return

        # Run optimization
        self.run_optimization(scenarios)

    # ------------------------------------------------------------------
    # Project persistence
    # ------------------------------------------------------------------
    def open_project(self):
        """Load a previously saved project and resume at scenario selection."""
        filename = sg.popup_get_file(
            'Select a project file to open:',
            file_types=(('Project Files', '*.json'), ('All Files', '*.*')),
            title='Open Project',
        )

        if not filename:
            return

        result = load_project(filename)
        if result is None:
            sg.popup_error('Could not load project file. '
                           'It may be corrupted or an invalid format.',
                           title='Open Project', font=BODY_FONT)
            return

        self.client, self.accounts, self.income_streams, self.expenses = result

        sg.popup_ok(
            f"Loaded project for {self.client.first_name} {self.client.last_name}\n"
            f"{len(self.accounts)} account(s) · "
            f"{len(self.income_streams)} income stream(s)",
            title='Project Loaded', font=BODY_FONT,
        )

        # Skip straight to scenario selection since data is already loaded
        scenarios = self.step_scenario_selection()
        if scenarios is None:
            self.show_main_menu()
            return

        self.run_optimization(scenarios)

    def save_current_project(self):
        """Save the current analysis state to a project file."""
        if self.client is None or not self.accounts:
            sg.popup_error('No analysis data to save. Complete a new analysis first.',
                           title='Save Project', font=BODY_FONT)
            return

        default_name = f"{self.client.first_name}_{self.client.last_name}_project.json"
        filename = sg.popup_save_as(
            default_filename=default_name,
            save_as_title='Save Project',
            file_types=(('Project Files', '*.json'), ('All Files', '*.*')),
        )

        if not filename:
            return

        try:
            save_project(self.client, self.accounts, self.income_streams,
                         self.expenses, filename)
            sg.popup_ok(f'Project saved to:\n{filename}',
                        title='Project Saved', font=BODY_FONT)
        except Exception as e:
            sg.popup_error(f'Error saving project: {e}',
                           title='Save Project', font=BODY_FONT)

    def export_excel_report(self, optimizer: ConversionOptimizer) -> None:
        """Write a formatted Excel workbook with an embedded chart."""
        if not self.strategies:
            sg.popup_error('Run an analysis before exporting a report.',
                           title='No Analysis', font=BODY_FONT)
            return

        default_name = (f"{self.client.first_name}_{self.client.last_name}"
                        f"_roth_report.xlsx")
        filename = sg.popup_save_as(
            default_filename=default_name,
            save_as_title='Save Excel Report',
            file_types=(('Excel Workbook', '*.xlsx'), ('All Files', '*.*')),
        )
        if not filename:
            return

        try:
            comparison_df = optimizer.compare_strategies(self.strategies)
            payload = build_excel_report(
                self.client,
                self.strategies,
                comparison_df=comparison_df,
                chart_png=self._comparison_chart(),
            )
            write_excel_report(filename, payload)
        except Exception as e:
            sg.popup_error(f'Error saving Excel report: {e}',
                           title='Report Error', font=BODY_FONT)
            return

        sg.popup_ok(f'Excel report saved to:\n{filename}',
                    title='Report Saved', font=BODY_FONT)

    def export_html_report(self, optimizer: ConversionOptimizer) -> None:
        """Write a self-contained HTML report and offer to open it."""
        if not self.strategies:
            sg.popup_error('Run an analysis before exporting a report.',
                           title='No Analysis', font=BODY_FONT)
            return

        default_name = (f"{self.client.first_name}_{self.client.last_name}"
                        f"_roth_report.html")
        filename = sg.popup_save_as(
            default_filename=default_name,
            save_as_title='Save HTML Report',
            file_types=(('HTML Report', '*.html'), ('All Files', '*.*')),
        )
        if not filename:
            return

        try:
            comparison_df = optimizer.compare_strategies(self.strategies)
            report = build_html_report(
                self.client,
                self.strategies,
                comparison_df=comparison_df,
                chart_png=self._comparison_chart(),
                mascot_data_uri=mascot_data_uri(180),
            )
            write_html_report(filename, report)
        except Exception as e:
            sg.popup_error(f'Error saving report: {e}',
                           title='Report Error', font=BODY_FONT)
            return

        if sg.popup_yes_no(
            f'Report saved to:\n{filename}\n\nOpen it in your browser?',
            title='Report Saved', font=BODY_FONT,
        ) == 'Yes':
            try:
                webbrowser.open(Path(filename).resolve().as_uri())
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Wizard steps
    # ------------------------------------------------------------------
    def step_client_profile(self) -> Optional[ClientProfile]:
        """Collect client profile information."""
        current_year = datetime.now().year

        layout = _title(
            'Client Profile',
            'Who is this analysis for?',
            step=1,
        ) + _section('Personal details') + [
            _field('First Name', sg.Input(key='first_name', size=(28,), font=BODY_FONT)),
            _field('Last Name', sg.Input(key='last_name', size=(28,), font=BODY_FONT)),
            _field('Birth Year', sg.Input(key='birth_year', size=(28,), font=BODY_FONT)),
        ] + _section('Household') + [
            [sg.Text('Married?', size=(17,), font=BODY_FONT),
             sg.Radio('Yes', 'married', True, key='married_yes'),
             sg.Radio('No', 'married', False, key='married_no')],
            _field('Spouse Birth Year', sg.Input(key='spouse_birth_year', size=(28,),
                                                disabled=True, font=BODY_FONT)),
            _field('State Residence', sg.Combo(sorted(STATE_TAX_RATES.keys()),
                                              key='state', default_value='ID',
                                              size=(26,), font=BODY_FONT)),
            [sg.Text('')],
            [_primary('Next', key='next', size=(15, 1)),
             _neutral('Cancel', key='cancel', size=(15, 1))],
        ]

        window = sg.Window('New Analysis - Step 1/5: Client Profile', layout,
                           finalize=True, icon=self.icon)
        window['married_yes'].bind('<ButtonRelease>', '_CHANGED')
        window['married_no'].bind('<ButtonRelease>', '_CHANGED')

        while True:
            event, values = window.read()

            if event in (sg.WINDOW_CLOSED, 'cancel'):
                window.close()
                return None

            elif event in ('married_yes_CHANGED', 'married_no_CHANGED'):
                window['spouse_birth_year'].update(disabled=not values['married_yes'])

            elif event == 'next':
                try:
                    first_name = values['first_name'].strip()
                    last_name = values['last_name'].strip()
                    birth_year = int(values['birth_year'])

                    if not first_name or not last_name or birth_year <= 1900 or birth_year > current_year:
                        sg.popup_error('Please enter valid name and birth year',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    spouse_birth_year = None
                    if values['married_yes']:
                        spouse_birth_year = int(values['spouse_birth_year'])
                        if spouse_birth_year <= 1900 or spouse_birth_year > current_year:
                            sg.popup_error('Please enter valid spouse birth year',
                                           title='Invalid Input', font=BODY_FONT)
                            continue

                    client = ClientProfile(
                        first_name=first_name,
                        last_name=last_name,
                        birth_year=birth_year,
                        spouse_birth_year=spouse_birth_year,
                        state_residence=values['state'],
                        filing_status='married_filing_jointly' if values['married_yes'] else 'single',
                    )

                    window.close()
                    return client

                except ValueError:
                    sg.popup_error('Please enter valid numbers for birth years',
                                   title='Invalid Input', font=BODY_FONT)

    def step_accounts(self) -> Optional[List[Account]]:
        """Collect account information."""
        accounts = []

        layout = _title(
            'Accounts',
            'Add every retirement and investment account that matters for the plan.',
            step=2,
        ) + [
            _field('Account Name', sg.Input(key='acc_name', size=(26,), font=BODY_FONT)),
            _field('Account Type', sg.Combo(ACCOUNT_TYPES, key='acc_type',
                                           size=(24,), font=BODY_FONT)),
            _field('Current Balance', sg.Input(key='acc_balance', size=(26,), font=BODY_FONT)),
            _field('Pre-tax Basis', sg.Input(key='acc_pretax', size=(26,), font=BODY_FONT)),
            _field('After-tax Basis', sg.Input(key='acc_aftertax', size=(26,), font=BODY_FONT)),
            _field('Taxable Cost Basis', sg.Input(key='acc_cost_basis', size=(26,),
                                                 font=BODY_FONT,
                                                 tooltip='Original cost of taxable holdings; used to calculate realized gains.')),
            _field('Expected Growth %', sg.Input('7.0', key='acc_growth', size=(26,),
                                                font=BODY_FONT,
                                                tooltip='Average annual return, e.g. 7 for 7%')),
            _field('Annual Contribution', sg.Input('0', key='acc_contrib', size=(26,),
                                                  font=BODY_FONT)),
            [sg.Text('')],
            [_primary('Add Account', key='add_account', size=(15, 1)),
             _neutral('Done', key='done', size=(15, 1)),
             _danger('Cancel', key='cancel', size=(12, 1))],
            [sg.Text('')],
            _section('Accounts added'),
            [sg.Listbox([], key='acc_list', size=(66, 7), font=BODY_FONT,
                        disabled=True, no_scrollbar=False,
                        background_color=theme.SURFACE, text_color=theme.TEXT,
                        highlight_background_color=theme.TEAL_SOFT,
                        highlight_text_color=theme.NAVY)],
        ]

        window = sg.Window('New Analysis - Step 2/5: Accounts', layout,
                           finalize=True, icon=self.icon)

        while True:
            event, values = window.read()

            if event in (sg.WINDOW_CLOSED, 'cancel'):
                window.close()
                return None

            elif event == 'add_account':
                try:
                    name = values['acc_name'].strip()
                    acc_type = values['acc_type']
                    balance = float(values['acc_balance'])
                    pretax = float(values['acc_pretax']) if values['acc_pretax'] else 0.0
                    aftertax = float(values['acc_aftertax']) if values['acc_aftertax'] else 0.0
                    cost_basis = float(values['acc_cost_basis']) if values['acc_cost_basis'] else 0.0
                    growth = float(values['acc_growth']) / 100
                    contrib = float(values['acc_contrib']) if values['acc_contrib'] else 0.0

                    if not name or not acc_type:
                        sg.popup_error('Please enter account name and type',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    if balance < 0:
                        sg.popup_error('Balance must be non-negative',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    if cost_basis < 0 or cost_basis > balance:
                        sg.popup_error('Taxable cost basis must be between zero and the balance',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    account = Account(
                        name=name,
                        account_type=acc_type,
                        current_balance=balance,
                        pretax_basis=pretax,
                        aftertax_basis=aftertax,
                        cost_basis=cost_basis,
                        growth_rate=growth,
                        annual_contribution=contrib,
                    )

                    accounts.append(account)

                    # Update list
                    list_items = [f"{a.name} ({a.account_type}) - ${a.current_balance:,.0f}"
                                  for a in accounts]
                    window['acc_list'].update(list_items)

                    # Clear inputs
                    window['acc_name'].update('')
                    window['acc_type'].update('')
                    window['acc_balance'].update('')
                    window['acc_pretax'].update('')
                    window['acc_aftertax'].update('')
                    window['acc_cost_basis'].update('')
                    window['acc_growth'].update('7.0')
                    window['acc_contrib'].update('0')

                except ValueError:
                    sg.popup_error('Please enter valid numbers for all fields',
                                   title='Invalid Input', font=BODY_FONT)

            elif event == 'done':
                if not accounts:
                    sg.popup_error('Please add at least one account',
                                   title='Missing Accounts', font=BODY_FONT)
                    continue
                window.close()
                return accounts

    def step_income_streams(self) -> Optional[List[IncomeStream]]:
        """Collect income stream information."""
        income_streams = []

        layout = _title(
            'Income Streams',
            'Add Social Security, pensions, part-time work and other income.',
            step=3,
        ) + [
            _field('Income Name', sg.Input(key='inc_name', size=(26,), font=BODY_FONT)),
            _field('Type', sg.Combo(['W2 Income', 'Self-Employment', 'Social Security',
                                     'Pension', 'Dividends'],
                                    key='inc_type', size=(24,), font=BODY_FONT)),
            _field('Annual Amount', sg.Input(key='inc_amount', size=(26,), font=BODY_FONT)),
            _field('Start Age', sg.Input('65', key='inc_start', size=(26,), font=BODY_FONT)),
            _field('End Age', sg.Input('100', key='inc_end', size=(26,), font=BODY_FONT)),
            _field('Annual Growth %', sg.Input('0', key='inc_growth', size=(26,),
                                              font=BODY_FONT,
                                              tooltip='Cost-of-living adjustment, e.g. 2.5 for 2.5%')),
            _field('Tax Treatment', sg.Combo(['Ordinary Income', 'Qualified Dividends', 'Tax-Free'],
                                            key='inc_tax', default_value='Ordinary Income',
                                            size=(24,), font=BODY_FONT)),
            [sg.Text('')],
            [_primary('Add Income', key='add_income', size=(15, 1)),
             _neutral('Done', key='done', size=(15, 1)),
             _danger('Cancel', key='cancel', size=(12, 1))],
            [sg.Text('')],
            _section('Income streams added'),
            [sg.Listbox([], key='inc_list', size=(66, 7), font=BODY_FONT,
                        disabled=True, background_color=theme.SURFACE,
                        text_color=theme.TEXT,
                        highlight_background_color=theme.TEAL_SOFT,
                        highlight_text_color=theme.NAVY)],
        ]

        window = sg.Window('New Analysis - Step 3/5: Income Streams', layout,
                           finalize=True, icon=self.icon)

        while True:
            event, values = window.read()

            if event in (sg.WINDOW_CLOSED, 'cancel'):
                window.close()
                return None

            elif event == 'add_income':
                try:
                    name = values['inc_name'].strip()
                    inc_type = values['inc_type']
                    amount = float(values['inc_amount'])
                    start = int(values['inc_start'])
                    end = int(values['inc_end'])
                    growth = float(values['inc_growth']) / 100
                    tax = values['inc_tax'].lower().replace(' ', '_')

                    if not name or not inc_type:
                        sg.popup_error('Please enter income name and type',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    if amount < 0 or start < 0 or end < start:
                        sg.popup_error('Please enter valid amounts and age ranges',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    income = IncomeStream(
                        name=name,
                        income_type=inc_type,
                        annual_amount=amount,
                        start_age=start,
                        end_age=end,
                        growth_rate=growth,
                        tax_treatment=tax,
                    )

                    income_streams.append(income)

                    # Update list
                    list_items = [f"{i.name} - ${i.annual_amount:,.0f}/year (ages {i.start_age}-{i.end_age})"
                                  for i in income_streams]
                    window['inc_list'].update(list_items)

                    # Clear inputs
                    window['inc_name'].update('')
                    window['inc_type'].update('')
                    window['inc_amount'].update('')
                    window['inc_start'].update('65')
                    window['inc_end'].update('100')
                    window['inc_growth'].update('0')

                except ValueError:
                    sg.popup_error('Please enter valid numbers for all fields',
                                   title='Invalid Input', font=BODY_FONT)

            elif event == 'done':
                if not income_streams:
                    sg.popup_error('Please add at least one income stream',
                                   title='Missing Income', font=BODY_FONT)
                    continue
                window.close()
                return income_streams

    def step_expenses(self) -> Optional[Expenses]:
        """Collect expense information."""
        layout = _title(
            'Annual Expenses',
            'Enter expected yearly spending by category. Totals update as you type.',
            step=4,
        ) + [
            _field('Housing', sg.Input(key='housing', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Utilities', sg.Input(key='utilities', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Food', sg.Input(key='food', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Transportation', sg.Input(key='transportation', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Healthcare', sg.Input(key='healthcare', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Insurance', sg.Input(key='insurance', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Discretionary', sg.Input(key='discretionary', size=(20,), font=BODY_FONT, enable_events=True)),
            _field('Other', sg.Input(key='other', size=(20,), font=BODY_FONT, enable_events=True)),
            [sg.HorizontalSeparator(color=SEPARATOR_COLOR, pad=(0, (8, 8)))],
            _field('Total Monthly', sg.Text('$0', key='monthly_total', size=(20,),
                                           font=SECTION_FONT, text_color=BRAND_GREEN)),
            _field('Total Annual', sg.Text('$0', key='annual_total', size=(20,),
                                          font=SECTION_FONT, text_color=BRAND_GREEN)),
            [sg.Text('')],
            [_primary('Next', key='next', size=(15, 1)),
             _neutral('Clear', key='clear', size=(15, 1)),
             _danger('Cancel', key='cancel', size=(12, 1))],
        ]

        window = sg.Window('New Analysis - Step 4/5: Expenses', layout,
                           finalize=True, icon=self.icon)

        while True:
            event, values = window.read()

            if event in (sg.WINDOW_CLOSED, 'cancel'):
                window.close()
                return None

            elif event in EXPENSE_KEYS:
                annual, monthly = _expense_totals(values)
                window['annual_total'].update(f'${annual:,.0f}')
                window['monthly_total'].update(f'${monthly:,.0f}')

            elif event == 'clear':
                for key in EXPENSE_KEYS:
                    window[key].update('')
                window['annual_total'].update('$0')
                window['monthly_total'].update('$0')

            elif event == 'next':
                try:
                    parsed = {key: _amount(values, key) for key in EXPENSE_KEYS}
                    expenses = Expenses(**parsed)

                    window.close()
                    return expenses

                except ValueError:
                    sg.popup_error('Please enter valid numbers for all fields',
                                   title='Invalid Input', font=BODY_FONT)

    def step_scenario_selection(self) -> Optional[List[ScenarioSettings]]:
        """Select which scenarios to analyze."""
        current_year = datetime.now().year
        objective_rows = []
        for index, objective in enumerate(OBJECTIVES):
            objective_rows.append([
                sg.Checkbox(objective, key=f'obj_{index}', font=BODY_FONT,
                            default=objective != 'Maximize Inheritance')
            ])

        layout = _title(
            'Scenario Selection',
            'Choose the objectives to compare and the projection window.',
            step=5,
        ) + objective_rows + [
            [sg.HorizontalSeparator(color=SEPARATOR_COLOR, pad=(0, (8, 8)))],
            [sg.Text('Analysis Period', size=(15,), font=SECTION_FONT)],
            [sg.Text('From Year:', size=(10,), font=BODY_FONT),
             sg.Input(str(current_year), key='start_year', size=(10,), font=BODY_FONT),
             sg.Text('To Year:', size=(10,), font=BODY_FONT),
             sg.Input(str(current_year + 29), key='end_year', size=(10,), font=BODY_FONT)],
            [sg.Text('Tax Funding', size=(15,), font=SECTION_FONT),
             sg.Text('How should taxes be paid?', font=BODY_FONT, text_color=MUTED_TEXT)],
            [sg.Text('Payment source:', size=(26,), font=BODY_FONT),
             sg.Combo(['Cash', 'Withhold from conversion', 'Sell taxable assets',
                       'External funds'], key='tax_source', default_value='Cash',
                      readonly=True, size=(28,), font=BODY_FONT)],
            [sg.Text('External funds available ($/yr):', size=(26,), font=BODY_FONT),
             sg.Input('0', key='external_funding', size=(14,), font=BODY_FONT)],
            [sg.Text('Deferred tax on remaining pre-tax (%):', size=(26,), font=BODY_FONT),
             sg.Input('22', key='deferred_rate', size=(14,), font=BODY_FONT)],
            [sg.Text('External funds are used only when explicitly entered; '
                     'the simulator never assumes unlimited outside cash.',
                     font=SMALL_FONT, text_color=MUTED_TEXT)],
            [sg.Text('')],
            [_primary('Run Analysis', key='run', size=(15, 1)),
             _danger('Cancel', key='cancel', size=(12, 1))],
        ]

        window = sg.Window('New Analysis - Step 5/5: Scenarios', layout,
                           finalize=True, icon=self.icon)

        while True:
            event, values = window.read()

            if event in (sg.WINDOW_CLOSED, 'cancel'):
                window.close()
                return None

            elif event == 'run':
                try:
                    selected = [objective for index, objective in enumerate(OBJECTIVES)
                                if values[f'obj_{index}']]

                    if not selected:
                        sg.popup_error('Please select at least one scenario',
                                       title='No Scenarios', font=BODY_FONT)
                        continue

                    start_year = int(values['start_year'])
                    end_year = int(values['end_year'])

                    if start_year >= end_year:
                        sg.popup_error('Start year must be before end year',
                                       title='Invalid Period', font=BODY_FONT)
                        continue

                    source_map = {
                        'Cash': 'cash',
                        'Withhold from conversion': 'withhold',
                        'Sell taxable assets': 'taxable',
                        'External funds': 'external',
                    }
                    external_funding = float(values['external_funding'] or 0)
                    deferred_rate = float(values['deferred_rate'] or 22) / 100.0
                    if external_funding < 0 or not 0 <= deferred_rate <= 1:
                        sg.popup_error('Tax funding and deferred rate must be valid non-negative values',
                                       title='Invalid Input', font=BODY_FONT)
                        continue

                    # Build policy-driven scenarios through the optimizer so
                    # every objective gets its documented conversion behavior.
                    base_scenario = ScenarioSettings(
                        name="Base",
                        start_year=start_year,
                        end_year=end_year,
                        tax_payment_source=source_map[values['tax_source']],
                        external_tax_funding=external_funding,
                        deferred_tax_rate=deferred_rate,
                    )
                    optimizer = ConversionOptimizer(self.client)
                    scenarios = optimizer.generate_scenarios(
                        base_scenario, selected
                    )

                    window.close()
                    return scenarios

                except ValueError:
                    sg.popup_error('Please enter valid years',
                                   title='Invalid Period', font=BODY_FONT)

    # ------------------------------------------------------------------
    # Analysis and results
    # ------------------------------------------------------------------
    def run_optimization(self, scenarios: List[ScenarioSettings]):
        """Run optimization with a progress indicator and display results."""
        optimizer = ConversionOptimizer(self.client)

        try:
            self.strategies = []
            total = max(1, len(scenarios))

            for index, scenario in enumerate(scenarios):
                keep_going = sg.one_line_progress_meter(
                    'Analyzing strategies',
                    index + 1,
                    total,
                    f'{scenario.name} ({index + 1}/{total})',
                    key='analysis_progress',
                    orientation='h',
                    bar_color=(BRAND_GREEN, theme.BORDER),
                )

                if keep_going is False:
                    sg.popup('Analysis cancelled.',
                             title='Cancelled', font=BODY_FONT)
                    self.show_main_menu()
                    return

                self.strategies.append(
                    optimizer.simulator.run_full_simulation(
                        scenario, self.accounts, self.income_streams, self.expenses
                    )
                )

            self.show_results(optimizer)

        except Exception as e:
            sg.popup_error(f'Error running analysis: {str(e)}',
                           title='Analysis Error', font=BODY_FONT)
            self.show_main_menu()

    def _comparison_chart(self) -> Optional[bytes]:
        """Render a friendly light bar chart of final net worth per strategy."""
        if not self.strategies:
            return None

        try:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure

            ordered = sorted(self.strategies, key=lambda s: s.final_net_worth)
            names = [s.scenario.name for s in ordered]
            values = [s.final_net_worth / 1_000_000 for s in ordered]
            best = ordered[-1] if ordered else None
            colors = [theme.GOLD if s is best else BRAND_GREEN for s in ordered]

            fig = Figure(figsize=(10, 4.2), facecolor=theme.SURFACE)
            FigureCanvasAgg(fig)
            ax = fig.add_subplot(111)
            ax.set_facecolor(CHART_BG)

            bars = ax.barh(names, values, color=colors, alpha=0.9,
                           edgecolor=theme.TEAL_DARK, linewidth=0.6)
            for bar, value in zip(bars, values):
                ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                        f'  ${value:,.2f}M', va='center', color=theme.TEXT,
                        fontsize=9, fontweight='bold')

            ax.set_xlabel('Final net worth ($M)', color=MUTED_TEXT, fontsize=10)
            ax.set_title('Strategy comparison · final net worth',
                         color=NAVY, fontsize=13, fontweight='bold', pad=14)
            ax.grid(True, axis='x', alpha=0.35, color=theme.CHART_GRID,
                    linestyle='--')
            ax.tick_params(colors=MUTED_TEXT, labelsize=9)
            for spine in ('top', 'right'):
                ax.spines[spine].set_visible(False)
            for spine in ('left', 'bottom'):
                ax.spines[spine].set_color(theme.BORDER)
            fig.tight_layout()

            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=110,
                        facecolor=fig.get_facecolor(), bbox_inches='tight')
            return buffer.getvalue()

        except Exception:
            return None

    def show_results(self, optimizer: ConversionOptimizer):
        """Display analysis results in a tabbed, modern window."""
        comparison_df = optimizer.compare_strategies(self.strategies)
        best = max(self.strategies, key=lambda s: s.final_net_worth)
        summary = (f"Best final net worth: {best.scenario.name} · "
                   f"${best.final_net_worth:,.0f}")

        thrifty = min(self.strategies,
                      key=lambda s: s.total_tax_liability)
        tax_summary = (f"Lowest lifetime tax liability: {thrifty.scenario.name} · "
                       f"${thrifty.total_tax_liability:,.0f}")
        mascot = _mascot_image(110)
        summary_cells = [
            [sg.Text('Penny’s pick', font=('Segoe UI', 9, 'bold'),
                     text_color=BRAND_GREEN)],
            [sg.Text(summary, font=BODY_FONT, text_color=NAVY)],
            [sg.Text(tax_summary, font=SMALL_FONT, text_color=MUTED_TEXT)],
        ]
        summary_row = []
        if mascot:
            summary_row.append(sg.Image(data=mascot, pad=(0, 0)))
        summary_row.append(sg.Column(summary_cells, pad=(14, 0),
                                     vertical_alignment='center'))

        comparison_tab = [
            summary_row,
            [sg.Table(
                values=comparison_df.values.tolist(),
                headings=comparison_df.columns.tolist(),
                key='results_table',
                size=(100, 12),
                num_rows=12,
                justification='right',
                font=BODY_FONT,
                text_color=theme.TEXT,
                background_color=theme.SURFACE,
                header_background_color=BRAND_GREEN,
                header_text_color='white',
                alternating_row_color='#F7FBF9',
                auto_size_columns=True,
            )],
        ]

        chart = self._comparison_chart()
        chart_tab = (
            [[sg.Image(data=chart, key='comparison_chart')]]
            if chart else
            [[sg.Text('Chart could not be generated in this environment.',
                      font=BODY_FONT, text_color=MUTED_TEXT)]]
        )

        layout = _title(
            'Analysis Results',
            f"{self.client.first_name} {self.client.last_name} · "
            f"{len(self.strategies)} strategies compared",
        ) + [
            [sg.TabGroup(
                [[sg.Tab('Comparison', comparison_tab),
                  sg.Tab('Chart', chart_tab)]],
                key='results_tabs',
                expand_x=True,
                expand_y=True,
                background_color=PANEL_BG,
                tab_background_color=theme.SOFT_PEACH,
                selected_background_color=theme.SURFACE,
                selected_title_color=NAVY,
                title_color=MUTED_TEXT,
                border_width=0,
            )],
            [sg.Text('Tax liability includes income tax, taxable Social '
                     'Security, RMD tax, conversion tax, realized gains and IRMAA. '
                     'Tax paid shows how much was actually funded; unpaid tax and '
                     'the deferred-tax reserve reduce after-tax net worth. Save '
                     'the project or export HTML/Excel/CSV reports for review.',
                     font=SMALL_FONT, text_color=MUTED_TEXT)],
            [_primary('Save Project', key='save_project'),
             _neutral('Export to CSV', key='export_csv'),
             _secondary('HTML Report', key='export_report'),
             _neutral('Excel Report', key='export_excel'),
             _neutral('Detail View', key='detail_view'),
             _danger('Back to Menu', key='back')],
        ]

        window = sg.Window('Analysis Results', layout, finalize=True,
                           size=(1220, 640), icon=self.icon)

        while True:
            event, _ = window.read()

            if event in (sg.WINDOW_CLOSED, 'back'):
                break
            elif event == 'save_project':
                self.save_current_project()
            elif event == 'export_csv':
                folder = sg.popup_get_folder('Select folder for export',
                                             title='Export CSV')
                if folder:
                    for i, strategy in enumerate(self.strategies):
                        safe_name = ''.join(
                            c if c.isalnum() else '_' for c in strategy.scenario.name
                        )
                        filename = os.path.join(
                            folder, f"strategy_{i + 1}_{safe_name}.csv"
                        )
                        optimizer.export_strategy_to_csv(strategy, filename)
                    sg.popup_ok(f'Exported {len(self.strategies)} strategies to\n{folder}',
                                title='Export Complete', font=BODY_FONT)
            elif event == 'export_report':
                self.export_html_report(optimizer)
            elif event == 'export_excel':
                self.export_excel_report(optimizer)
            elif event == 'detail_view':
                self.show_detail_view(optimizer)

        window.close()
        self.show_main_menu()

    def _choose_strategy(self, names: List[str]) -> Optional[str]:
        """Modal strategy picker used by the detail view."""
        layout = _title(
            'Strategy Detail',
            'Select a strategy to inspect year by year.',
        ) + [
            [sg.Listbox(names, key='strategy_choice',
                        size=(52, min(10, max(3, len(names)))),
                        font=BODY_FONT, enable_events=True,
                        select_mode=sg.LISTBOX_SELECT_MODE_SINGLE)],
            [_primary('View Detail', key='choose'),
             _neutral('Cancel', key='cancel')],
        ]

        window = sg.Window('Select Strategy', layout, finalize=True,
                           modal=True, icon=self.icon)
        choice = None

        while True:
            event, values = window.read()

            if event in (sg.WINDOW_CLOSED, 'cancel'):
                break
            elif event == 'strategy_choice' and values['strategy_choice']:
                choice = values['strategy_choice'][0]
                break
            elif event == 'choose':
                if values['strategy_choice']:
                    choice = values['strategy_choice'][0]
                    break
                sg.popup_error('Select a strategy first.',
                               title='No Selection', font=BODY_FONT)

        window.close()
        return choice

    def show_detail_view(self, optimizer: ConversionOptimizer):
        """Show detailed year-by-year view for a strategy."""
        if not self.strategies:
            return

        strategy_names = [s.scenario.name for s in self.strategies]
        choice = self._choose_strategy(strategy_names)
        if not choice:
            return

        strategy = self.strategies[strategy_names.index(choice)]

        # Create year-by-year data
        data = []
        for year_result in strategy.years:
            data.append([
                year_result.year,
                year_result.age,
                f"${year_result.start_balance_pretax:,.0f}",
                f"${year_result.rmd_required:,.0f}",
                f"${year_result.taxable_social_security:,.0f}",
                f"${year_result.recommended_conversion:,.0f}",
                f"${year_result.conversion_tax:,.0f}",
                f"${year_result.irmaa_impact:,.0f}",
                f"${year_result.magi:,.0f}",
                f"${year_result.irmaa_magi:,.0f}",
                f"${year_result.end_balance_roth:,.0f}",
                f"${year_result.total_tax_paid:,.0f}",
                f"${year_result.taxes_paid:,.0f}",
                f"${year_result.taxes_unpaid:,.0f}",
                f"${year_result.spending_paid:,.0f}",
                f"${year_result.reconciliation_difference:,.2f}",
            ])

        headings = ['Year', 'Age', 'Start Pretax', 'RMD', 'Taxable SS',
                    'Conversion', 'Conv. Tax', 'IRMAA', 'MAGI', 'IRMAA MAGI',
                    'End Roth', 'Tax Liability', 'Tax Paid', 'Tax Unpaid',
                    'Spending Paid', 'Recon Diff']

        layout = _title('Detail View', choice) + [
            [sg.Table(
                values=data,
                headings=headings,
                key='detail_table',
                size=(142, 18),
                num_rows=18,
                justification='right',
                font=BODY_FONT,
                text_color=theme.TEXT,
                background_color=theme.SURFACE,
                header_background_color=BRAND_GREEN,
                header_text_color='white',
                alternating_row_color='#F7FBF9',
                auto_size_columns=True,
            )],
            [_neutral('Close', key='close')],
        ]

        window = sg.Window('Strategy Detail', layout, finalize=True,
                           size=(1380, 580), modal=True, icon=self.icon)

        while True:
            event, _ = window.read()
            if event in (sg.WINDOW_CLOSED, 'close'):
                break

        window.close()

    def show_help(self):
        """Show help documentation."""
        help_text = """
ROTH CONVERSION SIMULATOR - Help

Hi, I'm Penny, your friendly planning pig. My job is to make the tax side of
retirement feel a little less intimidating. Here's how this tool helps you:

This tool helps you optimize Roth conversion strategies for retirement by:

1. Modeling your complete financial picture (assets, income, expenses)
2. Projecting account values to age 100
3. Analyzing multiple conversion strategies
4. Identifying optimal approaches based on your goals

KEY CONCEPTS:

Roth Conversion: Moving money from traditional (pre-tax) IRAs to Roth (after-tax) accounts.
- Pro: Tax-free growth, no RMDs, tax-free inheritance
- Con: Pay income tax on conversion amount

IRMAA: Income-Related Monthly Adjustment Amounts
- 2026 surcharges start above $109k single / $218k married filing jointly
- Six tiers include both Part B and Part D; the top tier starts at $500k/$750k
- The premium uses MAGI from two years earlier
- Conversions increase MAGI, potentially triggering IRMAA two years later

RMD: Required Minimum Distributions
- Start at age 73 if born 1951-1959; age 75 if born in 1960 or later
- Must withdraw a percentage of traditional IRA/401k each year
- Roth IRAs have no RMD during owner's lifetime

SOCIAL SECURITY AND DEDUCTIONS:
- Up to 85% of Social Security can be taxable under provisional-income rules
- 2026 standard deduction: $16,100 single / $32,200 married filing jointly
- Age 65+ adds $2,050 single or $1,650 per eligible married spouse
- Qualified dividends use 0/15/20% federal rates
- Federal brackets and thresholds are indexed at 2.5% after 2026

OBJECTIVES:

1. Maximize Roth Value: Fill the bracket and accept IRMAA to build Roth assets
2. Maximize Gross Net Worth: Fill up to the 22% bracket without an IRMAA cap
3. Minimize Tax Paid: No voluntary conversions; take only RMDs
4. Minimize IRMAA: Convert only up to the first Medicare threshold
5. Maximize Inheritance: Convert while keeping the federal rate at 24% or less
6. Balanced Growth: Fill the 22% bracket while avoiding IRMAA

CASH FLOW AND TAX FUNDING:

- Living expenses are paid from cash first, then taxable assets. If neither is
  available, the shortfall is reported; the simulator does not invent money.
- Taxes are funded from the source selected in Step 5: cash, Roth withholding,
  taxable-account sales or explicit external money. External funding is capped
  at the amount you enter.
- Taxable sales use the cost basis you enter and realize taxable gains.
- Tax liability is not the same as tax paid. Unpaid tax and the deferred-tax
  reserve on remaining pre-tax balances reduce Net After All Taxes.
- The HTML report includes the rule registry so verified law, planning
  assumptions and unsupported areas are easy to review.

REPORTS:

From the results window, choose HTML Report to save a friendly, self-contained
report with the strategy comparison, a chart and year-by-year tables. It opens
in any browser and can be shared with your tax professional; use the browser's
Print dialog to save a PDF. Choose Excel Report for a formatted workbook with
summary, comparison, yearly sheets and an embedded chart. Export CSV is still
available when you want raw data for a spreadsheet.

PROJECTS:

Save an analysis from the results window (Save Project) and reopen it
from the main menu (Open Project) to keep your inputs between sessions.

LIMITS:

2026 federal and IRMAA values are verified against official sources. Later-year
indexing is a 2.5% planning assumption. State tax is a flat approximation.
Short-term gains, wash sales, loss carryforwards, NIIT, AMT, QCDs, the OBBBA
senior deduction, MFS/HOH brackets and estate tax are not modeled.

For more information, visit the documentation.
        """
        sg.popup_scrolled(help_text, title='Help', size=(76, 30), font=BODY_FONT)

    def main(self):
        """Entry point for GUI."""
        self.run()


if __name__ == '__main__':
    app = RothSimulatorGUI()
    app.main()
