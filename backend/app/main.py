"""SpendSense REST API."""

import os
from typing import Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db
from .categoriser import CATEGORIES, Categoriser
from .parser import StatementParseError, parse_statement

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB is far more than any statement needs

app = FastAPI(title="SpendSense", description="Bank statement analyser with automatic categorisation")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_categoriser = None


def get_conn():
    """One SQLite connection per request.

    FastAPI runs requests on a thread pool, and sharing a single SQLite
    connection between threads can lock up. A fresh connection is cheap.
    """
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def get_categoriser():
    global _categoriser
    if _categoriser is None:
        _categoriser = Categoriser()
    return _categoriser


class CategoryUpdate(BaseModel):
    category: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/categories")
def categories():
    return CATEGORIES


@app.post("/api/import")
async def import_statement(
    file: UploadFile = File(...),
    conn=Depends(get_conn),
    categoriser: Categoriser = Depends(get_categoriser),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File is too large (max 5 MB)")

    try:
        parsed = parse_statement(content)
    except (StatementParseError, UnicodeDecodeError) as exc:
        raise HTTPException(422, f"Could not read this statement: {exc}") from exc

    user_rules = db.get_user_rules(conn)
    rows = []
    for tx in parsed:
        category, source, confidence, review = categoriser.categorise(tx["description"], tx["amount"], user_rules)
        rows.append({**tx, "category": category, "source": source,
                     "confidence": round(confidence, 3), "needs_review": review})

    import_id, inserted, duplicates = db.insert_import(conn, file.filename, rows)
    return {
        "import_id": import_id,
        "inserted": inserted,
        "duplicates_skipped": duplicates,
        "needs_review": sum(r["needs_review"] for r in rows),
    }


@app.get("/api/transactions")
def transactions(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    category: Optional[str] = None,
    needs_review: Optional[bool] = None,
    conn=Depends(get_conn),
):
    return db.list_transactions(conn, month, category, needs_review)


@app.patch("/api/transactions/{tx_id}")
def set_category(tx_id: int, body: CategoryUpdate, conn=Depends(get_conn)):
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category. Choose one of: {', '.join(CATEGORIES)}")
    result = db.update_category(conn, tx_id, body.category)
    if result is None:
        raise HTTPException(404, "Transaction not found")
    row, relabelled = result
    return {"transaction": row, "also_relabelled": relabelled}


@app.get("/api/summary")
def summary(month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"), conn=Depends(get_conn)):
    return {**db.summary(conn, month), "top_merchants": db.top_merchants(conn, month)}


@app.get("/api/trends")
def trends(conn=Depends(get_conn)):
    return db.monthly_trend(conn)


@app.get("/api/months")
def months(conn=Depends(get_conn)):
    return db.months(conn)


@app.delete("/api/data")
def reset(conn=Depends(get_conn)):
    db.reset(conn)
    return {"status": "cleared"}
