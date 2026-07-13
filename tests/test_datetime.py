from datetime import datetime, timezone
from unittest import TestCase

from utils.datetime import format_tashkent_datetime, parse_datetime, to_tashkent


class TashkentDatetimeTests(TestCase):
    def test_format_converts_utc_without_offset_suffix(self):
        self.assertEqual(
            format_tashkent_datetime("2026-07-14T10:30:45+00:00"),
            "14.07.2026 15:30",
        )

    def test_format_accepts_z_suffix(self):
        self.assertEqual(
            format_tashkent_datetime("2026-01-02T23:15:00Z"),
            "03.01.2026 04:15",
        )

    def test_naive_backend_datetime_is_treated_as_utc(self):
        value = datetime(2026, 7, 14, 10, 30)

        self.assertEqual(
            to_tashkent(value).strftime("%Y-%m-%d %H:%M"),
            "2026-07-14 15:30",
        )

    def test_parse_returns_aware_utc_value(self):
        parsed = parse_datetime("2026-07-14T15:30:00+05:00")

        self.assertEqual(
            parsed,
            datetime(2026, 7, 14, 10, 30, tzinfo=timezone.utc),
        )

    def test_format_uses_default_for_missing_or_invalid_value(self):
        self.assertEqual(format_tashkent_datetime(None), "—")
        self.assertEqual(format_tashkent_datetime("not-a-datetime"), "—")
