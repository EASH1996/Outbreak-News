import time
import pandas as pd
import requests
from bs4 import BeautifulSoup

LIMIT = 250
PAUSE = 1.5
headers = {"User-Agent": "OutbreakNewsStudentProject"}


def get_article_text(url):
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    groups = {}
    for p in soup.find_all("p"):
        key = id(p.parent)
        if key not in groups:
            groups[key] = [p.parent, 0]
        groups[key][1] += len(p.get_text(strip=True))
    if not groups:
        return ""
    parent = max(groups.values(), key=lambda g: g[1])[0]
    return parent.get_text(" ", strip=True)


table = pd.read_csv("ncdc_list.csv").head(LIMIT).copy()

texts = []
for i, row in table.iterrows():
    try:
        text = get_article_text(row["link"])
    except requests.RequestException as error:
        print("Failed:", row["link"], error)
        text = ""
    texts.append(text)
    print(i, row["date"], len(text), "characters |", row["title"][:60])
    time.sleep(PAUSE)

table["text"] = [t if t else s for t, s in zip(texts, table["snippet"])]
table = table.drop(columns=["snippet"])
table.to_csv("ncdc_news.csv", index=False)

empty = sum(1 for t in texts if not t)
print()
print("Saved", len(table), "items to ncdc_news.csv")
print("Pages with no text found:", empty)