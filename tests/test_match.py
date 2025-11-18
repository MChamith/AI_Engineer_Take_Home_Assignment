from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import date
from src.match import _clean_reference, _get_attachment_reference, _score_amount_match, _attachment_dates, _date_match, AMOUNT_WEIGHT, AMOUNT_TOLERANCE


class TestCleanReference(unittest.TestCase):
    """Tests for _clean_reference function."""

    def test_returns_none_for_none(self):
        """Test that None input returns None."""
        self.assertIsNone(_clean_reference(None))

    def test_returns_none_for_empty_string(self):
        """Test that empty string returns None."""
        self.assertIsNone(_clean_reference(''))

    def test_returns_none_for_whitespace_only(self):
        """Test that whitespace-only strings return None."""
        self.assertIsNone(_clean_reference('   '))
        self.assertIsNone(_clean_reference('\n\t'))

    def test_returns_none_for_zeros_only(self):
        """Test that strings with only zeros return None."""
        self.assertIsNone(_clean_reference('000'))
        self.assertIsNone(_clean_reference('0 0 0'))
        self.assertIsNone(_clean_reference('0000000000'))

    def test_strips_whitespace_and_leading_zeros(self):
        """Test that whitespace and leading zeros are stripped."""
        self.assertEqual(_clean_reference('  00123  '), '123')
        self.assertEqual(_clean_reference('\t000abc'), 'abc')
        self.assertEqual(_clean_reference('ref001'), 'ref001')
        self.assertEqual(_clean_reference('0010200'), '10200')
        self.assertEqual(_clean_reference('  0 0 123 '), '123')
        self.assertEqual(_clean_reference('1234 56 7 890'), '1234567890')


class TestGetAttachmentReference(unittest.TestCase):
    """Tests for _get_attachment_reference function."""

    def test_returns_clean_reference(self):
        """Test that attachment reference is cleaned properly."""
        attachment = {
            'type': 'invoice',
            'id': 3001,
            'data': {
                'invoice_number': 'INV-1001',
                'reference': '  00012345672  ',
            },
        }
        self.assertEqual(_get_attachment_reference(attachment), '12345672')

    def test_returns_none_when_reference_missing(self):
        """Test that None is returned when reference is None."""
        attachment = {
            'type': 'invoice',
            'id': 3004,
            'data': {
                'invoice_number': 'PINV-3002',
                'reference': None,
            },
        }
        self.assertIsNone(_get_attachment_reference(attachment))

    def test_returns_none_when_data_missing(self):
        """Test that None is returned when data field is missing."""
        attachment = {
            'type': 'invoice',
            'id': 9999,
        }
        self.assertIsNone(_get_attachment_reference(attachment))


class TestScoreAmountMatch(unittest.TestCase):
    """Tests for _score_amount_match function."""

    def test_exact_match(self):
        """Test exact amount matches."""
        self.assertEqual(_score_amount_match(100.0, 100.0), AMOUNT_WEIGHT)
        self.assertEqual(_score_amount_match(0.0, 0.0), AMOUNT_WEIGHT)

    def test_at_tolerance_boundary(self):
        """Test amounts at tolerance boundary."""
        self.assertEqual(_score_amount_match(100.0, 100.01), AMOUNT_WEIGHT)
        self.assertEqual(_score_amount_match(100.0, 99.99), AMOUNT_WEIGHT)

    def test_within_tolerance(self):
        """Test amounts within tolerance."""
        self.assertEqual(_score_amount_match(100.0, 100.005), AMOUNT_WEIGHT)

    def test_outside_tolerance(self):
        """Test amounts outside tolerance."""
        self.assertEqual(_score_amount_match(100.0, 100.011), 0)
        self.assertEqual(_score_amount_match(100.0, 99.989), 0)
        self.assertEqual(_score_amount_match(100.0, 150.0), 0)

    def test_opposite_amounts(self):
        """Test negative amounts."""
        self.assertEqual(_score_amount_match(100.0, -100.005), AMOUNT_WEIGHT)
        self.assertEqual(_score_amount_match(100.0, -100.02), 0)

  


class TestAttachmentDates(unittest.TestCase):
    """Tests for _attachment_dates function."""

    def test_with_no_dates(self):
        """Test that empty list is returned when attachment has no date fields."""
        attachment = {
            'type': 'invoice',
            'id': 1001,
            'data': {
                'invoice_number': 'INV-001',
                'amount': 100.0,
            },
        }
        self.assertEqual(_attachment_dates(attachment), [])

    def test_with_single_date(self):
        """Test extraction of single date field."""
        attachment = {
            'type': 'invoice',
            'id': 1001,
            'data': {
                'invoice_date': '2024-01-10',
                'amount': 100.0,
            },
        }
        self.assertEqual(_attachment_dates(attachment), [date(2024, 1, 10)])

    def test_with_two_dates(self):
        """Test extraction of two date fields."""
        attachment = {
            'type': 'invoice',
            'id': 1001,
            'data': {
                'invoice_date': '2024-01-10',
                'due_date': '2024-01-25',
            },
        }
        self.assertEqual(_attachment_dates(attachment), [date(2024, 1, 10), date(2024, 1, 25)])

    def test_with_different_date_field_names(self):
        """Test extraction with various date field naming conventions."""
        attachment = {
            'type': 'receipt',
            'id': 2001,
            'data': {
                'receiving_date': '2024-02-15',
                'payment_date': '2024-02-20',
            },
        }
        self.assertEqual(_attachment_dates(attachment), [date(2024, 2, 15), date(2024, 2, 20)])


class TestScoreDateMatch(unittest.TestCase):
    """Tests for _date_match function."""

    def test_none_transaction_date(self):
        """Test that None transaction_date returns None."""
        attachment_dates = [date(2024, 1, 10), date(2024, 1, 20)]
        self.assertIsNone(_date_match(None, attachment_dates))

    def test_empty_attachment_dates(self):
        """Test that empty attachment_date list returns None."""
        transaction_date = date(2024, 1, 15)
        self.assertIsNone(_date_match(transaction_date, []))

    def test_more_than_14_days_returns_none(self):
        """Test more than 14 days from max date returns None."""
        transaction_date = date(2024, 2, 5)
        attachment_dates = [date(2024, 1, 10), date(2024, 1, 20)]
        self.assertIsNone(_date_match(transaction_date, attachment_dates))


if __name__ == '__main__':
    unittest.main()
