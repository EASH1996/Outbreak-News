import re
import html
import time
import hashlib
import sqlite3
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup

FEEDS = [
    ("ecdc", "European Centre for Disease Prevention and Control (ECDC)", "https://www.ecdc.europa.eu/en/taxonomy/term/1307/feed"),
    ("cdc", "US Centers for Disease Control and Prevention (CDC)", "https://tools.cdc.gov/api/v2/resources/media/285676.rss"),
    ("paho", "Pan American Health Organization (PAHO)", "https://www.paho.org/en/rss.xml"),
]
PAUSE = 1.5
headers = {"User-Agent": "OutbreakNewsStudentProject"}


def clean_html(raw):
    if not isinstance(raw, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_article(url):
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        return "", url
    soup = BeautifulSoup(response.text, "html.parser")
    groups = {}
    for p in soup.find_all("p"):
        key = id(p.parent)
        if key not in groups:
            groups[key] = [p.parent, 0]
        groups[key][1] += len(p.get_text(strip=True))
    if not groups:
        return "", response.url
    parent = max(groups.values(), key=lambda g: g[1])[0]
    return parent.get_text(" ", strip=True), response.url


conn = sqlite3.connect("outbreaks.db")
known_ids = {row[0] for row in conn.execute("SELECT id FROM articles")}
conn.close()

items = []
for prefix, source, feed_url in FEEDS:
    try:
        response = requests.get(feed_url, headers=headers, timeout=30)
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as error:
        print("Failed to read feed:", source, error)
        continue

    new = 0
    for item in root.findall("./channel/item"):
        link = item.findtext("link", "").strip()
        article_id = prefix + "-" + hashlib.md5(link.encode()).hexdigest()[:12]
        if not link or article_id in known_ids:
            continue

        try:
            text, real_link = get_article(link)
        except requests.RequestException as error:
            print("Failed:", link, error)
            text, real_link = "", link
        if not text:
            text = clean_html(item.findtext("description", ""))

        items.append({
            "id": article_id,
            "date": parsedate_to_datetime(item.findtext("pubDate")).strftime("%Y-%m-%d"),
            "title": clean_html(item.findtext("title", "")),
            "source": source,
            "link": real_link,
            "text": text,
        })
        new += 1
        time.sleep(PAUSE)

    print(source + ": " + str(new) + " new items")

table = pd.DataFrame(items, columns=["id", "date", "title", "source", "link", "text"])
table.to_csv("rss_news.csv", index=False)
print()
print("Saved", len(table), "new items to rss_news.csv")
