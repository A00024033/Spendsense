"""Hybrid transaction categoriser: rules first, machine learning second.

Order of decisions for each transaction:
  1. User rules     : the user corrected this merchant before, so trust them.
  2. Keyword rules  : well known UK merchants (TESCO, TFL, NETFLIX...).
  3. ML classifier  : TF-IDF on characters and words + logistic regression,
                      for merchants the rules have never seen.
  4. Low confidence : if the model is unsure, mark it "Other" and flag it
                      for review instead of guessing.

Rules are fast, exact and explainable; the model generalises to new
merchants ("THE GOLDEN DRAGON RESTAURANT" looks like eating out even if
we have never seen it). Combining them gets the best of both.
"""

import csv
import re
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRAINING_FILE = DATA_DIR / "training.csv"
MODEL_FILE = DATA_DIR / "model.joblib"

CATEGORIES = [
    "Groceries", "Eating Out", "Transport", "Bills", "Shopping", "Entertainment",
    "Health", "Rent", "Income", "Transfers", "Other",
]
CONFIDENCE_THRESHOLD = 0.45

# Longer, more specific keywords are checked first, so "BOOTS PHARMACY"
# becomes Health before the shorter "BOOTS" makes it Shopping.
KEYWORD_RULES = {
    "Groceries": ["TESCO", "SAINSBURY", "ASDA", "ALDI", "LIDL", "WAITROSE", "MORRISONS",
                  "OCADO", "ICELAND FOODS", "M&S SIMPLY FOOD", "CO-OP GROUP FOOD"],
    "Eating Out": ["PRET A MANGER", "STARBUCKS", "COSTA COFFEE", "CAFFE NERO", "MCDONALDS",
                   "NANDOS", "WAGAMAMA", "DELIVEROO", "UBER EATS", "JUST EAT", "GREGGS"],
    "Transport": ["TFL", "UBER *TRIP", "UBER TRIP", "TRAINLINE", "BOLT.EU", "NATIONAL EXPRESS",
                  "LIME *RIDE", "SOUTH WESTERN RAILWAY"],
    "Bills": ["THAMES WATER", "BRITISH GAS", "OCTOPUS ENERGY", "EDF ENERGY", "VIRGIN MEDIA",
              "VODAFONE", "COUNCIL TAX", "TV LICENCE", "GIFFGAFF"],
    "Shopping": ["AMAZON.CO.UK", "AMZN MKTP", "ARGOS", "PRIMARK", "IKEA", "ASOS", "BOOTS"],
    "Entertainment": ["NETFLIX", "SPOTIFY", "DISNEY PLUS", "STEAM GAMES", "PUREGYM",
                      "ODEON", "CINEWORLD", "AMAZON PRIME"],
    "Health": ["BOOTS PHARMACY", "LLOYDS PHARMACY", "SPECSAVERS", "NHS PRESCRIPTION"],
    "Rent": ["RENT PAYMENT", "OPENRENT", "UNITE STUDENTS"],
    "Income": ["SALARY", "PAYROLL", "STUDENT FINANCE", "HMRC REFUND"],
    "Transfers": ["TRANSFER TO SAVINGS", "MONZO POT", "ATM WITHDRAWAL"],
}
_SORTED_RULES = sorted(
    ((kw, cat) for cat, kws in KEYWORD_RULES.items() for kw in kws),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_PREFIXES = re.compile(r"^(CARD PAYMENT TO|CONTACTLESS|DD|DIRECT DEBIT|POS)\s+")
# Card readers used by small shops put their own name first: "SQ *JOES FALAFEL"
_PROCESSORS = re.compile(r"^(SQ|SUMUP|ZETTLE_?|IZ)\s*\*\s*")
_DATE_SUFFIX = re.compile(r"\bON \d{2}-\d{2}\b")
_NOISE = re.compile(r"[^A-Z&*.\s]")
_STOP_TOKENS = {"GB", "UK", "REF", "LONDON", "LTD"}


def normalise(description):
    """Strip payment prefixes, dates, numbers and noise from a description."""
    text = description.upper().strip()
    text = _PREFIXES.sub("", text)
    text = _PROCESSORS.sub("", text)
    text = _DATE_SUFFIX.sub("", text)
    text = _NOISE.sub(" ", text)
    return " ".join(text.split())


def merchant_key(description):
    """A short stable key for a merchant, used to remember user corrections."""
    tokens = [t for t in normalise(description).replace("*", " ").split()
              if t not in _STOP_TOKENS and len(t) > 1]
    return " ".join(tokens[:2])


def build_model():
    features = FeatureUnion([
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), token_pattern=r"[A-Z&]{2,}",
                                  lowercase=False)),
    ])
    return Pipeline([
        ("features", features),
        ("clf", LogisticRegression(max_iter=2000, C=5.0)),
    ])


def load_training_data(path=TRAINING_FILE):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    texts = [normalise(r["description"]) for r in rows]
    labels = [r["category"] for r in rows]
    groups = [r["merchant"] for r in rows]
    kinds = [r.get("kind", "brand") for r in rows]
    return texts, labels, groups, kinds


class Categoriser:
    def __init__(self, model=None):
        self.model = model or self._load_or_train()

    @staticmethod
    def _load_or_train():
        if MODEL_FILE.exists():
            return joblib.load(MODEL_FILE)
        texts, labels, _, _ = load_training_data()
        model = build_model().fit(texts, labels)
        joblib.dump(model, MODEL_FILE)
        return model

    @staticmethod
    def match_rule(description):
        text = normalise(description)
        for keyword, category in _SORTED_RULES:
            if keyword in text:
                return category
        return None

    def predict_ml(self, description):
        probs = self.model.predict_proba([normalise(description)])[0]
        best = probs.argmax()
        return str(self.model.classes_[best]), float(probs[best])

    def categorise(self, description, amount, user_rules=None):
        """Return (category, source, confidence, needs_review)."""
        key = merchant_key(description)
        if user_rules and key in user_rules:
            return user_rules[key], "user", 1.0, False

        rule = self.match_rule(description)
        if rule:
            return rule, "rule", 1.0, False

        category, confidence = self.predict_ml(description)

        # Money coming in is almost never groceries or shopping. Unless the
        # model is sure it is a transfer, treat it as income.
        if amount > 0 and category not in ("Income", "Transfers"):
            return "Income", "ml", confidence, True

        if confidence < CONFIDENCE_THRESHOLD:
            return "Other", "ml", confidence, True
        return category, "ml", confidence, False
