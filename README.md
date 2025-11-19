# Bank Transaction-Attachment Matching System

This repository holds the code for take home assignment done for AI engineer position. See [PROBLEM.md](PROBLEM.md) for the complete assignment details.

## Running the Application

```bash
python run.py
```

This will process the transactions and attachments from `src/data/` and output a report of matched pairs.

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

#### 2. There is a match for amount and counterparty only:

- 

Maximum total score: 1.15 | Acceptance threshold: 0.60

### 3. **Hard Filters (Rejection Criteria)**
To minimize false positives:
- **Amount mismatch**: If both amounts present but don't match → reject immediately
- **Weak name match**: If name score < 0.20 → reject immediately

These filters ensure no match is created on date/amount alone without reasonable counterparty alignment.

### 4. **Bidirectional Matching**
Both `find_attachment()` and `find_transaction()` use the same core logic through a generalized `_find_match()` function, ensuring consistent behavior in both directions.

### 5. **Intelligent Field Extraction**
- **Counterparty names**: Extracts from `issuer`, `supplier`, or `recipient` fields (handles both purchase and sales invoices)
- **Dates**: Considers all date fields (`due_date`, `invoicing_date`, etc.) to create a flexible matching range
- **Company detection**: Ignores "Example Company Oy" when it appears in attachments (represents the company itself)

## Technical Decisions

- **Deterministic**: Same input always produces same output (no randomness)
- **Token-based name matching**: Robust to spelling variations and business suffix differences
- **Defensive scoring**: Returns `None` when insufficient data exists rather than guessing
- **Modular design**: Separate functions for each matching component, enabling easy testing and modification

## Test Coverage

Run tests with:
```bash
python -m pytest tests/
```

