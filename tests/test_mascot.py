"""Tests for Penny the mascot (no windows are opened)."""

import unittest

from src.mascot import mascot_data_uri, mascot_png


class TestMascot(unittest.TestCase):

    def test_png_bytes_for_small_and_large_sizes(self):
        for size in (96, 220):
            data = mascot_png(size)
            self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertGreater(len(data), 1000)

    def test_data_uri_is_embeddable(self):
        uri = mascot_data_uri(120)
        self.assertTrue(uri.startswith('data:image/png;base64,'))
        self.assertGreater(len(uri), 1000)

    def test_repeated_size_is_cached(self):
        self.assertIs(mascot_png(140), mascot_png(140))


if __name__ == '__main__':
    unittest.main()
