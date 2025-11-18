"""
Side-by-side comparison viewer for transaction-attachment matching.
Shows detailed comparison of expected matching pairs.
"""

import json
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher


def fuzzy_match_names(name1: str | None, name2: str | None, threshold: float = 0.8) -> tuple[bool, float]:
    """
    Compare two names using fuzzy string matching.
    
    Args:
        name1: First name to compare
        name2: Second name to compare
        threshold: Minimum similarity ratio (0-1) to consider a match
    
    Returns:
        tuple: (is_match: bool, similarity_score: float)
            - is_match: True if similarity >= threshold
            - similarity_score: Similarity ratio between 0 and 1
    """
    # Handle None values
    if not name1 or not name2:
        return (False, 0.0)
    
    # Normalize names
    name1_clean = name1.lower().strip()
    name2_clean = name2.lower().strip()
    
    # Exact match after normalization
    if name1_clean == name2_clean:
        return (True, 1.0)
    
    # Calculate sequence similarity
    sequence_ratio = SequenceMatcher(None, name1_clean, name2_clean).ratio()
    
    # Check if one name contains the other (handles cases like "John Doe" vs "John Doe Consulting")
    containment_score = 0.0
    if name1_clean in name2_clean or name2_clean in name1_clean:
        # Calculate what percentage the shorter name is of the longer
        shorter_len = min(len(name1_clean), len(name2_clean))
        longer_len = max(len(name1_clean), len(name2_clean))
        containment_score = shorter_len / longer_len
    
    # Use the higher of the two scores
    final_score = max(sequence_ratio, containment_score)
    
    is_match = final_score >= threshold
    return (is_match, round(final_score, 3))


def clean_reference(reference: str | None) -> str | None:
    """Clean the reference number by removing whitespace and leading zeros."""
    if not reference or not isinstance(reference, str):
        return None
    cleaned_reference = ''.join(reference.split())
    cleaned_reference = cleaned_reference.lstrip('0')
    return cleaned_reference or None


def load_data():
    """Load transactions and attachments from JSON files."""
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    
    with open(data_dir / "transactions.json", "r", encoding="utf-8") as f:
        transactions = json.load(f)
    
    with open(data_dir / "attachments.json", "r", encoding="utf-8") as f:
        attachments = json.load(f)
    
    # Convert to dictionaries for easy lookup
    transactions_dict = {tx["id"]: tx for tx in transactions}
    attachments_dict = {att["id"]: att for att in attachments}
    
    return transactions_dict, attachments_dict


def get_counterparty_name(attachment: dict) -> str:
    """Extract counterparty name from attachment (issuer, supplier, or recipient)."""
    data = attachment.get("data", {})
    return data.get("issuer") or data.get("supplier") or data.get("recipient") or "N/A"


def get_attachment_reference(attachment: dict) -> str | None:
    """Get the reference number from attachment."""
    return attachment.get("data", {}).get("reference")


def compare_amounts(tx_amount: float, att_amount: float) -> tuple[bool, str]:
    """Compare transaction and attachment amounts."""
    # Transaction amounts are negative for payments
    tx_abs = abs(tx_amount)
    att_abs = abs(att_amount)
    diff = abs(tx_abs - att_abs)
    
    match = diff <= 0.01
    status = "✓ MATCH" if match else f"✗ DIFF: {diff:.2f}"
    return match, status


def compare_dates(tx_date_str: str, attachment: dict) -> tuple[bool, str, list]:
    """Compare transaction date with attachment date range."""
    tx_date = datetime.strptime(tx_date_str, '%Y-%m-%d').date()
    
    # Extract all dates from attachment
    att_dates = []
    data = attachment.get("data", {})
    for key, value in data.items():
        if 'date' in key.lower() and value:
            try:
                att_dates.append(datetime.strptime(value, '%Y-%m-%d').date())
            except (ValueError, AttributeError):
                pass
    
    if not att_dates:
        return False, "✗ NO DATES", []
    
    min_date = min(att_dates)
    max_date = max(att_dates)
    
    # Check if transaction date is within the attachment date range
    if min_date <= tx_date <= max_date:
        return True, "✓ IN RANGE", att_dates
    
    # Calculate difference from max date (due date)
    days_diff = abs((tx_date - max_date).days)
    
    if days_diff <= 14:
        return True, f"✓ WITHIN 14d ({days_diff}d)", att_dates
    else:
        return False, f"✗ {days_diff} days", att_dates


def compare_references(tx_ref: str | None, att_ref: str | None) -> tuple[bool, str]:
    """Compare transaction and attachment references."""
    tx_clean = clean_reference(tx_ref)
    att_clean = clean_reference(att_ref)
    
    if not tx_clean and not att_clean:
        return None, "⚠ BOTH NULL"
    
    if not tx_clean:
        return None, "⚠ TX NULL"
    
    if not att_clean:
        return None, "⚠ ATT NULL"
    
    match = tx_clean == att_clean
    status = "✓ MATCH" if match else "✗ DIFFERENT"
    return match, status


def compare_counterparties(tx_contact: str | None, att_counterparty: str | None) -> tuple[bool, str]:
    """Compare transaction contact with attachment counterparty."""
    if not tx_contact and not att_counterparty:
        return None, "⚠ BOTH NULL"
    
    if not tx_contact:
        return None, "⚠ TX NULL"
    
    if not att_counterparty:
        return None, "⚠ ATT NULL"
    
    is_match, score = fuzzy_match_names(tx_contact, att_counterparty, threshold=0.8)
    status = f"✓ MATCH ({score:.2f})" if is_match else f"✗ NO MATCH ({score:.2f})"
    return is_match, status


def print_divider(char="=", length=120):
    """Print a divider line."""
    print(char * length)


def print_comparison_header():
    """Print the header for comparison table."""
    print_divider("=")
    print("SIDE-BY-SIDE COMPARISON OF MATCHING PAIRS")
    print_divider("=")


def print_pair_comparison(tx: dict, att: dict, pair_num: int):
    """Print detailed comparison of a transaction-attachment pair."""
    print(f"\n{'='*120}")
    print(f"PAIR #{pair_num}: Transaction {tx['id']} ↔ Attachment {att['id']}")
    print(f"{'='*120}")
    
    # Extract data
    tx_date = tx.get("date")
    tx_amount = tx.get("amount")
    tx_contact = tx.get("contact")
    tx_ref = tx.get("reference")
    
    att_counterparty = get_counterparty_name(att)
    att_amount = att.get("data", {}).get("total_amount")
    att_ref = get_attachment_reference(att)
    att_type = att.get("type")
    att_invoice_num = att.get("data", {}).get("invoice_number") or att.get("data", {}).get("receipt_number")
    
    # Perform comparisons
    ref_match, ref_status = compare_references(tx_ref, att_ref)
    amount_match, amount_status = compare_amounts(tx_amount, att_amount)
    date_match, date_status, att_dates = compare_dates(tx_date, att)
    counterparty_match, counterparty_status = compare_counterparties(tx_contact, att_counterparty)
    
    # Print side-by-side
    print(f"\n{'FIELD':<20} {'TRANSACTION':<40} {'ATTACHMENT':<40} {'STATUS':<20}")
    print("-" * 120)
    
    print(f"{'ID':<20} {tx['id']:<40} {att['id']:<40}")
    print(f"{'Type':<20} {'Transaction':<40} {att_type:<40}")
    
    print("-" * 120)
    
    # Reference
    tx_ref_display = f"{tx_ref} → {clean_reference(tx_ref)}" if tx_ref else "None"
    att_ref_display = f"{att_ref} → {clean_reference(att_ref)}" if att_ref else "None"
    print(f"{'Reference':<20} {tx_ref_display:<40} {att_ref_display:<40} {ref_status:<20}")
    
    # Amount
    tx_amount_display = f"{tx_amount:.2f}"
    att_amount_display = f"{att_amount:.2f}" if att_amount else "N/A"
    print(f"{'Amount':<20} {tx_amount_display:<40} {att_amount_display:<40} {amount_status:<20}")
    
    # Date
    att_dates_str = ", ".join([str(d) for d in att_dates]) if att_dates else "N/A"
    print(f"{'Date':<20} {tx_date:<40} {att_dates_str:<40} {date_status:<20}")
    
    # Counterparty
    tx_contact_display = tx_contact if tx_contact else "None"
    print(f"{'Contact/Party':<20} {tx_contact_display:<40} {att_counterparty:<40} {counterparty_status:<20}")
    
    # Additional info
    print(f"{'Invoice/Receipt #':<20} {'N/A':<40} {att_invoice_num if att_invoice_num else 'N/A':<40}")
    
    # Summary
    print("\n" + "-" * 120)
    print("MATCHING SUMMARY:")
    match_count = sum([bool(m) for m in [ref_match, amount_match, date_match, counterparty_match] if m is not None])
    total_fields = sum([1 for m in [ref_match, amount_match, date_match, counterparty_match] if m is not None])
    
    if ref_match:
        print("  ✓ Reference matches (STRONG SIGNAL)")
    if amount_match:
        print("  ✓ Amount matches")
    if date_match:
        print("  ✓ Date matches")
    if counterparty_match:
        print("  ✓ Counterparty matches")
    
    print(f"\nTotal matching fields: {match_count}/{total_fields}")


def main():
    """Main function to display all matching pairs."""
    # Expected matches from run.py
    EXPECTED_TX_TO_ATTACHMENT = {
        2001: 3001,
        2002: 3002,
        2003: 3003,
        2004: 3004,
        2005: 3005,
        2006: None,
        2007: 3006,
        2008: 3007,
        2009: None,
        2010: None,
        2011: None,
        2012: None,
    }
    
    # Load data
    transactions, attachments = load_data()
    
    print_comparison_header()
    print(f"\nTotal Transactions: {len(transactions)}")
    print(f"Total Attachments: {len(attachments)}")
    print(f"Expected Matches: {sum(1 for v in EXPECTED_TX_TO_ATTACHMENT.values() if v is not None)}")
    print(f"Unmatched Transactions: {sum(1 for v in EXPECTED_TX_TO_ATTACHMENT.values() if v is None)}")
    
    # Show matching pairs
    pair_num = 1
    for tx_id, att_id in EXPECTED_TX_TO_ATTACHMENT.items():
        if att_id is not None:
            tx = transactions[tx_id]
            att = attachments[att_id]
            print_pair_comparison(tx, att, pair_num)
            pair_num += 1
    
    # Show unmatched transactions
    print(f"\n\n{'='*120}")
    print("UNMATCHED TRANSACTIONS")
    print(f"{'='*120}")
    
    for tx_id, att_id in EXPECTED_TX_TO_ATTACHMENT.items():
        if att_id is None:
            tx = transactions[tx_id]
            print(f"\nTransaction {tx_id}:")
            print(f"  Date: {tx.get('date')}")
            print(f"  Amount: {tx.get('amount'):.2f}")
            print(f"  Contact: {tx.get('contact') or 'None'}")
            print(f"  Reference: {tx.get('reference') or 'None'}")
    
    # Show unmatched attachments
    matched_att_ids = set(v for v in EXPECTED_TX_TO_ATTACHMENT.values() if v is not None)
    unmatched_attachments = [att_id for att_id in attachments.keys() if att_id not in matched_att_ids]
    
    print(f"\n\n{'='*120}")
    print("UNMATCHED ATTACHMENTS")
    print(f"{'='*120}")
    
    for att_id in unmatched_attachments:
        att = attachments[att_id]
        print(f"\nAttachment {att_id} ({att.get('type')}):")
        data = att.get('data', {})
        print(f"  Invoice/Receipt #: {data.get('invoice_number') or data.get('receipt_number') or 'N/A'}")
        print(f"  Amount: {data.get('total_amount', 'N/A')}")
        print(f"  Counterparty: {get_counterparty_name(att)}")
        print(f"  Reference: {get_attachment_reference(att) or 'None'}")
        dates = [v for k, v in data.items() if 'date' in k.lower() and v]
        if dates:
            print(f"  Dates: {', '.join(dates)}")
    
    print(f"\n{'='*120}\n")


if __name__ == "__main__":
    main()

