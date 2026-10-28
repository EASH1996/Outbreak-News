import os
import json
import time
import sqlite3
import requests

MODEL = "gemini-flash-lite-latest"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"
API_KEY = os.environ["GEMINI_API_KEY"]
LIMIT = None
REPROCESS = False  # set to True once to re-run the AI on every article, not just new ones
PAUSE = 5
RETRIES = 3
RETRY_WAIT = 30

PROMPT = """You are helping organise disease outbreak news.
Read the article and reply with JSON only, using these keys:
"relevant": true only if it is about a specific disease outbreak, cases of an infectious disease, or a current health threat that is actually happening (including a vaccination campaign run in response to an outbreak). Set it to false for awareness days and weeks (for example World Polio Day, Antibiotics Awareness Week), anniversaries, general vaccination coverage or routine immunisation news, seasonal health advice, mental health, funding, training, meetings and other organisational news.
"disease": the short common name of the disease or health event, or "" if none
"country": the affected country, or "" if unknown
"event_date": the date the outbreak or event started or was first reported, as YYYY-MM-DD, or YYYY-MM if only the month is known, or "" if not stated

Date rules:
- Take dates only from the article. Never use your own knowledge of past outbreaks to fill in a date.
- The article was published on {published}. If the article gives a day and month but no year, use the year of publication, unless that would put the date after {published}, in which case use the year before.
- The event date can never be after {published}.
"category": one of "Outbreak report", "Situation update", "Vaccination campaign", "Preparedness/advisory", "Other"
"status": one of "New", "Ongoing", "Contained", "Over", "Unknown"
"summary": a 2-3 sentence summary, or "" if the article is not relevant

Naming rules, so the same outbreak is always named the same way:
- Use the short common disease name, not the full scientific name. Examples: "MERS", "Ebola", "Cholera", "Mpox", "Lassa fever", "Avian influenza A(H5N1)", "Measles".
- Use the common English country name, not the official long name. Examples: "Saudi Arabia" not "Kingdom of Saudi Arabia", "Democratic Republic of the Congo" not "DRC", "Russia" not "the Russian Federation".
- If the article covers several diseases, use "Multiple diseases". If the cause is not known, use "Unknown".
- If several countries are affected, use the main one. If the article is about a whole region, use the region name, for example "West Africa" or "Global".

Title: {title}
Article: {text}
"""


def ask_model(title, text, published):
    prompt = PROMPT.format(title=title, text=text[:8000], published=published)
    for _ in range(RETRIES):
        response = requests.post(
            API_URL,
            headers={"x-goog-api-key": API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=120,
        )
        if response.status_code not in (429, 503):
            break
        print("  Gemini busy (" + str(response.status_code) + "), waiting", RETRY_WAIT, "seconds...")
        time.sleep(RETRY_WAIT)
    response.raise_for_status()
    answer = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
    # Gemini sometimes wraps the object in a list
    if isinstance(answer, list) and answer:
        answer = answer[0]
    if not isinstance(answer, dict):
        raise ValueError("unexpected reply: " + str(answer)[:100])
    return answer


def check_event_date(event_date, published, text):
    # Drop dates the article cannot support: later than publication, or a year
    # that is neither in the text nor the publication year (or the one before).
    if not event_date or not published:
        return event_date
    if event_date > published:
        return ""
    year = event_date[:4]
    published_year = published[:4]
    if year in text or year in (published_year, str(int(published_year) - 1)):
        return event_date
    return ""


conn = sqlite3.connect("outbreaks.db")

for column in ["relevant INTEGER", "event_date TEXT"]:
    try:
        conn.execute("ALTER TABLE articles ADD COLUMN " + column)
    except sqlite3.OperationalError:
        pass

where = "" if REPROCESS else " WHERE summary IS NULL"
rows = conn.execute("SELECT id, title, text, date FROM articles" + where + " ORDER BY date DESC").fetchall()
if LIMIT:
    rows = rows[:LIMIT]
print("Articles to process:", len(rows))

for i, (article_id, title, text, published) in enumerate(rows):
    try:
        result = ask_model(title, text or "", published or "")
    except (requests.RequestException, ValueError, KeyError) as error:
        print("Failed:", title[:60], error)
        time.sleep(PAUSE)
        continue

    result["event_date"] = check_event_date(result.get("event_date", ""), published, text or "")
    conn.execute(
        "UPDATE articles SET relevant = ?, disease = ?, country = ?, event_date = ?, category = ?, status = ?, summary = ? WHERE id = ?",
        (
            1 if result.get("relevant") else 0,
            result.get("disease", ""),
            result.get("country", ""),
            result.get("event_date", ""),
            result.get("category", ""),
            result.get("status", ""),
            result.get("summary", ""),
            article_id,
        ),
    )
    conn.commit()
    print(i, result.get("disease"), "|", result.get("country"), "|", result.get("event_date"), "|", title[:60])
    time.sleep(PAUSE)

conn.close()
