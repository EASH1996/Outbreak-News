import sqlite3
import pandas as pd

FILES = ["who_news.csv", "ncdc_news.csv", "rss_news.csv"]

conn = sqlite3.connect("outbreaks.db")

conn.execute("""
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    date TEXT,
    title TEXT,
    source TEXT,
    link TEXT,
    text TEXT,
    disease TEXT,
    country TEXT,
    category TEXT,
    status TEXT,
    summary TEXT,
    relevant INTEGER,
    event_date TEXT,
    group_id TEXT
)
""")

before = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

for filename in FILES:
    df = pd.read_csv(filename)
    df["text"] = df["text"].fillna("")
    rows = df[["id", "date", "title", "source", "link", "text"]].values.tolist()
    conn.executemany(
        "INSERT OR IGNORE INTO articles (id, date, title, source, link, text) VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    print("Read", len(df), "rows from", filename)

conn.commit()

after = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
print()
print("Rows before:", before)
print("Rows after:", after)
print("New rows added:", after - before)
print()
print(pd.read_sql("SELECT source, COUNT(*) AS items FROM articles GROUP BY source", conn).to_string())

conn.close()