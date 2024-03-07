
from decimal import Decimal
from unittest import TestCase

from pwneddb.utils import duration


class DurationTest(TestCase):
    minute = 60
    hour = minute * 60
    day = hour * 24

    def test_negative(self) -> None:
        with self.assertRaisesRegex(ValueError, "Positive number expected, given: -245"):
            duration(-245)

    def test_bad_string(self) -> None:
        with self.assertRaisesRegex(ValueError, "Number of seconds expected..."):
            duration('banana')                              # type: ignore[arg-type]

    def test_bad_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "Number of seconds expected, given: None"):
            duration(None)                                  # type: ignore[arg-type]

    def test_other_numeric(self) -> None:
        self.assertEqual(duration(42.2), '42 seconds')
        self.assertEqual(
            duration(Decimal('42.0')),                      # type: ignore[arg-type]
            '42 seconds',
        )

    def test_years(self) -> None:
        self.assertEqual(duration(3000 * self.day), '8 years')
        self.assertEqual(duration(731 * self.day), '2 years')

    def test_months(self) -> None:
        self.assertEqual(duration(730 * self.day), '23 months')
        self.assertEqual(duration(200 * self.day), '6 months')
        self.assertEqual(duration(61 * self.day), '2 months')

    def test_weeks(self) -> None:
        self.assertEqual(duration(60 * self.day), '8 weeks')
        self.assertEqual(duration(30 * self.day), '4 weeks')
        self.assertEqual(duration(14 * self.day), '2 weeks')

    def test_days(self) -> None:
        self.assertEqual(duration(13 * self.day), '13 days')
        self.assertEqual(duration(48 * self.hour), '2 days')

    def test_hours(self) -> None:
        self.assertEqual(duration(47 * self.hour), '47 hours')
        self.assertEqual(duration(120 * self.minute), '2 hours')

    def test_minutes(self) -> None:
        self.assertEqual(duration(119 * self.minute), '119 minutes')
        self.assertEqual(duration(13 * self.minute), '13 minutes')
        self.assertEqual(duration(120), '2 minutes')

    def test_seconds(self) -> None:
        self.assertEqual(duration(119), '119 seconds')
        self.assertEqual(duration(42), '42 seconds')

    def test_one(self) -> None:
        self.assertEqual(duration(1), '1 second')

    def test_zero(self) -> None:
        self.assertEqual(duration(0), '0 seconds')
