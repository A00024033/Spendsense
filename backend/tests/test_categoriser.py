import pytest

from app.categoriser import Categoriser, merchant_key, normalise


@pytest.fixture(scope="module")
def cat():
    return Categoriser()


def test_normalise_strips_prefixes_dates_and_numbers():
    assert normalise("CARD PAYMENT TO TESCO STORES 3021 ON 12-10") == "TESCO STORES"
    assert normalise("contactless pret a manger") == "PRET A MANGER"


def test_strips_card_reader_prefixes():
    assert normalise("SQ *JOES FALAFEL") == "JOES FALAFEL"
    assert normalise("ZETTLE_*THE BREW ROOM") == "THE BREW ROOM"
    assert merchant_key("SUMUP *VINTAGE CLOTHING 22") == "VINTAGE CLOTHING"


def test_merchant_key_is_stable_across_noise():
    assert merchant_key("TESCO STORES 3021 LONDON") == merchant_key("CARD PAYMENT TO TESCO STORES ON 01-02")


def test_rules_win_and_longest_keyword_first(cat):
    assert cat.categorise("BOOTS PHARMACY 123", -8)[:2] == ("Health", "rule")
    assert cat.categorise("BOOTS 123", -8)[:2] == ("Shopping", "rule")


def test_user_rule_beats_everything(cat):
    rules = {merchant_key("TESCO STORES 99"): "Shopping"}
    assert cat.categorise("TESCO STORES 42", -20, rules)[:2] == ("Shopping", "user")


def test_ml_handles_unseen_independent_business(cat):
    category, source, confidence, _ = cat.categorise("NEPTUNE PIZZERIA SW4", -14)
    assert (category, source) == ("Eating Out", "ml")
    assert 0 <= confidence <= 1


def test_money_in_from_unknown_source_is_income(cat):
    category, _, _, review = cat.categorise("NEPTUNE PIZZERIA SW4", 14)
    assert category == "Income" and review is True


def test_gibberish_is_flagged_for_review(cat):
    category, _, _, review = cat.categorise("XQZ 7781 PLK", -5)
    assert review is True
