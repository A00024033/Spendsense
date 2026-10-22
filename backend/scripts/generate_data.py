"""Generate labelled training data and a sample bank statement.

Real bank descriptions are messy: store numbers, locations, card payment
prefixes, dates. This script builds realistic descriptions from merchant
lists and templates, so the classifier learns to cope with that noise.

Run:  python scripts/generate_data.py
Writes: data/training.csv and ../sample_data/sample_statement.csv
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent

MERCHANTS = {
    "Groceries": [
        "TESCO STORES", "TESCO EXPRESS", "SAINSBURYS S/MKTS", "SAINSBURYS LOCAL", "ASDA SUPERSTORE",
        "ALDI", "LIDL GB", "WAITROSE", "MORRISONS", "CO-OP GROUP FOOD", "M&S SIMPLY FOOD",
        "ICELAND FOODS", "OCADO RETAIL", "WHOLE FOODS MARKET", "BOOTHS", "COSTCO WHOLESALE",
        "GREENGROCER LTD", "CORNER MINI MARKET", "HALAL BUTCHERS", "FRESH FOOD MARKET",
        "SUPERMARKET EXPRESS", "THE FARM SHOP", "ORGANIC GROCERY",
    ],
    "Eating Out": [
        "PRET A MANGER", "STARBUCKS", "COSTA COFFEE", "CAFFE NERO", "MCDONALDS", "KFC",
        "NANDOS", "WAGAMAMA", "DELIVEROO", "UBER EATS", "JUST EAT", "GREGGS", "LEON",
        "FIVE GUYS", "BURGER KING", "PIZZA EXPRESS", "DISHOOM", "ITSU", "WASABI", "TACO BELL",
        "THE GOLDEN DRAGON RESTAURANT", "BELLA ITALIA RESTAURANT", "CORNER CAFE",
        "THE RED LION PUB", "SUSHI BAR", "KEBAB HOUSE", "ESPRESSO BAR", "NOODLE KITCHEN",
        "BURGER JOINT", "PIZZERIA NAPOLI", "THE COFFEE HOUSE", "BAKERY AND CAFE",
    ],
    "Transport": [
        "TFL TRAVEL CH", "TFL CYCLE HIRE", "UBER *TRIP", "BOLT.EU", "TRAINLINE", "LNER",
        "GWR", "SOUTH WESTERN RAILWAY", "NATIONAL EXPRESS", "SHELL", "BP", "ESSO",
        "TEXACO", "LIME *RIDE", "ADDISON LEE", "FREENOW", "MEGABUS", "AVANTI WEST COAST",
        "CITY PARKING", "NCP CAR PARK", "PETROL STATION", "RAILWAY STATION TICKETS",
        "TAXI SERVICES LTD",
    ],
    "Bills": [
        "THAMES WATER", "BRITISH GAS", "OCTOPUS ENERGY", "EDF ENERGY", "EON NEXT",
        "VIRGIN MEDIA", "BT GROUP", "SKY DIGITAL", "VODAFONE", "EE LIMITED", "O2 UK",
        "THREE UK", "GIFFGAFF", "LAMBETH COUNCIL TAX", "TV LICENCE", "LEBARA MOBILE",
        "WANDSWORTH COUNCIL", "SOUTHERN WATER", "BROADBAND PROVIDER", "MOBILE NETWORK LTD",
        "ENERGY SUPPLY CO", "HOME INSURANCE",
    ],
    "Shopping": [
        "AMAZON.CO.UK", "AMZN MKTP UK", "ARGOS", "PRIMARK", "ZARA", "H&M", "UNIQLO",
        "JOHN LEWIS", "IKEA", "CURRYS", "APPLE STORE", "ASOS.COM", "BOOTS", "SUPERDRUG",
        "TK MAXX", "EBAY", "SHEIN", "NEXT RETAIL", "SPORTS DIRECT", "WATERSTONES",
        "THE CLOTHING STORE", "FASHION OUTLET", "HOMEWARE SHOP", "ELECTRONICS WORLD",
        "SHOE SHOP", "GIFT SHOP",
    ],
    "Entertainment": [
        "NETFLIX.COM", "SPOTIFY", "DISNEY PLUS", "AMAZON PRIME", "APPLE.COM/BILL",
        "YOUTUBE PREMIUM", "STEAM GAMES", "PLAYSTATION NETWORK", "XBOX", "ODEON CINEMAS",
        "VUE CINEMA", "CINEWORLD", "TICKETMASTER", "EVENTBRITE", "PUREGYM", "THE GYM GROUP",
        "BOWLING ALLEY", "CITY CINEMA", "LIVE MUSIC VENUE", "THEATRE TICKETS",
        "GAMING STORE ONLINE", "FITNESS CLUB",
    ],
    "Health": [
        "BOOTS PHARMACY", "LLOYDS PHARMACY", "SUPERDRUG PHARMACY", "SPECSAVERS",
        "VISION EXPRESS", "BUPA", "NHS PRESCRIPTION", "DENTAL PRACTICE", "CITY PHARMACY",
        "HIGH STREET CHEMIST", "OPTICIANS LTD", "MEDICAL CENTRE", "PHYSIO CLINIC",
    ],
    "Income": [
        "SALARY", "UNIVERSITY OF ROEHAMPTON", "HMRC REFUND", "STUDENT FINANCE",
        "PAYROLL", "WAGES", "BONUS PAYMENT", "INTEREST PAID", "CASHBACK",
        "TUTORING PAYMENT", "FREELANCE INVOICE",
    ],
    "Rent": [
        "RENT PAYMENT", "FOXTONS LETTINGS", "OPENRENT", "LANDLORD", "PROPERTY MANAGEMENT",
        "UNITE STUDENTS", "IQ STUDENT ACCOMMODATION", "LETTING AGENT",
    ],
    "Transfers": [
        "TRANSFER TO SAVINGS", "MONZO POT", "REVOLUT", "WISE PAYMENTS", "PAYPAL *TRANSFER",
        "STANDING ORDER", "TO SAVINGS ACCOUNT", "FASTER PAYMENT", "ATM WITHDRAWAL",
        "CASH MACHINE", "TRANSFER FROM",
    ],
}

# Independent businesses have no famous brand name, but their names usually
# contain a descriptive word ("ROSA'S KITCHEN", "HIGH STREET PHARMACY").
# These are what the ML model can genuinely generalise to.
DESCRIPTORS = {
    "Groceries": ["SUPERMARKET", "GROCERS", "MINI MARKET", "FOOD STORE", "BUTCHERS", "GREENGROCER",
                  "FARM SHOP", "CONVENIENCE STORE", "FOOD MARKET", "OFF LICENCE"],
    "Eating Out": ["RESTAURANT", "CAFE", "COFFEE", "KITCHEN", "PIZZERIA", "GRILL", "BISTRO",
                   "TAKEAWAY", "PUB", "BAKERY", "SUSHI", "NOODLE BAR", "KEBAB", "DINER", "TAPAS"],
    "Transport": ["TAXI", "CABS", "RAILWAY", "PARKING", "CAR PARK", "PETROL", "FUEL", "COACHES",
                  "BUS TICKETS", "BIKE HIRE", "SERVICE STATION"],
    "Bills": ["ENERGY", "WATER", "BROADBAND", "MOBILE", "TELECOM", "COUNCIL", "INSURANCE",
              "UTILITIES", "GAS AND ELECTRIC"],
    "Shopping": ["CLOTHING", "FASHION", "BOUTIQUE", "HOMEWARE", "ELECTRONICS", "SHOES", "GIFTS",
                 "DEPARTMENT STORE", "BOOKSHOP", "FURNITURE", "HARDWARE"],
    "Entertainment": ["CINEMA", "THEATRE", "GYM", "FITNESS", "BOWLING", "GAMES", "TICKETS",
                      "MUSIC VENUE", "STREAMING", "ARCADE", "CLIMBING CENTRE"],
    "Health": ["PHARMACY", "CHEMIST", "DENTAL", "DENTIST", "OPTICIANS", "CLINIC", "PHYSIO",
               "MEDICAL CENTRE", "HEALTH CENTRE"],
    "Income": ["SALARY", "WAGES", "PAYROLL", "REFUND", "INVOICE PAYMENT", "BURSARY", "INTEREST"],
    "Rent": ["LETTINGS", "RENT", "PROPERTY MANAGEMENT", "ESTATES", "ACCOMMODATION", "HOUSING"],
    "Transfers": ["TRANSFER", "SAVINGS", "STANDING ORDER", "ATM", "CASH WITHDRAWAL", "POT"],
}
NAME_PARTS = [
    "ROSA", "GOLDEN DRAGON", "CITY", "ROYAL", "OLD MILL", "SUNRISE", "KINGS", "BELLA", "RIVERSIDE",
    "HIGH STREET", "PARK LANE", "MARIO", "AL NOOR", "THE CORNER", "GREEN LEAF", "BLUE OCEAN",
    "VICTORIA", "OAKWOOD", "PRIME", "STAR", "UNITED", "NORTHSIDE", "SOUTHBANK", "MAPLE", "ATLAS",
    "CROWN", "PHOENIX", "SILVER", "HAPPY", "LOTUS", "EMPIRE", "ORCHARD", "HARBOUR", "METRO",
    "BRIGHT", "NOVA", "ZARA AND SONS", "ALI", "PATEL", "SMITH", "JONES", "CHEN", "KHAN", "MURPHY",
]


def independent_merchants(per_category=40):
    """Unique made up independent businesses, e.g. 'PHOENIX PHARMACY'."""
    out = {}
    for category, words in DESCRIPTORS.items():
        names = set()
        while len(names) < per_category:
            names.add(f"{random.choice(NAME_PARTS)} {random.choice(words)}")
        out[category] = sorted(names)
    return out


TOWNS = ["LONDON", "CLAPHAM", "PUTNEY", "BRIXTON", "CROYDON", "MANCHESTER", "LEEDS", ""]

TEMPLATES = [
    "{m}",
    "{m} {town}",
    "{m} {num} {town}",
    "CARD PAYMENT TO {m} ON {d}",
    "{m} {town} GB",
    "CONTACTLESS {m} {town}",
    "{m}*{num}",
    "DD {m} {num}",
    "{m} REF {num}",
]


def noisy(merchant):
    template = random.choice(TEMPLATES)
    return " ".join(template.format(
        m=merchant,
        town=random.choice(TOWNS),
        num=random.randint(100, 99999),
        d=f"{random.randint(1, 28):02d}-{random.randint(1, 12):02d}",
    ).split())


def write_training(path, per_merchant=8):
    rows = []
    for kind, source in (("brand", MERCHANTS), ("independent", independent_merchants())):
        for category, merchants in source.items():
            for merchant in merchants:
                for _ in range(per_merchant):
                    rows.append({"description": noisy(merchant), "merchant": merchant,
                                 "kind": kind, "category": category})
    random.shuffle(rows)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["description", "merchant", "kind", "category"])
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


AMOUNT_RANGES = {
    "Groceries": (5, 85), "Eating Out": (3, 45), "Transport": (2, 60), "Bills": (15, 95),
    "Shopping": (8, 120), "Entertainment": (5, 40), "Health": (4, 60),
}


UNSEEN_MERCHANTS = [
    ("MAMA LAN DUMPLINGS BRIXTON", 9, 22), ("SQ *JOES FALAFEL", 6, 12), ("ZETTLE_*THE BREW ROOM", 3, 7),
    ("CLAPHAM NOODLE BAR", 10, 18), ("SUMUP *VINTAGE CLOTHING", 15, 40), ("PAYPAL *GUMROAD", 5, 25),
    ("PECKHAM LEVELS", 8, 30), ("FIX MY PHONE LTD", 20, 60), ("SW4 LAUNDERETTE", 4, 9),
]


def write_sample_statement(path, months=4):
    """A realistic four month student statement in Monzo style columns."""
    start = date(2026, 6, 1)
    rows = []
    for month in range(months):
        first = date(start.year, start.month + month, 1)
        rows.append((first, "STUDENT FINANCE", 2350.00))
        rows.append((first + timedelta(days=2), "UNITE STUDENTS RENT", -780.00))
        rows.append((first + timedelta(days=4), "DD OCTOPUS ENERGY", -42.00))
        rows.append((first + timedelta(days=5), "VODAFONE", -18.00))
        rows.append((first + timedelta(days=6), "SPOTIFY", -5.99))
        rows.append((first + timedelta(days=7), "NETFLIX.COM", -4.99))
        rows.append((first + timedelta(days=14), "TUTORING PAYMENT", 120.00))
        rows.append((first + timedelta(days=20), "TRANSFER TO SAVINGS", -150.00))
        # Realistic merchants the model has never seen, some of them vague,
        # so the "needs review" flow has something to do
        for desc, low, high in UNSEEN_MERCHANTS:
            if random.random() < 0.5:
                day = first + timedelta(days=random.randint(0, 27))
                rows.append((day, desc, -round(random.uniform(low, high), 2)))
        for _ in range(38):
            category = random.choices(
                list(AMOUNT_RANGES), weights=[30, 25, 22, 0, 12, 6, 5])[0]
            merchant = random.choice(MERCHANTS[category])
            low, high = AMOUNT_RANGES[category]
            day = first + timedelta(days=random.randint(0, 27))
            rows.append((day, noisy(merchant), -round(random.uniform(low, high), 2)))
    rows.sort()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Name", "Amount"])
        for d, desc, amt in rows:
            writer.writerow([d.strftime("%d/%m/%Y"), desc, f"{amt:.2f}"])
    return len(rows)


if __name__ == "__main__":
    n = write_training(ROOT / "data" / "training.csv")
    s = write_sample_statement(ROOT.parent / "sample_data" / "sample_statement.csv")
    print(f"training rows: {n}, sample statement rows: {s}")
