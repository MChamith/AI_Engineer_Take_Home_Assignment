from datetime import date, datetime
from typing import Callable, Optional


Attachment = dict[str, dict]
Transaction = dict[str, dict]

AMOUNT_TOLERANCE = 0.01
AMOUNT_WEIGHT = 5
DATE_WEIGHT = 5
COUNTERPARTY_WEIGHT = 5
OVERDUE_TOLERANCE = 14
EXAMPLE_COMPANY_NAME = "Example Company Oy"


def find_attachment(
    transaction: Transaction,
    attachments: list[Attachment],
) -> Attachment | None:
    """Find the best matching attachment for a given transaction."""

    primary_reference = _clean_reference(transaction.get("reference"))
    return _find_match(
        primary_item=transaction,
        primary_reference=primary_reference,
        candidate_reference_fn=_get_attachment_reference,
        candidate_list=attachments,
        score_fn=lambda candidate: _score_pair(transaction, candidate),
    )


def find_transaction(
    attachment: Attachment,
    transactions: list[Transaction],
) -> Transaction | None:
    """Find the best matching transaction for a given attachment."""
    primary_reference = _get_attachment_reference(attachment)
    return _find_match(
        primary_item=attachment,
        primary_reference=primary_reference,
        candidate_reference_fn=lambda tx: _clean_reference(tx.get("reference")),
        candidate_list=transactions,
        score_fn=lambda candidate: _score_pair(candidate, attachment),
    )


def _clean_reference(reference: Optional[str]) -> Optional[str]:
    """Clean the reference number by removing whitespace and leading zeros."""
    if not reference or not isinstance(reference, str):
        return None
    cleaned_reference = "".join(reference.split())
    cleaned_reference = cleaned_reference.lstrip("0")
    return cleaned_reference or None


def _get_attachment_reference(attachment: Attachment) -> Optional[str]:
    """Get the reference number for a given attachment."""
    reference = attachment.get("data", {}).get("reference")
    return _clean_reference(reference)


def _score_amount_match(transaction_amount: float, attachment_amount: float) -> float:
    """Score the amount match between a transaction and an attachment."""
    # Round to avoid floating-point precision issues with monetary amounts
    difference = round(abs(abs(transaction_amount) - abs(attachment_amount)), 3)
    if difference <= AMOUNT_TOLERANCE:
        return 0.35
    return 0


def _attachment_dates(attachment: Attachment) -> list[date]:
    """Extract date values from attachment data fields containing 'date' in their key name.

    Assumes all date-related fields have 'date' substring in the key (e.g., 'due_date',
    'invoicing_date', 'receiving_date' , etc.).

    Returns a list of parsed date objects. If no date fields are found, returns an empty list.
    """
    dates: list[date] = []
    data = attachment.get("data", {})

    if not isinstance(data, dict):
        return dates

    for key, value in data.items():
        if "date" in key.lower():
            parsed_date = _parse_date(value)
            if parsed_date:
                dates.append(parsed_date)

    return dates


def _date_match(transaction_date: date, attachment_date: list[date]) -> Optional[float]:
    """Score transaction date proximity to attachment date range.
    Returns score between 0 and 0.40 according to the difference
    in days between the transaction date and the attachment date range."""
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
        return 0.40

    # Calculate days after the max date (due date)
    days_diff = abs((transaction_date - max_date).days)
    if days_diff <= 3:
        return 0.30
    elif days_diff <= 7:
        return 0.20
    elif days_diff <= 14:
        return 0.10
    else:
        return 0.0


def _normalize_text(text: Optional[str]) -> Optional[str]:
    """Normalize a name by removing whitespace and converting to lowercase."""
    if not text or not isinstance(text, str):
        return None
    return text.lower().strip()


def _is_example_company(name: str) -> bool:
    """Check if a name is the example company name."""
    return _normalize_text(name) == _normalize_text(EXAMPLE_COMPANY_NAME)


def _tokenize_name(name: str) -> set[str]:
    """Tokenize and normalize a name, removing business suffixes (Oy, Tmi, Ltd, etc.)."""

    business_suffixes = {
        "oy",
        "ab",
        "oyj",
        "tmi",
        "ltd",
        "llc",
        "inc",
        "corp",
        "gmbh",
        "sa",
        "sas",
        "as",
        "bv",
        "nv",
        "ag",
        "spa",
        "oy.",
        "ab.",
        "ltd.",
        "inc.",
        "corp.",
    }

    normalized = _normalize_text(name)
    tokens = normalized.split()
    stripped_tokens = [token.rstrip(".,;:") for token in tokens]
    filtered_tokens = {t for t in stripped_tokens if t not in business_suffixes}

    return filtered_tokens


def _token_based_match(name1: Optional[str], name2: Optional[str]) -> Optional[float]:
    """Score name similarity using token comparison (removes business suffixes).
    Returns between 0 and 0.4 based on the similarity score."""
    if (
        not name1
        or not isinstance(name1, str)
        or not name2
        or not isinstance(name2, str)
    ):
        return None

    tokens1 = _tokenize_name(name1)
    tokens2 = _tokenize_name(name2)

    # Exact token set match
    if tokens1 == tokens2:
        return 0.40

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    similarity = len(intersection) / len(union) if union else 0

    if similarity >= 0.8:
        return 0.40
    elif similarity >= 0.6:
        return 0.30
    elif similarity >= 0.4:
        return 0.20
    else:
        return 0.0


def _counterparty_names(attachment: Attachment) -> list[str]:
    """Extract counterparty names from attachment data fields."""
    potential_fields = ["issuer", "supplier", "recipient"]
    names: list[str] = []
    data = attachment.get("data", {})
    if not isinstance(data, dict):
        return names
    for key, value in data.items():
        if key.lower() in potential_fields:
            names.append(value)
    return names


def _parse_date(date_str: str | None) -> date | None:
    """Parse a date string into a date object in YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _score_pair(transaction: Transaction, attachment: Attachment) -> Optional[float]:
    """Score the match between a transaction and an attachment.

    Returns a score based on amount, date, and counterparty name matching.
    Scoring weights: Amount (0.35), Name (0.40), Date (0.40). Total max: 1.15
    Acceptance threshold: 0.60

    Hard filters:
    - Amount mismatch (if both present) → reject immediately
    - Name score < 0.20 (if present) → reject immediately

    Returns None if not enough data is present to make a meaningful comparison.
    """
    amount_score: Optional[float] = None
    date_score: Optional[float] = None
    name_score: Optional[float] = None

    # Score amount match - HARD FILTER
    transaction_amount = transaction.get("amount")
    attachment_amount = attachment.get("data", {}).get("total_amount")
    if transaction_amount is not None and attachment_amount is not None:
        amount_score = _score_amount_match(transaction_amount, attachment_amount)
        # If amounts are present but don't match, reject immediately
        if amount_score == 0:
            return None

    # Score counterparty name match
    transaction_counterparty = transaction.get("contact")
    attachment_counterparties = _counterparty_names(attachment)

    if transaction_counterparty:
        best_name_score = None
        for attachment_counterparty in attachment_counterparties:
            score = _token_based_match(
                transaction_counterparty, attachment_counterparty
            )
            if score is not None and (
                best_name_score is None or score > best_name_score
            ):
                best_name_score = score
        name_score = best_name_score

    # If name score is too low, reject immediately - HARD FILTER
    # This guarantees that whether the date or amount match,
    # if the name match is weak, the match is rejected.
    if name_score is not None and name_score < 0.20:
        return None

    # Score date match
    transaction_date_str = transaction.get("date")
    transaction_date = (
        _parse_date(transaction_date_str) if transaction_date_str else None
    )
    attachment_dates = _attachment_dates(attachment)
    if transaction_date and attachment_dates:
        date_score = _date_match(transaction_date, attachment_dates)

    # Combine scores - only add non-None scores
    total_score = 0.0

    if amount_score is not None:
        total_score += amount_score

    if date_score is not None:
        total_score += date_score

    if name_score is not None:
        total_score += name_score

    return total_score


def _find_match(
    primary_item: Attachment | Transaction,
    primary_reference: Optional[str],
    candidate_reference_fn: Callable[[Attachment | Transaction], Optional[str]],
    candidate_list: list[Attachment | Transaction],
    score_fn: Callable[[Attachment | Transaction], Optional[float]],
) -> Attachment | Transaction | None:
    """Find the best match for a given primary item and reference. If an exact match for reference is found, return the candidate."""
    if primary_reference:
        for candidate in candidate_list:
            candidate_reference = candidate_reference_fn(candidate)
            if candidate_reference == primary_reference:
                return candidate

    name_matched: bool = False
    best_score = -float("inf")
    best_candidate: Optional[Attachment | Transaction] = None

    for candidate in candidate_list:
        score = score_fn(candidate)
        if score is not None and score > best_score:
            best_score = score
            best_candidate = candidate
    if best_candidate and best_score > 0.6:
        return best_candidate

    return None
