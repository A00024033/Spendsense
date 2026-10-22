import pytest

from app.parser import StatementParseError, parse_money, parse_statement


def test_signed_amount_format():
    csv = "Date,Name,Amount\n01/10/2026,TESCO STORES,-12.50\n02/10/2026,SALARY,1500.00\n"
    rows = parse_statement(csv)
    assert rows == [
        {"date": "2026-10-01", "description": "TESCO STORES", "amount": -12.5},
        {"date": "2026-10-02", "description": "SALARY", "amount": 1500.0},
    ]


def test_paid_in_paid_out_format():
    csv = "Transaction Date,Transaction Description,Paid out,Paid in\n2026-10-01,TFL TRAVEL,4.20,\n2026-10-02,REFUND,,10.00\n"
    rows = parse_statement(csv)
    assert [r["amount"] for r in rows] == [-4.2, 10.0]


def test_handles_bom_pound_signs_commas_and_blank_lines():
    csv = "﻿Date,Description,Amount\n01/10/2026,RENT,\"-£1,200.00\"\n\n"
    rows = parse_statement(csv.encode("utf-8"))
    assert rows[0]["amount"] == -1200.0


def test_collapses_whitespace_in_description():
    rows = parse_statement("Date,Name,Amount\n01/10/2026,  PRET   A MANGER  ,-3\n")
    assert rows[0]["description"] == "PRET A MANGER"


@pytest.mark.parametrize("value,expected", [("(12.50)", -12.5), ("", 0.0), ("£3", 3.0), ("1,000.01", 1000.01)])
def test_parse_money(value, expected):
    assert parse_money(value) == expected


def test_missing_columns_is_a_clear_error():
    with pytest.raises(StatementParseError, match="date and description"):
        parse_statement("foo,bar\n1,2\n")


def test_bad_date_reports_line_number():
    with pytest.raises(StatementParseError, match="Line 3"):
        parse_statement("Date,Name,Amount\n01/10/2026,A,-1\nnot a date,B,-2\n")


def test_empty_file():
    with pytest.raises(StatementParseError):
        parse_statement("Date,Name,Amount\n")
