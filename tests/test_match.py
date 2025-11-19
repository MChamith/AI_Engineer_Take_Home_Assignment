from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.match import find_attachment, find_transaction


class TestMatchingScenarios(unittest.TestCase):
    """Scenario-based tests for transaction-attachment matching workflow.

    These tests validate the complete matching system including reference matching,
    scoring, threshold checking, and best candidate selection.
    """

    # =============================================================================
    # ACCEPTED SCENARIOS - Perfect Amount + Name Combinations
    # =============================================================================

    def test_scenario_perfect_amount_and_name_no_date(self):
        """Invoice matches transaction perfectly, but date field missing. Should be accepted."""
        transaction = {
            "id": 1001,
            "amount": 175.00,
            "contact": "John Doe Consulting",
            "reference": None,
            "date": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2001,
                "data": {
                    "total_amount": 175.00,
                    "issuer": "John Doe Consulting",
                    "reference": None,
                },
            },
            {
                "type": "invoice",
                "id": 2002,
                "data": {
                    "total_amount": 200.00,
                    "issuer": "Different Company",
                    "reference": None,
                },
            },
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2001)

    def test_scenario_perfect_amount_good_name_no_date(self):
        """Amount matches, names similar but not exact (business suffix difference). Should be accepted."""
        transaction = {
            "id": 1002,
            "amount": 200.00,
            "contact": "Doe Media",  # Missing "Oy" suffix
            "reference": None,
            "date": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2002,
                "data": {
                    "total_amount": 200.00,
                    "issuer": "Doe Media Oy",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2002)

    def test_scenario_perfect_amount_moderate_name_good_date(self):
        """Amount matches, name partially matches, payment 5 days late. Should be accepted."""
        transaction = {
            "id": 1003,
            "amount": 1000.00,
            "contact": "Best Supplies",  # Missing "EMEA"
            "date": "2024-07-30",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2003,
                "data": {
                    "total_amount": 1000.00,
                    "supplier": "Best Supplies EMEA",
                    "invoicing_date": "2024-07-05",
                    "due_date": "2024-07-25",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2003)

    def test_scenario_perfect_amount_moderate_name_late_date(self):
        """Amount matches, name partially matches, payment 10 days late. Should be accepted."""
        transaction = {
            "id": 1004,
            "amount": 35.00,
            "contact": "Matti",  # Only first name
            "date": "2024-07-31",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2004,
                "data": {
                    "total_amount": 35.00,
                    "supplier": "Matti Meikäläinen Tmi",
                    "invoicing_date": "2024-07-18",
                    "due_date": "2024-07-21",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2004)

    # =============================================================================
    # ACCEPTED SCENARIOS - Amount + Date (No Name)
    # =============================================================================

    def test_scenario_perfect_amount_and_date_no_name(self):
        """Transaction has no counterparty, but amount and date match perfectly. Should be accepted."""
        transaction = {
            "id": 1005,
            "amount": 50.00,
            "contact": None,
            "date": "2024-07-10",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2005,
                "data": {
                    "total_amount": 50.00,
                    "supplier": "City Utilities",
                    "invoicing_date": "2024-06-30",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2005)

    def test_scenario_perfect_amount_slightly_late_no_name(self):
        """Transaction has no counterparty, payment 2 days late. Should be accepted."""
        transaction = {
            "id": 1006,
            "amount": 324.10,
            "contact": None,
            "date": "2024-08-18",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2006,
                "data": {
                    "total_amount": 324.10,
                    "supplier": "Pinewood Ltd",
                    "invoicing_date": "2024-08-02",
                    "due_date": "2024-08-16",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2006)

    # =============================================================================
    # ACCEPTED SCENARIOS - Name + Date (No Amount)
    # =============================================================================

    def test_scenario_perfect_name_and_date_no_amount(self):
        """Amount missing from attachment, but name and date match perfectly. Should be accepted."""
        transaction = {
            "id": 1007,
            "amount": 250.00,
            "contact": "Unknown Customer",
            "date": "2024-08-15",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2007,
                "data": {
                    "total_amount": None,
                    "recipient": "Unknown Customer",
                    "invoicing_date": "2024-08-10",
                    "due_date": "2024-08-20",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2007)

    def test_scenario_perfect_name_slightly_late_no_amount(self):
        """Amount missing, name perfect, payment 2 days late. Should be accepted."""
        transaction = {
            "id": 1008,
            "amount": 120.00,
            "contact": "Office Mart",
            "date": "2024-08-18",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2008,
                "data": {
                    "total_amount": None,
                    "supplier": "Office Mart",
                    "invoicing_date": "2024-08-05",
                    "due_date": "2024-08-16",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2008)

    def test_scenario_perfect_name_moderate_delay_no_amount(self):
        """Amount missing, name perfect, payment 5 days late (threshold case). Should be accepted."""
        transaction = {
            "id": 1009,
            "amount": 88.88,
            "contact": "Random Vendor Oy",
            "date": "2024-08-15",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2009,
                "data": {
                    "total_amount": None,
                    "supplier": "Random Vendor Oy",
                    "invoicing_date": "2024-08-01",
                    "due_date": "2024-08-10",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2009)

    def test_scenario_good_name_perfect_date_no_amount(self):
        """Amount missing, names similar, date within range. Should be accepted."""
        transaction = {
            "id": 1010,
            "amount": 500.50,
            "contact": "Meta Corporation",
            "date": "2024-08-12",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2010,
                "data": {
                    "total_amount": None,
                    "supplier": "Meta Corp",
                    "invoicing_date": "2024-08-05",
                    "due_date": "2024-08-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2010)

    # =============================================================================
    # REJECTED SCENARIOS - Hard Filters
    # =============================================================================

    def test_scenario_amount_mismatch_hard_filter(self):
        """Amounts don't match, everything else perfect. Should be rejected."""
        transaction = {
            "id": 1011,
            "amount": 175.00,
            "contact": "John Doe Consulting",
            "date": "2024-06-16",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2011,
                "data": {
                    "total_amount": 200.00,  # Different amount
                    "issuer": "John Doe Consulting",
                    "invoicing_date": "2024-06-15",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)  # Should be rejected

    def test_scenario_weak_name_match_hard_filter(self):
        """Names completely different, amounts match. Should be rejected."""
        transaction = {
            "id": 1012,
            "amount": 175.00,
            "contact": "Completely Different Company Ltd",
            "date": "2024-06-16",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2012,
                "data": {
                    "total_amount": 175.00,
                    "issuer": "John Doe Consulting",
                    "invoicing_date": "2024-06-15",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)  # Should be rejected due to weak name

    # =============================================================================
    # REJECTED SCENARIOS - Below Threshold
    # =============================================================================

    def test_scenario_only_amount_and_weak_date(self):
        """Only amount matches with moderate late date, insufficient. Should be rejected."""
        transaction = {
            "id": 1013,
            "amount": 640.00,
            "contact": None,
            "date": "2024-09-05",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2013,
                "data": {
                    "total_amount": 640.00,
                    "issuer": "Northwind Imports",
                    "invoicing_date": "2024-08-01",
                    "due_date": "2024-08-31",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)  # Below threshold

    def test_scenario_perfect_name_very_late_no_amount(self):
        """Name matches, but payment too late and no amount to confirm. Should be rejected."""
        transaction = {
            "id": 1014,
            "amount": 310.00,
            "contact": "Global Traders",
            "date": "2024-06-22",
            "reference": None,
        }
        attachments = [
            {
                "type": "receipt",
                "id": 2014,
                "data": {
                    "total_amount": None,
                    "supplier": "Global Traders",
                    "receiving_date": "2024-06-12",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)  # Below threshold

    def test_scenario_good_name_moderate_date_no_amount(self):
        """Both fields moderate but not strong enough together. Should be rejected."""
        transaction = {
            "id": 1015,
            "amount": 100.00,
            "contact": "ABC",
            "date": "2024-08-10",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2015,
                "data": {
                    "total_amount": None,
                    "supplier": "ABC Corporation Limited",
                    "invoicing_date": "2024-08-01",
                    "due_date": "2024-08-05",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)  # Below threshold

    # =============================================================================
    # BEST CANDIDATE SELECTION
    # =============================================================================

    def test_scenario_best_candidate_selection(self):
        """Multiple potential matches exist, system should select the best one."""
        transaction = {
            "id": 1016,
            "amount": 175.00,
            "contact": "John Doe Consulting",
            "date": "2024-06-16",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2016,
                "data": {
                    "total_amount": 175.00,
                    "issuer": "John Doe",  # Partial name match
                    "invoicing_date": "2024-06-15",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            },
            {
                "type": "invoice",
                "id": 2017,
                "data": {
                    "total_amount": 175.00,
                    "issuer": "John Doe Consulting",  # Perfect name match
                    "invoicing_date": "2024-06-15",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            },
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2017)  # Should select the better match

    def test_scenario_no_candidates_above_threshold(self):
        """Multiple candidates exist but none above threshold. Should reject all."""
        transaction = {
            "id": 1017,
            "amount": 100.00,
            "contact": None,
            "date": "2024-10-01",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2018,
                "data": {
                    "total_amount": 100.00,
                    "issuer": "Company A",
                    "invoicing_date": "2024-08-01",
                    "due_date": "2024-08-15",  # Way too late
                    "reference": None,
                },
            },
            {
                "type": "invoice",
                "id": 2019,
                "data": {
                    "total_amount": 100.00,
                    "issuer": "Company B",
                    "invoicing_date": "2024-07-01",
                    "due_date": "2024-07-15",  # Way too late
                    "reference": None,
                },
            },
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)  # No candidate above threshold

    def test_scenario_multiple_same_supplier_select_best_date(self):
        """Multiple invoices from same supplier with same amount, should select the one with best date match."""
        transaction = {
            "id": 1025,
            "amount": 500.00,
            "contact": "TechSupply Ltd",
            "date": "2024-08-10",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2025,
                "data": {
                    "total_amount": 500.00,
                    "supplier": "TechSupply Ltd",
                    "invoicing_date": "2024-07-01",
                    "due_date": "2024-07-15",  # Old invoice, paid too late
                    "reference": None,
                },
            },
            {
                "type": "invoice",
                "id": 2026,
                "data": {
                    "total_amount": 500.00,
                    "supplier": "TechSupply Ltd",
                    "invoicing_date": "2024-08-01",
                    "due_date": "2024-08-12",  # Recent invoice, date within range
                    "reference": None,
                },
            },
            {
                "type": "invoice",
                "id": 2027,
                "data": {
                    "total_amount": 300.00,  # Different amount
                    "supplier": "ABC Ltd",
                    "invoicing_date": "2024-08-05",
                    "due_date": "2024-08-15",
                    "reference": None,
                },
            },
        ]

        result = find_attachment(transaction, attachments)
        self.assertEqual(result["id"], 2026)

    # =============================================================================
    # REFERENCE MATCHING - Bypasses Scoring
    # =============================================================================

    def test_scenario_reference_match_bypasses_scoring(self):
        """Exact reference match should find attachment immediately, regardless of other fields."""
        transaction = {
            "id": 1018,
            "amount": 175.00,
            "contact": "Jane Smith",
            "reference": "12345672",
            "date": "2024-06-16",
        }
        attachments = [
            {
                "type": "invoice",
                "id": 3001,
                "data": {
                    "total_amount": 999.99,  # Different amount
                    "recipient": "Different Person",  # Different name
                    "reference": "12345672",  # Same reference
                    "invoicing_date": "2024-01-01",
                    "due_date": "2024-01-15",
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 3001)  # Reference match bypasses scoring

    def test_scenario_reference_match_with_whitespace_and_zeros(self):
        """Reference matching should handle whitespace and leading zeros."""
        transaction = {
            "id": 1019,
            "amount": 200.00,
            "contact": "John Doe",
            "reference": "9876 543 2103",
            "date": "2024-06-17",
        }
        attachments = [
            {
                "type": "invoice",
                "id": 3002,
                "data": {
                    "total_amount": 200.00,
                    "issuer": "Doe Media Oy",
                    "reference": "0000098765432103",  # Leading zeros, no spaces
                    "invoicing_date": "2024-06-14",
                    "due_date": "2024-07-14",
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 3002)

    # =============================================================================
    # REVERSE MATCHING - find_transaction
    # =============================================================================

    def test_scenario_find_transaction_for_attachment(self):
        """Test reverse matching: finding transaction for an attachment."""
        attachment = {
            "type": "invoice",
            "id": 3003,
            "data": {
                "total_amount": 200.00,
                "supplier": "Jane Doe Design",
                "invoicing_date": "2024-06-18",
                "due_date": "2024-07-18",
                "reference": "5550001114",
            },
        }
        transactions = [
            {
                "id": 2003,
                "date": "2024-06-20",
                "amount": 200.00,
                "contact": "Jane Doe",
                "reference": "0000 0000 5550 0011 14",  # Same reference with formatting
            }
        ]

        result = find_transaction(attachment, transactions)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2003)

    def test_scenario_find_transaction_by_score_no_reference(self):
        """Test reverse matching without reference, based on scoring."""
        attachment = {
            "type": "invoice",
            "id": 3004,
            "data": {
                "total_amount": 50.00,
                "supplier": "City Utilities",
                "invoicing_date": "2024-06-30",
                "due_date": "2024-07-15",
                "reference": None,
            },
        }
        transactions = [
            {
                "id": 2004,
                "date": "2024-07-15",
                "amount": -50.00,  # Negative (outgoing payment)
                "contact": None,
                "reference": None,
            }
        ]

        result = find_transaction(attachment, transactions)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2004)

    # =============================================================================
    # EDGE CASES
    # =============================================================================

    def test_scenario_negative_amounts_should_match(self):
        """Negative transaction amounts should match positive invoice amounts."""
        transaction = {
            "id": 1020,
            "amount": -175.00,  # Negative (outgoing payment)
            "contact": "John Doe Consulting",
            "date": "2024-06-16",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2020,
                "data": {
                    "total_amount": 175.00,  # Positive (invoice)
                    "issuer": "John Doe Consulting",
                    "invoicing_date": "2024-06-15",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2020)

    def test_scenario_business_suffix_ignored_in_names(self):
        """Business suffixes (Oy, Ltd, Tmi) should be ignored in name matching."""
        transaction = {
            "id": 1021,
            "amount": 35.00,
            "contact": "Matti Meikäläinen",  # No Tmi
            "date": "2024-07-20",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2021,
                "data": {
                    "total_amount": 35.00,
                    "supplier": "Matti Meikäläinen Tmi",  # With Tmi
                    "invoicing_date": "2024-07-18",
                    "due_date": "2024-07-21",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2021)

    def test_scenario_empty_attachments_list(self):
        """System should handle empty attachments list gracefully."""
        transaction = {
            "id": 1022,
            "amount": 100.00,
            "contact": "Test Company",
            "date": "2024-08-01",
            "reference": None,
        }
        attachments = []

        result = find_attachment(transaction, attachments)
        self.assertIsNone(result)

    def test_scenario_multiple_counterparty_fields(self):
        """Attachment may have multiple counterparty fields (issuer, supplier, recipient)."""
        transaction = {
            "id": 1023,
            "amount": 150.00,
            "contact": "ACME Corporation",
            "date": "2024-08-10",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2023,
                "data": {
                    "total_amount": 150.00,
                    "issuer": "Different Company",
                    "recipient": "ACME Corporation",  # Match on recipient
                    "invoicing_date": "2024-08-05",
                    "due_date": "2024-08-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2023)

    def test_scenario_date_within_invoice_range(self):
        """Transaction date within invoice date range (between invoicing and due date)."""
        transaction = {
            "id": 1024,
            "amount": 100.00,
            "contact": "Test Supplier",
            "date": "2024-07-10",  # Between invoice and due date
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2024,
                "data": {
                    "total_amount": 100.00,
                    "supplier": "Test Supplier",
                    "invoicing_date": "2024-07-01",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2024)

    # =============================================================================
    # EXAMPLE COMPANY EDGE CASES
    # =============================================================================

    def test_scenario_match_with_example_company_only_on_amount_and_date(self):
        """Match when attachment has only Example Company Oy with perfect amount and date.
        
        Example Company Oy is filtered out, leaving no counterparty data.
        Should match based on amount + date (0.75 score > 0.60 threshold).
        """
        transaction = {
            "id": 1025,
            "amount": 500.00,
            "contact": "Different Company Ltd",
            "date": "2024-07-15",
            "reference": None,
        }
        attachments = [
            {
                "type": "invoice",
                "id": 2025,
                "data": {
                    "invoice_number": "INV-2025",
                    "total_amount": 500.00,
                    "issuer": "Example Company Oy",
                    "invoicing_date": "2024-07-15",
                    "due_date": "2024-07-15",
                    "reference": None,
                },
            }
        ]

        result = find_attachment(transaction, attachments)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], 2025)




if __name__ == "__main__":
    unittest.main()
