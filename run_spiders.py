"""Run every spider one after another and report how each one did.

Meant to be started once a day by Task Scheduler (Windows) or cron (Raspberry Pi):

    venv\\Scripts\\python run_spiders.py              # all spiders
    venv\\Scripts\\python run_spiders.py a101Spider   # only some

Each spider runs as its own "scrapy crawl" process, so one crashing does not stop
the others. Logs go to logs/<date>/<spider>.log and a summary to logs/<date>/summary.txt.
The exit code is 1 when any spider failed, so the scheduler can flag the run.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
LOG_ROOT = ROOT / "logs"
KEEP_LOGS_DAYS = 30
# warn when a market saves less than this share of its previous run's prices
MIN_SHARE_OF_PREVIOUS = 0.8

# lines like  'item_scraped_count': 8433,  in the stats Scrapy prints at the end
STAT_LINE = re.compile(r"'([^']+)': ('?)(.*?)\2,?$")

# compare today's saved prices per market with the market's previous scrape day
DAILY_COUNTS = """
    WITH daily AS (
        SELECT p.market_id, (pr.scraped_at AT TIME ZONE 'Europe/Istanbul')::date AS day,
               count(*) AS prices
        FROM prices pr
        JOIN products p ON p.id = pr.product_id
        WHERE pr.scraped_at > now() - interval '14 days'
        GROUP BY 1, 2
    )
    SELECT m.name, today.prices, previous.prices
    FROM markets m
    LEFT JOIN daily today
        ON today.market_id = m.id AND today.day = (now() AT TIME ZONE 'Europe/Istanbul')::date
    LEFT JOIN LATERAL (
        SELECT d.prices FROM daily d
        WHERE d.market_id = m.id AND d.day < (now() AT TIME ZONE 'Europe/Istanbul')::date
        ORDER BY d.day DESC LIMIT 1
    ) previous ON true
    ORDER BY m.name
"""


def scrapy(*args, **kwargs):
    # sys.executable is the venv's python, so the venv's Scrapy is used
    return subprocess.run([sys.executable, "-m", "scrapy", *args], cwd=ROOT, **kwargs)


def read_stats(log_file):
    """The stats dictionary Scrapy writes to the end of the log."""
    stats, inside = {}, False
    if not log_file.exists():
        return stats
    for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if "Dumping Scrapy stats" in line:
            stats, inside = {}, True
        elif inside:
            match = STAT_LINE.search(line.strip(" {}"))
            if match:
                stats[match.group(1)] = match.group(3)
            if line.rstrip().endswith("}"):
                inside = False
    return stats


def run_spider(spider, log_dir):
    log_file = log_dir / f"{spider}.log"
    started = time.monotonic()
    process = scrapy("crawl", spider, "-s", f"LOG_FILE={log_file}", "-s", "LOG_LEVEL=INFO")
    minutes = (time.monotonic() - started) / 60

    stats = read_stats(log_file)
    scraped = int(stats.get("item_scraped_count", 0))
    dropped = int(stats.get("item_dropped_count", 0))
    errors = int(stats.get("log_count/ERROR", 0))

    problems = []
    if process.returncode != 0:
        problems.append(f"exit code {process.returncode}")
    if stats.get("finish_reason", "missing") != "finished":
        problems.append(f"finish reason {stats.get('finish_reason', 'missing')}")
    if scraped == 0:
        problems.append("no items")
    if errors:
        problems.append(f"{errors} errors in log")

    line = f"{spider:16} {scraped:7} items {dropped:5} dropped {minutes:6.1f} min"
    return line + ("   FAILED: " + ", ".join(problems) if problems else "   ok"), not problems


def connect():
    load_dotenv(ROOT / ".env")
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        autocommit=True,
    )


def refresh_product_groups():
    """Regroups the products for the webapp, which lists the same product of different
    markets together (product_groups in db/init.sql). CONCURRENTLY keeps the webapp
    answering from the old groups while the new ones are computed."""
    started = time.monotonic()
    try:
        with connect() as conn:
            conn.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY product_groups")
    except psycopg.Error as e:
        return f"product groups refresh failed: {e}", False
    return f"product groups refreshed in {time.monotonic() - started:.0f} s", True


def database_check():
    """Saved prices per market today vs. the previous run, catching silent partial runs."""
    lines, ok = [], True
    try:
        with connect() as conn:
            for market, today, previous in conn.execute(DAILY_COUNTS):
                today, line = today or 0, f"{market:16} {today or 0:7} prices today"
                if previous:
                    line += f", {previous} on the previous run"
                    if today < previous * MIN_SHARE_OF_PREVIOUS:
                        line += f"   WARNING: under {MIN_SHARE_OF_PREVIOUS:.0%} of the previous run"
                        ok = False
                lines.append(line)
    except psycopg.Error as e:
        return [f"database check failed: {e}"], False
    return lines, ok


def remove_old_logs():
    cutoff = date.today() - timedelta(days=KEEP_LOGS_DAYS)
    for folder in LOG_ROOT.glob("????-??-??"):
        try:
            if date.fromisoformat(folder.name) < cutoff:
                shutil.rmtree(folder)
        except ValueError:
            continue


def main():
    spiders = sys.argv[1:] or scrapy("list", capture_output=True, text=True, check=True).stdout.split()
    log_dir = LOG_ROOT / date.today().isoformat()
    log_dir.mkdir(parents=True, exist_ok=True)

    summary = [f"Run started {datetime.now():%Y-%m-%d %H:%M}", ""]
    all_ok = True
    for spider in spiders:
        print(f"Running {spider}...", flush=True)
        line, ok = run_spider(spider, log_dir)
        print(line, flush=True)
        summary.append(line)
        all_ok &= ok

    groups_line, groups_ok = refresh_product_groups()
    db_lines, db_ok = database_check()
    summary += ["", *db_lines, groups_line, "", f"Run finished {datetime.now():%Y-%m-%d %H:%M}"]
    all_ok &= db_ok and groups_ok

    text = "\n".join(summary) + "\n"
    print("\n" + text)
    with open(log_dir / "summary.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")

    remove_old_logs()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
