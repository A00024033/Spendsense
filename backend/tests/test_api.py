import pytest
from fastapi.testclient import TestClient

from app import db, main

STATEMENT = (
    "Date,Name,Amount\n"
    "01/10/2026,STUDENT FINANCE,2000.00\n"
    "02/10/2026,UNITE STUDENTS RENT,-800.00\n"
    "03/10/2026,TESCO STORES 3021,-25.00\n"
    "03/10/2026,TESCO STORES 3021,-25.00\n"   # a genuine second identical purchase
    "04/10/2026,NEPTUNE PIZZERIA,-15.00\n"
    "05/10/2026,TRANSFER TO SAVINGS,-100.00\n"
    "06/11/2026,NEPTUNE PIZZERIA,-12.00\n"
)


@pytest.fixture
def client(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    main.app.dependency_overrides[main.get_conn] = lambda: conn
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def upload(client, text=STATEMENT, name="statement.csv"):
    return client.post("/api/import", files={"file": (name, text, "text/csv")})


def test_import_and_summary(client):
    r = upload(client)
    assert r.status_code == 200
    assert r.json()["inserted"] == 7

    s = client.get("/api/summary", params={"month": "2026-10"}).json()
    assert s["income"] == 2000.0
    assert s["spending"] == 865.0           # transfers are not spending
    assert s["net"] == 1135.0
    by_cat = {c["category"]: c["total"] for c in s["by_category"]}
    assert by_cat["Rent"] == 800.0 and by_cat["Groceries"] == 50.0


def test_reimporting_the_same_file_skips_duplicates(client):
    upload(client)
    r = upload(client).json()
    assert r["inserted"] == 0 and r["duplicates_skipped"] == 7


def test_correction_relabels_merchant_and_is_learned(client):
    upload(client)
    pizza = client.get("/api/transactions", params={"month": "2026-10", "category": "Eating Out"}).json()[0]

    r = client.patch(f"/api/transactions/{pizza['id']}", json={"category": "Entertainment"}).json()
    assert r["transaction"]["source"] == "user"
    assert r["also_relabelled"] == 1        # the November pizza too

    upload(client, "Date,Name,Amount\n01/12/2026,NEPTUNE PIZZERIA,-9.00\n", "dec.csv")
    dec = client.get("/api/transactions", params={"month": "2026-12"}).json()[0]
    assert dec["category"] == "Entertainment" and dec["source"] == "user"


def test_rejects_unknown_category(client):
    upload(client)
    tx = client.get("/api/transactions").json()[0]
    assert client.patch(f"/api/transactions/{tx['id']}", json={"category": "Crypto"}).status_code == 400


def test_missing_transaction_is_404(client):
    assert client.patch("/api/transactions/9999", json={"category": "Other"}).status_code == 404


def test_bad_files_are_rejected_clearly(client):
    assert upload(client, "hello", "notes.txt").status_code == 400
    r = upload(client, "a,b\n1,2\n")
    assert r.status_code == 422 and "date and description" in r.json()["detail"]


def test_invalid_month_format(client):
    assert client.get("/api/summary", params={"month": "October"}).status_code == 422


def test_trends_and_months(client):
    upload(client)
    assert client.get("/api/months").json() == ["2026-11", "2026-10"]
    trend = client.get("/api/trends").json()
    assert {"month": "2026-11", "category": "Eating Out", "total": 12.0} in trend
