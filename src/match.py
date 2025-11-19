from datetime import date, datetime
from typing import Callable, Optional


Attachment = dict[str, dict]
Transaction = dict[str, dict]

# Tolerance and thresholds
AMOUNT_TOLERANCE = 0.01
EXAMPLE_COMPANY_NAME = "Example Company Oy"

# Scoring weights
AMOUNT_MATCH_SCORE = 0.35
NAME_EXACT_MATCH_SCORE = 0.40
NAME_GOOD_MATCH_SCORE = 0.30
NAME_FAIR_MATCH_SCORE = 0.20
DATE_EXACT_MATCH_SCORE = 0.40
DATE_CLOSE_MATCH_SCORE = 0.30
DATE_RECENT_MATCH_SCORE = 0.20
DATE_ACCEPTABLE_MATCH_SCORE = 0.10

# Name matching thresholds
NAME_MINIMUM_SCORE_THRESHOLD = 0.20
TOKEN_SIMILARITY_EXCELLENT = 0.8
TOKEN_SIMILARITY_GOOD = 0.6
TOKEN_SIMILARITY_FAIR = 0.4

# Overall acceptance threshold
ACCEPTANCE_THRESHOLD = 0.60


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
        return AMOUNT_MATCH_SCORE
    return 0


def _attachment_dates(attachment: Attachment) -> list[date]:
    """Extract date values from attachment data fields containing 'date' in their key name.
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
    Returns score between 0 and DATE_EXACT_MATCH_SCORE according to the difference
    in days between the transaction date and the attachment date range."""
    if transaction_date is None or not attachment_date:
        return None

    # Find the date range from attachment dates
    min_date = min(attachment_date)
    max_date = max(attachment_date)

    # Check if transaction date is within the attachment date range
    if min_date <= transaction_date <= max_date:
        return DATE_EXACT_MATCH_SCORE

    # Calculate days after the max date (due date)
    days_diff = abs((transaction_date - max_date).days)
    if days_diff <= 3:
        return DATE_CLOSE_MATCH_SCORE
    elif days_diff <= 7:
        return DATE_RECENT_MATCH_SCORE
    elif days_diff <= 14:
        return DATE_ACCEPTABLE_MATCH_SCORE
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
    Returns between 0 and NAME_EXACT_MATCH_SCORE based on the similarity score."""
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
        return NAME_EXACT_MATCH_SCORE

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2
    similarity = len(intersection) / len(union) if union else 0

    if similarity >= TOKEN_SIMILARITY_EXCELLENT:
        return NAME_EXACT_MATCH_SCORE
    elif similarity >= TOKEN_SIMILARITY_GOOD:
        return NAME_GOOD_MATCH_SCORE
    elif similarity >= TOKEN_SIMILARITY_FAIR:
        return NAME_FAIR_MATCH_SCORE
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
            if not _is_example_company(value):
                names.append(value)
    return names


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string into a date object in YYYY-MM-DD format."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def _score_amount(transaction: Transaction, attachment: Attachment) -> Optional[float]:
    """Score the amount match between transaction and attachment.

    Returns None if either amount is missing, 0 if amounts don't match,
    or AMOUNT_MATCH_SCORE if they match within tolerance.
    """
    transaction_amount = transaction.get("amount")
    attachment_amount = attachment.get("data", {}).get("total_amount")

    if transaction_amount is None or attachment_amount is None:
        return None

    return _score_amount_match(transaction_amount, attachment_amount)


def _score_counterparty(
    transaction: Transaction, attachment: Attachment
) -> Optional[float]:
    """Score the counterparty name match between transaction and attachment.

    Compares the transaction contact against all counterparty names in the attachment,
    returning the best match score or None if no transaction counterparty exists.
    """
    transaction_counterparty = transaction.get("contact")
    if not transaction_counterparty:
        return None

    attachment_counterparties = _counterparty_names(attachment)
    if not attachment_counterparties:
        return None

    best_name_score = None

    for attachment_counterparty in attachment_counterparties:
        score = _token_based_match(transaction_counterparty, attachment_counterparty)
        if score is not None and (best_name_score is None or score > best_name_score):
            best_name_score = score

    return best_name_score


def _score_date(transaction: Transaction, attachment: Attachment) -> Optional[float]:
    """Score the date match between transaction and attachment.

    Returns None if either date is missing, or a score based on date proximity.
    """
    transaction_date_str = transaction.get("date")
    transaction_date = (
        _parse_date(transaction_date_str) if transaction_date_str else None
    )

    if not transaction_date:
        return None

    attachment_dates = _attachment_dates(attachment)
    if not attachment_dates:
        return None

    return _date_match(transaction_date, attachment_dates)


def _score_pair(transaction: Transaction, attachment: Attachment) -> Optional[float]:
    """Score the match between a transaction and an attachment.

    Returns a score based on amount, date, and counterparty name matching.
    Scoring weights: Amount (0.35), Name (0.40), Date (0.40). Total max: 1.15
    Acceptance threshold: 0.60

    Hard filters:
    - Amount mismatch (if both present) → reject immediately
    - Name score < NAME_MINIMUM_SCORE_THRESHOLD (if present) → reject immediately

    Returns None if not enough data is present to make a meaningful comparison.
    """

    # Score amount match - HARD FILTER
    amount_score = _score_amount(transaction, attachment)
    if amount_score is not None and amount_score == 0:
        # If amounts are present but don't match, reject immediately
        return None

    # Score counterparty name match - HARD FILTER
    name_score = _score_counterparty(transaction, attachment)
    if name_score is not None and name_score < NAME_MINIMUM_SCORE_THRESHOLD:
        # If name score is too low, reject immediately
        return None

    # Score date match
    date_score = _score_date(transaction, attachment)

    # Combine scores - only add non-None scores
    total_score = 0.0
    if amount_score is not None:
        total_score += amount_score
    if date_score is not None:
        total_score += date_score
    if name_score is not None:
        total_score += name_score

    return total_score


def _find_exact_reference_match(
    primary_reference: Optional[str],
    candidate_reference_fn: Callable[[Attachment | Transaction], Optional[str]],
    candidate_list: list[Attachment | Transaction],
) -> Attachment | Transaction | None:
    """Find an exact reference match in the candidate list.

    Returns the first candidate with a matching reference number, or None if no match found.
    """
    if not primary_reference:
        return None

    for candidate in candidate_list:
        candidate_reference = candidate_reference_fn(candidate)
        if candidate_reference == primary_reference:
            return candidate

    return None


def _find_best_score_match(
    candidate_list: list[Attachment | Transaction],
    score_fn: Callable[[Attachment | Transaction], Optional[float]],
) -> Attachment | Transaction | None:
    """Find the best scoring match from the candidate list.

    Returns the candidate with the highest score above ACCEPTANCE_THRESHOLD,
    or None if no candidate meets the threshold.
    """
    best_score = -float("inf")
    best_candidate: Optional[Attachment | Transaction] = None

    for candidate in candidate_list:
        score = score_fn(candidate)
        if score is not None and score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate and best_score >= ACCEPTANCE_THRESHOLD:
        return best_candidate

    return None


def _find_match(
    primary_item: Attachment | Transaction,
    primary_reference: Optional[str],
    candidate_reference_fn: Callable[[Attachment | Transaction], Optional[str]],
    candidate_list: list[Attachment | Transaction],
    score_fn: Callable[[Attachment | Transaction], Optional[float]],
) -> Attachment | Transaction | None:
    """Find the best match for a given primary item.

    First attempts to find an exact reference match. If found, returns immediately.
    Otherwise, performs score-based matching using amount, date, and name similarity.
    """
    # Try exact reference match first
    exact_match = _find_exact_reference_match(
        primary_reference, candidate_reference_fn, candidate_list
    )
    if exact_match is not None:
        return exact_match

    # Fall back to score-based matching
    return _find_best_score_match(candidate_list, score_fn)
