import sqlite3
from datetime import date

MAX_GAP_DAYS = 60

DISEASE_FIXES = {
    "Poliovirus": "Polio",
    "Unknown illness": "Unknown",
    "Multiple": "Multiple diseases",
    "Multiple infectious diseases": "Multiple diseases",
    "Infectious diseases": "Multiple diseases",
    "Marburg virus disease": "Marburg",
    "Nipah virus": "Nipah",
    "Salmonellosis": "Salmonella",
}
COUNTRY_FIXES = {
    "Multi-country": "Global",
    "United States of America": "United States",
    "The Americas": "Americas",
}

conn = sqlite3.connect("outbreaks.db")

try:
    conn.execute("ALTER TABLE articles ADD COLUMN group_id TEXT")
except sqlite3.OperationalError:
    pass

fixed = 0
for column, fixes in [("disease", DISEASE_FIXES), ("country", COUNTRY_FIXES)]:
    for old, new in fixes.items():
        fixed += conn.execute("UPDATE articles SET " + column + " = ? WHERE " + column + " = ?", (new, old)).rowcount
print("Names cleaned up:", fixed)

rows = conn.execute(
    "SELECT id, date, disease, country FROM articles "
    "WHERE relevant = 1 AND disease != '' AND country != '' "
    "ORDER BY LOWER(disease), LOWER(country), date"
).fetchall()

conn.execute("UPDATE articles SET group_id = id")

group_id = None
previous_key = None
previous_date = None
groups = {}

for article_id, article_date, disease, country in rows:
    key = (disease.strip().lower(), country.strip().lower())
    current_date = date.fromisoformat(article_date)

    same_outbreak = (
        key == previous_key
        and (current_date - previous_date).days <= MAX_GAP_DAYS
    )
    if not same_outbreak:
        group_id = article_id

    conn.execute("UPDATE articles SET group_id = ? WHERE id = ?", (group_id, article_id))
    groups.setdefault(group_id, []).append(article_id)

    previous_key = key
    previous_date = current_date

conn.commit()

multi = {g: ids for g, ids in groups.items() if len(ids) > 1}
print("Articles checked:", len(rows))
print("Outbreaks with more than one report:", len(multi))
print("Reports grouped as related:", sum(len(ids) for ids in multi.values()))

conn.close()
