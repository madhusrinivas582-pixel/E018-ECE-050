
import sys
import os
import unittest
from decimal import Decimal

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from value_parser import (
    parse_value,
    check_tolerance,
    get_sample_size,
    get_acceptance_number,
    get_lot_decision,
    evaluate_lot,
    is_beyond_three_x_tolerance
)


class TestValueParser(unittest.TestCase):

    def test_engineering_suffixes(self):
       self.assertEqual(parse_value("4.7k"), Decimal("4700"))
       self.assertEqual(parse_value("0.0047M"), Decimal("4700"))
       self.assertEqual(parse_value("8u"), Decimal("8e-6"))
       self.assertEqual(parse_value("3p"), Decimal("3e-12"))

    def test_invalid_values(self):
        invalid_values = [
            "--", "1O0n", "1k2", "4.7.2",
            "1,000", "100ohm", "1e3"
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_value(value)

    def test_tolerance(self):
        self.assertEqual(check_tolerance(95, 100, 5), "IN")
        self.assertEqual(check_tolerance(105, 100, 5), "IN")
        self.assertEqual(check_tolerance(110, 100, 5), "OUT")

    def test_sample_size(self):
        self.assertEqual(get_sample_size(500), 20)
        self.assertEqual(get_sample_size(1500), 50)
        self.assertEqual(get_sample_size(3200), 50)
        self.assertEqual(get_sample_size(4000), 80)

    def test_acceptance_number(self):
        self.assertEqual(get_acceptance_number(20), 1)
        self.assertEqual(get_acceptance_number(50), 3)
        self.assertEqual(get_acceptance_number(80), 5)

    def test_lot_decision(self):
        self.assertEqual(get_lot_decision(1, 1), "ACCEPTED")
        self.assertEqual(get_lot_decision(3, 1), "SCREEN_100")
        self.assertEqual(get_lot_decision(4, 1), "REJECTED")

    def test_insufficient_samples(self):
        result = evaluate_lot(50, 46, 45, 1, 0)
        self.assertEqual(result, ("HELD", "INSUFFICIENT_SAMPLE"))

    def test_wrong_value_suspected(self):
        self.assertTrue(
            is_beyond_three_x_tolerance(116, 100, 5)
        )
        self.assertFalse(
            is_beyond_three_x_tolerance(115, 100, 5)
        )


if __name__ == "__main__":
    unittest.main()
