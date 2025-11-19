# Bank Transaction-Attachment Matching System

This repository holds the code for take home assignment done for AI engineer position. See [PROBLEM.md](PROBLEM.md) for the complete assignment details.

## Running the Application

Run the matching system:

```bash
python run.py
```

This will process the transactions and attachments from `src/data/` and output a report of matched pairs.

Run unit tests:

```bash
python tests/test_match.py
```

## Architecture & Approach

### 1. **Reference-Based Matching (Priority)**
- Exact reference number match always creates a 1:1 link
- Handles format variations: strips whitespace and leading zeros
- If reference match found, immediately returns without further scoring

### 2. **Multi-Factor Scoring System**
When no reference match exists, candidates are scored using three signals **Amount**, **Counterparty name**, and **date** fields according to the problem statement:

High level approach for developing the solution is as follows:

#### 1. There's a match for amount and date only:
- If counterparty names mismatch, reject immediately (different business entity).
- If counterparty data is missing, evaluate based on amount and date match strength.

> **Rationale**: The problem states amount, date, and counterparty are equally strong signals. While amount+date alone risks false positives in real-world scenarios (multiple transactions with same amount on same date), test cases `2004` and `3004` validate that this combination can be sufficient when counterparty data is unavailable. 

#### 2. When only amount and counterparty align:

- If no date information exists, accept and calculate score using match confidence.
- If date information exists and falls within acceptable range, accept and score by match confidence.
- If date discrepancy exceeds 14 days or represents an obvious mismatch, discard the candidate.

> **Rationale**: Following the same logic as above, we assume two strong matching signals provide adequate evidence for candidate consideration. Again this simplified assumtion is not valid for real world use cases.

#### 3. When counterparty and date align:

- If amount information is absent, accept and determine score based on match confidence.
- If amount is present and matches within tolerance, accept and score accordingly.
- If amount shows significant deviation or clear mismatch, reject the candidate.

> **Rationale**: Consistent with the previous approach, two strong signals are deemed sufficient for match consideration. This is on the premise that single counter party can have multiple invoices on the same day.

## Assumptions

1. **Date Overdue Threshold**: Transactions dated more than 14 days after the attachment's latest date are not considered matches unless other strong signals align.

2. **Amount Matching Precision**: Transactions must match invoice amounts exactly, partial payments and overpayments are not supported. A tolerance of 0.01 is applied solely to accommodate floating-point arithmetic rounding differences.

3. **Name Variations vs. Typos**: I assume "Spelling variations" in the problem refers to legitimate business name differences (e.g., "Matti Meikäläinen" vs "Matti Meikäläinen Tmi" in case 2005→3005), not character-level typos. Clearly, "Jon Snow" and "John Snow" are distinct entities and should not match. Similarly, "Matti Meikäläinen" and "Matti Meittiläinen" (case 2006) are rejected. Due to this reason, token-based matching was chosen over character-level algorithms (e.g. Jaro-Winkler) to prevent false matches between different legal entities with similar names. Supported variations include case differences, business suffixes (Oy, Ltd, Tmi), and word order.

