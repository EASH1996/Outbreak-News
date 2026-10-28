import os
import sys
import subprocess
from datetime import datetime

STEPS = [
    ("Collect WHO Disease Outbreak News", "collector.py"),
    ("Collect NCDC press release list", "scraper_ncdc.py"),
    ("Download NCDC article text", "ncdc_fulltext.py"),
    ("Collect ECDC, CDC and PAHO RSS feeds", "collector_rss.py"),
    ("Save new articles to the database", "database.py"),
    ("AI: filter, categorise and summarise", "ai_enrich.py"),
    ("Group related reports", "dedupe.py"),
]

folder = os.path.dirname(os.path.abspath(__file__))
print("Pipeline started:", datetime.now().strftime("%Y-%m-%d %H:%M"))

for name, script in STEPS:
    print()
    print("=== " + name + " (" + script + ") ===")
    result = subprocess.run([sys.executable, script], cwd=folder)
    if result.returncode != 0:
        print("Step failed:", script, "- stopping the pipeline.")
        sys.exit(1)

print()
print("Pipeline finished:", datetime.now().strftime("%Y-%m-%d %H:%M"))
