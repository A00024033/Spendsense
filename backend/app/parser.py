"""Parse bank statement CSV files into a common format.

UK banks all export CSVs slightly differently: different column names,
date formats, and some use one signed "Amount" column while others use
separate "Paid in" / "Paid out" columns. This module detects the layout
from the header row so the rest of the app only ever sees:

    {"date": "YYYY-MM-DD", "description": str, "amount": float}

Spending is negative, income is positive.
"""

import csv
import io
from datetime import datetime

DATE_COLUMNS = ["date", "transaction date", "posted date", "posting date", "completed date"]
DESCRIPTION_COLUMNS = [
    "description", "transaction description", "name", "merchant",
    "counter party", "payee", "memo", "reference", "details",
]
AMOUNT_COLUMNS = ["amount", "amount (gbp)", "value", "amount(gbp)"]
OUT_COLUMNS = ["paid out", "money out", "debit", "debit amount", "withdrawals"]
IN_COLUMNS = ["paid in", "money in", "credit", "credit amount", "deposits"]

DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%d/%m/%y", "%d.%m.%Y"]


class StatementParseError(ValueError):
    """Raised when a CSV cannot be understood as a bank statement."""


def _find_column(headers, candidates):
    """Return the original header that matches one of the candidate names."""
    normalised = {h.strip().lower(): h for h in headers if h}
    for name in candidates:
        if name in normalised:
            return normalised[name]
    return None


def parse_date(value):
    value = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise StatementParseError(f"Unrecognised date format: {value!r}")


def parse_money(value):
    """Turn strings like '£1,234.50', '-12.00' or '' into a float."""
    if value is None:
        return 0.0
    cleaned = value.strip().replace("£", "").replace(",", "").replace(" ", "")
    if cleaned in ("", "-"):
        return 0.0
    # Some banks write negatives as (12.50)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError as exc:
        raise StatementParseError(f"Unrecognised amount: {value!r}") from exc


def parse_statement(content):
    """Parse CSV text and return a list of transaction dicts."""
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []

    date_col = _find_column(headers, DATE_COLUMNS)
    desc_col = _find_column(headers, DESCRIPTION_COLUMNS)
    amount_col = _find_column(headers, AMOUNT_COLUMNS)
    out_col = _find_column(headers, OUT_COLUMNS)
    in_col = _find_column(headers, IN_COLUMNS)

    if not date_col or not desc_col:
        raise StatementParseError(
            f"Could not find date and description columns in headers: {headers}"
        )
    if not amount_col and not (out_col or in_col):
        raise StatementParseError(
            f"Could not find an amount column (or paid in / paid out) in headers: {headers}"
        )

    transactions = []
    for line_no, row in enumerate(reader, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue  # skip blank lines
        try:
            if amount_col:
                amount = parse_money(row.get(amount_col))
            else:
                amount = parse_money(row.get(in_col)) - parse_money(row.get(out_col))
            transactions.append({
                "date": parse_date(row[date_col]),
                "description": " ".join((row[desc_col] or "").split()),
                "amount": round(amount, 2),
            })
        except StatementParseError as exc:
            raise StatementParseError(f"Line {line_no}: {exc}") from exc

    if not transactions:
        raise StatementParseError("The file has no transactions")
    return transactions
