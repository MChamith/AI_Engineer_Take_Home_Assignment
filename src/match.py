from datetime import date, datetime
from typing import Callable, TypeVar


Attachment = dict[str, dict]
Transaction = dict[str, dict]
#TODO Remove typevar
T = TypeVar('T', Attachment, Transaction)

AMOUNT_TOLERANCE = 0.01
AMOUNT_WEIGHT = 5
DATE_WEIGHT = 5
COUNTERPARTY_WEIGHT = 5
OVERDUE_TOLERANCE = 14


def find_attachment(
    transaction: Transaction,
    attachments: list[Attachment],
) -> Attachment | None:
    """Find the best matching attachment for a given transaction."""
    #TODO: reference number is transaction is assumed to be always present
    primary_reference = _clean_reference(transaction.get('reference'))
    return None


def find_transaction(
    attachment: Attachment,
    transactions: list[Transaction],
) -> Transaction | None:
    """Find the best matching transaction for a given attachment."""
    # TODO: Implement me
    primary_reference = _get_attachment_reference(attachment)
    print('attachment', attachment)
    print('transactions', transactions)
    return None

def _clean_reference(reference: str | None) -> str | None:
    """Clean the reference number by removing whitespace and leading zeros."""
    if not reference or not isinstance(reference, str):
        return None
    cleaned_reference = ''.join(reference.split())
    cleaned_reference = cleaned_reference.lstrip('0')
    return cleaned_reference or None

def _get_attachment_reference(attachment: Attachment) -> str | None:
    """Get the reference number for a given attachment."""
    reference = attachment.get('data', {}).get('reference')
    return _clean_reference(reference)

def _score_amount_match(transaction_amount: float, attachment_amount: float) -> float:
    """Score the amount match between a transaction and an attachment."""
    # Round to avoid floating-point precision issues with monetary amounts
    difference = round(abs(abs(transaction_amount) - abs(attachment_amount)), 3)
    if difference <= AMOUNT_TOLERANCE:
        return AMOUNT_WEIGHT
    return 0

def _attachment_dates(attachment: Attachment) -> list[date]:
    """Extract date values from attachment data fields containing 'date' in their key name.
    
    Assumes all date-related fields have 'date' substring in the key (e.g., 'due_date', 
    'invoicing_date', 'receiving_date' , etc.).
    
    Returns a list of parsed date objects. If no date fields are found, returns an empty list.
    """
    dates: list[date] = []
    data = attachment.get('data', {})

    if not isinstance(data, dict):
        return dates
    
    for key, value in data.items():
        if 'date' in key.lower():
            parsed_date = _parse_date(value)
            if parsed_date:
                dates.append(parsed_date)
    
    return dates

def _date_match(transaction_date: date, attachment_date: list[date]) -> float | None:
    """Score how strongly the transaction date matches the attachment date range.
    
    Returns:
        2: transaction date is within the attachment date range or within 14 days of max date
        None: transaction date is more than 14 days from max date (due date) or invalid inputs
    """
    if transaction_date is None or not attachment_date:
        return None
    
    min_date = max_date = attachment_date[0]
    for d in attachment_date[1:]:
        if d < min_date:
            min_date = d
        elif d > max_date:
            max_date = d

    # Check if transaction date is within the attachment date range
    if min_date <= transaction_date <= max_date:
        return 2.0
    
    # Check if within 14 days of max date (due date)
    days_diff = abs((transaction_date - max_date).days)
    return 2.0 if days_diff <= OVERDUE_TOLERANCE else None

# def _name_match(contact: str, attachment: Attachment) -> float | None:

def _parse_date(date_str: str | None) -> date | None:
    """Parse a date string into a date object in YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, AttributeError):
        return None


def _find_match(
    primary_item: T,
    primary_reference: str | None,
    candidate_reference_fn: Callable[[T], str | None],
    candidate_list: list[T],
) -> T | None:
    """Find the best match for a given primary item and reference. If an exact match for reference is found, return the candidate."""
    if primary_reference:
        for candidate in candidate_list:
            candidate_reference = candidate_reference_fn(candidate)
            if candidate_reference == primary_reference:
                return candidate

    best_score = float('-inf')
    best_candidate: T | None = None
    
    return None
