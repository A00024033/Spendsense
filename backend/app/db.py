"""SQLite storage, written in plain SQL (no ORM) so every query is visible."""

import hashlib
import os
import sqlite3
from contextlib import contextmanager

from .categoriser import merchant_key

DB_PATH = os.environ.get("SPENDSENSE_DB", os.path.join(os.path.dirname(__file__), "..", "data", "spendsense.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS imports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    row_count   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id    INTEGER REFERENCES imports(id) ON DELETE CASCADE,
    date         TEXT NOT NULL,           -- ISO format YYYY-MM-DD
    description  TEXT NOT NULL,
    amount       REAL NOT NULL,           -- negative = money out
    category     TEXT NOT NULL,
    source       TEXT NOT NULL CHECK (source IN ('rule', 'ml', 'user')),
    confidence   REAL NOT NULL,
    needs_review INTEGER NOT NULL DEFAULT 0,
    fingerprint  TEXT NOT NULL UNIQUE     -- stops the same row being imported twice
);

CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);

-- When a user corrects a category, we remember it for that merchant
CREATE TABLE IF NOT EXISTS user_rules (
    merchant_key TEXT PRIMARY KEY,
    category     TEXT NOT NULL
);
"""


def connect(path=None):
    conn = sqlite3.connect(path or DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # readers do not block the writer
    # Make our Python merchant_key() callable from inside SQL queries
    conn.create_function("merchant_key", 1, merchant_key, deterministic=True)
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn):
    """Commit if everything worked, roll back if anything failed."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def fingerprint(tx, occurrence):
    """Same date, description and amount = same transaction.

    `occurrence` separates genuinely repeated rows (two identical coffees
    on the same day) within one file.
    """
    raw = f"{tx['date']}|{tx['description']}|{tx['amount']:.2f}|{occurrence}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_user_rules(conn):
    return {r["merchant_key"]: r["category"] for r in conn.execute("SELECT * FROM user_rules")}


def insert_import(conn, filename, rows):
    """Insert categorised rows; returns (import_id, inserted, duplicates)."""
    with transaction(conn):
        cur = conn.execute("INSERT INTO imports (filename, row_count) VALUES (?, ?)", (filename, len(rows)))
        import_id = cur.lastrowid
        inserted = 0
        seen = {}
        for tx in rows:
            base = (tx["date"], tx["description"], tx["amount"])
            seen[base] = seen.get(base, 0) + 1
            cur = conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (import_id, date, description, amount, category, source, confidence, needs_review, fingerprint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (import_id, tx["date"], tx["description"], tx["amount"], tx["category"], tx["source"],
                 tx["confidence"], int(tx["needs_review"]), fingerprint(tx, seen[base])),
            )
            inserted += cur.rowcount
        conn.execute("UPDATE imports SET row_count = ? WHERE id = ?", (inserted, import_id))
    return import_id, inserted, len(rows) - inserted


def list_transactions(conn, month=None, category=None, needs_review=None, limit=500):
    sql = "SELECT * FROM transactions WHERE 1 = 1"
    params = []
    if month:
        sql += " AND strftime('%Y-%m', date) = ?"
        params.append(month)
    if category:
        sql += " AND category = ?"
        params.append(category)
    if needs_review is not None:
        sql += " AND needs_review = ?"
        params.append(int(needs_review))
    sql += " ORDER BY date DESC, id DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def update_category(conn, tx_id, category):
    """Correct one transaction and learn from it.

    1. Set the category on this transaction.
    2. Save a user rule for its merchant, so future imports get it right.
    3. Relabel the merchant's other rows that the system guessed. Rows the
       user already set by hand are left alone.
    All three happen in one database transaction.
    Returns (updated_row, number_of_other_rows_relabelled), or None.
    """
    with transaction(conn):
        row = conn.execute("SELECT description FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if row is None:
            return None
        key = merchant_key(row["description"])
        conn.execute(
            "UPDATE transactions SET category = ?, source = 'user', confidence = 1.0, needs_review = 0 WHERE id = ?",
            (category, tx_id),
        )
        conn.execute(
            "INSERT INTO user_rules (merchant_key, category) VALUES (?, ?) "
            "ON CONFLICT(merchant_key) DO UPDATE SET category = excluded.category",
            (key, category),
        )
        cur = conn.execute(
            "UPDATE transactions SET category = ?, source = 'user', confidence = 1.0, needs_review = 0 "
            "WHERE merchant_key(description) = ? AND source != 'user'",
            (category, key),
        )
        relabelled = cur.rowcount
    return dict(conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,)).fetchone()), relabelled


def summary(conn, month=None):
    where, params = ("WHERE strftime('%Y-%m', date) = ?", [month]) if month else ("", [])
    totals = conn.execute(
        f"""SELECT
                COALESCE(SUM(CASE WHEN amount > 0 AND category != 'Transfers' THEN amount END), 0) AS income,
                COALESCE(-SUM(CASE WHEN amount < 0 AND category != 'Transfers' THEN amount END), 0) AS spending,
                COUNT(*) AS count,
                COALESCE(SUM(needs_review), 0) AS needs_review
            FROM transactions {where}""",
        params,
    ).fetchone()
    by_category = conn.execute(
        f"""SELECT category, ROUND(-SUM(amount), 2) AS total, COUNT(*) AS count
            FROM transactions
            {where + ' AND' if where else 'WHERE'} amount < 0 AND category != 'Transfers'
            GROUP BY category
            ORDER BY total DESC""",
        params,
    ).fetchall()
    return {
        "income": round(totals["income"], 2),
        "spending": round(totals["spending"], 2),
        "net": round(totals["income"] - totals["spending"], 2),
        "count": totals["count"],
        "needs_review": totals["needs_review"],
        "by_category": [dict(r) for r in by_category],
    }


def monthly_trend(conn):
    rows = conn.execute(
        """SELECT strftime('%Y-%m', date) AS month, category, ROUND(-SUM(amount), 2) AS total
           FROM transactions
           WHERE amount < 0 AND category != 'Transfers'
           GROUP BY month, category
           ORDER BY month"""
    ).fetchall()
    return [dict(r) for r in rows]


def months(conn):
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) FROM transactions ORDER BY 1 DESC")]


def top_merchants(conn, month=None, limit=5):
    where, params = ("AND strftime('%Y-%m', date) = ?", [month]) if month else ("", [])
    rows = conn.execute(
        f"""SELECT merchant_key(description) AS merchant, category,
                   ROUND(-SUM(amount), 2) AS total, COUNT(*) AS visits
            FROM transactions
            WHERE amount < 0 AND category NOT IN ('Transfers', 'Rent', 'Bills') {where}
            GROUP BY merchant, category
            ORDER BY total DESC
            LIMIT ?""",
        params + [limit],
    ).fetchall()
    return [dict(r) for r in rows]


def reset(conn):
    with transaction(conn):
        conn.execute("DELETE FROM transactions")
        conn.execute("DELETE FROM imports")
        conn.execute("DELETE FROM user_rules")
