import re
from datetime import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://www.ncdc.gov.ng/news/press"
BASE = "https://www.ncdc.gov.ng"
headers = {"User-Agent": "OutbreakNewsStudentProject"}

response = requests.get(URL, headers=headers, timeout=30)
print("Status code:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

date_pattern = re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{2} [A-Z][a-z]{2} \d{4})\b")

items = {}
skipped = 0

for a in soup.find_all("a", href=True):
    match_id = re.search(r"/news/(\d+)/", a["href"])
    if not match_id:
        continue

    news_id = match_id.group(1)
    if news_id in items:
        continue

    row = a.find_parent("tr")
    if row is None:
        skipped += 1
        continue

    row_text = row.get_text(" ", strip=True)
    match_date = date_pattern.search(row_text)
    if match_date is None:
        skipped += 1
        continue

    title = row_text[:match_date.start()].strip()
    snippet = row_text[match_date.end():].strip()
    date = datetime.strptime(match_date.group(1), "%d %b %Y").strftime("%Y-%m-%d")

    href = a["href"]
    link = href if href.startswith("http") else BASE + href

    items[news_id] = {
        "id": "ncdc-" + news_id,
        "date": date,
        "title": title,
        "source": "Nigeria Centre for Disease Control (NCDC)",
        "link": link,
        "snippet": snippet,
    }

table = pd.DataFrame(list(items.values()))
table = table.sort_values("date", ascending=False)
table.to_csv("ncdc_list.csv", index=False)

print("Items collected:", len(table))
print("Skipped rows:", skipped)
print("Date range:", table["date"].min(), "to", table["date"].max())
print()
print(table[["date", "title"]].head(8).to_string())