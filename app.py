import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request

app = Flask(__name__)


@app.template_filter("event_date")
def format_event_date(value):
    # The AI gives YYYY-MM-DD, YYYY-MM or YYYY depending on what the report states.
    if not value:
        return "not stated in report"
    for fmt, out in [("%Y-%m-%d", "%d %B %Y"), ("%Y-%m", "%B %Y (day not stated)"), ("%Y", "%Y (month not stated)")]:
        try:
            return datetime.strptime(value, fmt).strftime(out).lstrip("0")
        except ValueError:
            pass
    return value

DB_PATH = os.path.join(os.path.dirname(__file__), "outbreaks.db")

COLUMNS = "id, date, title, source, link, disease, country, event_date, category, status, summary, group_id"
FILTERS = ["disease", "country", "category", "status"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_related(conn, articles):
    group_ids = list({a["group_id"] for a in articles if a["group_id"]})
    related = {}
    if not group_ids:
        return related
    placeholders = ", ".join("?" * len(group_ids))
    rows = conn.execute(
        "SELECT id, date, title, source, link, group_id FROM articles "
        "WHERE group_id IN (" + placeholders + ") ORDER BY date DESC",
        group_ids,
    ).fetchall()
    for row in rows:
        related.setdefault(row["group_id"], []).append(row)
    return related


def get_latest(limit):
    conn = connect()
    rows = conn.execute(
        "SELECT " + COLUMNS + " FROM articles WHERE relevant IS NOT 0 ORDER BY date DESC"
    ).fetchall()

    articles = []
    seen_groups = set()
    for row in rows:
        group = row["group_id"] or row["id"]
        if group in seen_groups:
            continue
        seen_groups.add(group)
        articles.append(row)
        if len(articles) == limit:
            break

    related = get_related(conn, articles)
    conn.close()
    return articles, related


def get_filter_options(conn):
    options = {}
    for column in FILTERS:
        rows = conn.execute(
            "SELECT DISTINCT " + column + " FROM articles "
            "WHERE relevant = 1 AND " + column + " != '' ORDER BY " + column
        ).fetchall()
        options[column] = [r[0] for r in rows]
    return options


def search_articles(query, selected):
    conn = connect()
    conditions = ["relevant IS NOT 0"]
    params = []

    if query:
        like = "%" + query + "%"
        conditions.append("(title LIKE ? OR text LIKE ? OR country LIKE ? OR disease LIKE ? OR summary LIKE ?)")
        params += [like, like, like, like, like]

    for column in FILTERS:
        if selected[column]:
            conditions.append(column + " = ?")
            params.append(selected[column])

    articles = conn.execute(
        "SELECT " + COLUMNS + " FROM articles WHERE " + " AND ".join(conditions) + " ORDER BY date DESC",
        params,
    ).fetchall()
    related = get_related(conn, articles)
    options = get_filter_options(conn)
    conn.close()
    return articles, related, options


@app.route("/")
def latest():
    articles, related = get_latest(20)
    return render_template("latest.html", articles=articles, related=related)


@app.route("/archive")
def archive():
    query = request.args.get("q", "").strip()
    selected = {column: request.args.get(column, "") for column in FILTERS}
    articles, related, options = search_articles(query, selected)
    return render_template(
        "archive.html",
        articles=articles,
        related=related,
        options=options,
        query=query,
        selected=selected,
    )


if __name__ == "__main__":
    app.run(debug=True)
