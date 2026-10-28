import re
import html
import requests
import pandas as pd

API_URL = "https://www.who.int/api/news/diseaseoutbreaknews"
BASE_LINK = "https://www.who.int/emergencies/disease-outbreak-news/item/"


def clean_html(raw):
    if not isinstance(raw, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


params = {"$orderby": "PublicationDate desc", "$top": 50}
response = requests.get(API_URL, params=params, timeout=30)
items = response.json()["value"]

df = pd.DataFrame(items)

full_text = (
    df["Overview"].apply(clean_html)
    + " "
    + df["Epidemiology"].apply(clean_html)
    + " "
    + df["Assessment"].apply(clean_html)
).str.strip()

table = pd.DataFrame({
    "id": df["Id"],
    "date": df["PublicationDate"].str[:10],
    "title": df["Title"],
    "source": "WHO Disease Outbreak News",
    "link": BASE_LINK + df["UrlName"],
    "text": full_text,
})

table.to_csv("who_news.csv", index=False)
print("Saved", len(table), "items to who_news.csv")
print("Empty texts:", (table["text"] == "").sum())
print("Average text length:", int(table["text"].str.len().mean()), "characters")
print()
print(table.loc[0, "title"])
print(table.loc[0, "text"][:600])