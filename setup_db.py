import csv
import sqlite3

DB_PATH = "housing.db"
HOUSING_CSV = "18100205.csv"
INCOME_CSV = "11100190.csv"

# Canonical city names mapped from each CSV's GEO strings
HOUSING_CITY_MAP = {
    "Toronto, Ontario": "Toronto",
    "Vancouver, British Columbia": "Vancouver",
    "Calgary, Alberta": "Calgary",
    "Edmonton, Alberta": "Edmonton",
    "Montréal, Quebec": "Montreal",
    "Ottawa-Gatineau, Ontario part, Ontario/Quebec": "Ottawa",
    "Winnipeg, Manitoba": "Winnipeg",
}

INCOME_CITY_MAP = {
    "Toronto, Ontario": "Toronto",
    "Vancouver, British Columbia": "Vancouver",
    "Calgary, Alberta": "Calgary",
    "Edmonton, Alberta": "Edmonton",
    "Montréal, Quebec": "Montreal",
    "Ottawa-Gatineau, Ontario/Quebec": "Ottawa",
    "Winnipeg, Manitoba": "Winnipeg",
}


def load_housing(conn):
    # Accumulate monthly values per (city, year) then average into annual
    annual = {}  # (city, year) -> [values]

    with open(HOUSING_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            geo = row["GEO"]
            city = HOUSING_CITY_MAP.get(geo)
            if city is None:
                continue
            if row["New housing price indexes"] != "Total (house and land)":
                continue
            ref_date = row["REF_DATE"]  # format: "2000-01"
            year = int(ref_date.split("-")[0])
            if year < 2000:
                continue
            value_str = row["VALUE"].strip()
            if not value_str:
                continue
            try:
                value = float(value_str)
            except ValueError:
                continue
            key = (city, year)
            annual.setdefault(key, []).append(value)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS housing_price_index (
            year    INTEGER NOT NULL,
            city    TEXT    NOT NULL,
            price_index REAL NOT NULL,
            PRIMARY KEY (year, city)
        )
    """)

    rows = []
    for (city, year), values in sorted(annual.items()):
        avg = sum(values) / len(values)
        rows.append((year, city, round(avg, 4)))

    conn.executemany(
        "INSERT OR REPLACE INTO housing_price_index (year, city, price_index) VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def load_income(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS median_income (
            year          INTEGER NOT NULL,
            city          TEXT    NOT NULL,
            median_income REAL    NOT NULL,
            PRIMARY KEY (year, city)
        )
    """)

    rows = []
    with open(INCOME_CSV, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            geo = row["GEO"]
            city = INCOME_CITY_MAP.get(geo)
            if city is None:
                continue
            if row["Income concept"] != "Median after-tax income":
                continue
            if row["Economic family type"] != "Economic families and persons not in an economic family":
                continue
            year = int(row["REF_DATE"])
            if year < 2000:
                continue
            value_str = row["VALUE"].strip()
            if not value_str:
                continue
            try:
                value = float(value_str)
            except ValueError:
                continue
            rows.append((year, city, value))

    rows.sort()
    conn.executemany(
        "INSERT OR REPLACE INTO median_income (year, city, median_income) VALUES (?, ?, ?)",
        rows,
    )
    return len(rows)


def create_affordability_view(conn):
    conn.execute("DROP VIEW IF EXISTS affordability")
    conn.execute("""
        CREATE VIEW affordability AS
        SELECT
            h.year,
            h.city,
            h.price_index,
            m.median_income,
            ROUND(
                h.price_index / (
                    m.median_income * 1.0 /
                    (SELECT mi.median_income
                     FROM median_income mi
                     WHERE mi.city = m.city
                       AND mi.year = (
                           SELECT MIN(year) FROM median_income
                           WHERE city = m.city AND year >= 2000
                       )
                    )
                ),
                4
            ) AS affordability_index,
            ROUND(
                (h.price_index - LAG(h.price_index) OVER (PARTITION BY h.city ORDER BY h.year))
                * 100.0
                / LAG(h.price_index) OVER (PARTITION BY h.city ORDER BY h.year),
                2
            ) AS yoy_price_change
        FROM housing_price_index h
        JOIN median_income m ON h.city = m.city AND h.year = m.year
    """)


def print_summary(conn):
    print("\n=== housing.db verification summary ===\n")

    print("Tables and row counts:")
    for table in ("housing_price_index", "median_income"):
        (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"  {table}: {count} rows")

    print("\nYear range per table:")
    for table, col in (("housing_price_index", "price_index"), ("median_income", "median_income")):
        row = conn.execute(
            f"SELECT MIN(year), MAX(year) FROM {table}"
        ).fetchone()
        print(f"  {table}: {row[0]} – {row[1]}")

    print("\nCities in each table:")
    for table in ("housing_price_index", "median_income"):
        cities = [r[0] for r in conn.execute(f"SELECT DISTINCT city FROM {table} ORDER BY city")]
        print(f"  {table}: {', '.join(cities)}")

    print("\nAffordability view — latest available year per city:")
    rows = conn.execute("""
        SELECT city, MAX(year) AS latest_year, price_index, median_income,
               affordability_index, yoy_price_change
        FROM affordability
        GROUP BY city
        ORDER BY city
    """).fetchall()
    header = f"  {'City':<12} {'Year':>4}  {'PriceIdx':>9}  {'Income':>9}  {'AffordIdx':>10}  {'YoY%':>6}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for city, year, pi, inc, ai, yoy in rows:
        yoy_str = f"{yoy:>6.2f}" if yoy is not None else "   N/A"
        print(f"  {city:<12} {year:>4}  {pi:>9.2f}  {inc:>9,.0f}  {ai:>10.4f}  {yoy_str}")

    print("\nAffordability view total rows:")
    (count,) = conn.execute("SELECT COUNT(*) FROM affordability").fetchone()
    print(f"  {count} rows")

    print("\n=== Done ===\n")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    print(f"Loading {HOUSING_CSV}...")
    h_rows = load_housing(conn)
    print(f"  Inserted {h_rows} annual housing price index rows")

    print(f"Loading {INCOME_CSV}...")
    i_rows = load_income(conn)
    print(f"  Inserted {i_rows} median income rows")

    print("Creating affordability view...")
    create_affordability_view(conn)
    print("  View created")

    conn.commit()
    print_summary(conn)
    conn.close()


if __name__ == "__main__":
    main()
