import unittest
from datetime import datetime, timezone

from main import get_report_date


class GetReportDateTest(unittest.TestCase):
    def test_returns_previous_date_in_taipei(self):
        now = datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc)

        self.assertEqual(get_report_date(now), "2026-09-09")

    def test_converts_utc_before_subtracting_day(self):
        now = datetime(2026, 9, 9, 17, 0, tzinfo=timezone.utc)

        self.assertEqual(get_report_date(now), "2026-09-09")


if __name__ == "__main__":
    unittest.main()
