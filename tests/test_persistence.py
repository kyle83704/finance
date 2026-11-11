"""Tests for project save/load persistence (JSON project files)."""

import json
import os
import tempfile
import unittest

from src.models import (
    Account,
    ClientProfile,
    Expenses,
    IncomeStream,
    load_project,
    save_project,
)


def _sample_state():
    client = ClientProfile(
        first_name='Ada',
        last_name='Lovelace',
        birth_year=1965,
        spouse_birth_year=1967,
        state_residence='CA',
        filing_status='married_filing_jointly',
    )
    accounts = [
        Account('Trad IRA', 'Traditional IRA', 500000.0, pretax_basis=450000.0,
                aftertax_basis=50000.0, growth_rate=0.06),
        Account('Roth', 'Roth IRA', 120000.0, growth_rate=0.07),
    ]
    incomes = [
        IncomeStream('Social Security', 'Social Security', 30000.0, 67, 100,
                     0.025, 'ordinary', 67),
        IncomeStream('Pension', 'Pension', 18000.0, 65, 100, 0.0),
    ]
    expenses = Expenses(housing=20000.0, utilities=3000.0, food=8000.0,
                        transportation=4000.0, healthcare=9000.0,
                        insurance=4000.0, discretionary=6000.0, other=2000.0)
    return client, accounts, incomes, expenses


class TestProjectPersistence(unittest.TestCase):

    def test_round_trip_preserves_analysis_state(self):
        client, accounts, incomes, expenses = _sample_state()

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'project.json')
            save_project(client, accounts, incomes, expenses, path)
            loaded = load_project(path)

        self.assertIsNotNone(loaded)
        loaded_client, loaded_accounts, loaded_incomes, loaded_expenses = loaded

        self.assertEqual(loaded_client.first_name, 'Ada')
        self.assertEqual(loaded_client.last_name, 'Lovelace')
        self.assertEqual(loaded_client.state_residence, 'CA')
        self.assertEqual(loaded_client.filing_status, 'married_filing_jointly')
        self.assertEqual(loaded_client.birth_year, 1965)
        self.assertEqual(loaded_client.spouse_birth_year, 1967)
        # current_age is recomputed rather than persisted
        self.assertEqual(loaded_client.current_age, client.current_age)

        self.assertEqual(len(loaded_accounts), 2)
        self.assertEqual(loaded_accounts[0].account_type, 'Traditional IRA')
        self.assertAlmostEqual(loaded_accounts[0].pretax_basis, 450000.0)
        self.assertAlmostEqual(loaded_accounts[0].aftertax_basis, 50000.0)
        self.assertAlmostEqual(loaded_accounts[1].growth_rate, 0.07)

        self.assertEqual(len(loaded_incomes), 2)
        self.assertEqual(loaded_incomes[0].ss_claim_age, 67)
        self.assertEqual(loaded_incomes[1].start_age, 65)

        self.assertAlmostEqual(loaded_expenses.total_annual, expenses.total_annual)

    def test_written_file_is_versioned_json(self):
        client, accounts, incomes, expenses = _sample_state()

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'project.json')
            save_project(client, accounts, incomes, expenses, path)
            with open(path, 'r', encoding='utf-8') as handle:
                payload = json.load(handle)

        self.assertEqual(payload['version'], 1)
        self.assertIn('saved_at', payload)
        self.assertEqual(len(payload['accounts']), 2)
        self.assertEqual(payload['client']['first_name'], 'Ada')

    def test_missing_file_returns_none(self):
        path = os.path.join(tempfile.gettempdir(), 'roth_project_does_not_exist.json')
        if os.path.exists(path):
            os.remove(path)
        self.assertIsNone(load_project(path))

    def test_corrupt_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'corrupt.json')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('{not valid json')
            self.assertIsNone(load_project(path))

    def test_invalid_payload_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'invalid.json')
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump({'version': 1, 'client': {'unexpected': True}}, handle)
            self.assertIsNone(load_project(path))


if __name__ == '__main__':
    unittest.main()
