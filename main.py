from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Sequence

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_RECORDS = 250
MIN_KEYWORD_LEN = 3
EXAMPLE_COMMANDS = [
    'MSFT -k "guidance, investigation" -d 5 -l 40',
    '"NVIDIA" -k "ai, chips, guidance"',
    'AAPL -k "earnings, outlook" -d 2',
    '"Tesla" --allow-non-english -l 15',
    '"Bank of America" -k "downgrade, investigation" -d 10 -l 40',
    '"Meta" -k "privacy, regulation" -d 7',
]


def ensure_requests():
    try:
        import requests  # type: ignore
        return requests
    except ModuleNotFoundError:
        print("Installing requests...", flush=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
        import requests  # type: ignore
        return requests


def _normalize_term(term: str) -> str:
    term = term.strip()
    if not term:
        return ""
    if " " in term:
        return f'"{term}"'
    return term


def normalize_keywords(raw_keywords: Sequence[str] | None) -> tuple[list[str], list[str]]:
    """
    Split comma-separated keywords, trim, drop empties, and collect too-short ones.
    Returns (usable_keywords, skipped_keywords).
    """
    if not raw_keywords:
        return [], []

    usable: list[str] = []
    skipped: list[str] = []

    for item in raw_keywords:
        parts = item.split(",")
        for part in parts:
            kw = part.strip()
            if not kw:
                continue
            if len(kw) < MIN_KEYWORD_LEN:
                skipped.append(kw)
                continue
            usable.append(kw)

    return usable, skipped


def build_query(symbol: str, keywords: Sequence[str] | None, english_only: bool = True) -> str:
    symbol = symbol.strip()
    if not symbol:
        raise ValueError("A stock symbol or company name is required.")

    parts: list[str] = [f'("{symbol}" OR {symbol})']

    if keywords:
        normalized = [_normalize_term(k) for k in keywords]
        normalized = [k for k in normalized if k]
        if normalized:
            if len(normalized) == 1:
                parts.append(normalized[0])
            else:
                parts.append("(" + " OR ".join(normalized) + ")")

    if english_only:
        parts.append("sourcelang:english")

    return " AND ".join(parts)


def fetch_articles(
    symbol: str,
    keywords: Sequence[str] | None,
    days: int = 3,
    limit: int = 25,
    english_only: bool = True,
):
    limit = max(1, min(limit, MAX_RECORDS))
    days = max(0, days)

    query = build_query(symbol, keywords, english_only)
    requests = ensure_requests()

    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": limit,
        "sort": "datedesc",
    }

    if days > 0:
        start = datetime.now(timezone.utc) - timedelta(days=days)
        params["startdatetime"] = start.strftime("%Y%m%d%H%M%S")

    response = requests.get(GDELT_URL, params=params, timeout=10)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        snippet = response.text[:500]
        raise RuntimeError(
            f"Unexpected response (status {response.status_code}): {snippet}"
        ) from exc

    articles = data.get("articles", [])
    results = []
    for article in articles:
        results.append(
            {
                "title": article.get("title"),
                "url": article.get("url"),
                "seendate": article.get("seendate"),
                "source": article.get("sourceCommonName") or article.get("sourcecountry"),
                "language": article.get("language"),
                "domain": article.get("domain"),
            }
        )
    return results


def print_articles(articles: list[dict[str, str | None]]) -> None:
    if not articles:
        print("No articles found.")
        return

    for idx, article in enumerate(articles, 1):
        title = article.get("title") or "No title"
        source = article.get("source") or "unknown source"
        date = article.get("seendate") or "unknown date"
        lang = article.get("language") or "?"
        url = article.get("url") or "unknown URL"

        print(f"[{idx}] {title}")
        print(f"    Source: {source} | Date: {date} | Lang: {lang}")
        print(f"    URL: {url}\n")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search stock-related news via GDELT (English-only by default)."
    )
    parser.add_argument("symbol", help="Stock symbol or company name (e.g., MSFT or Microsoft)")
    parser.add_argument(
        "-k",
        "--keyword",
        action="append",
        dest="keywords",
        default=None,
        help="Keyword(s) to include; repeatable or comma-separated string.",
    )
    parser.add_argument(
        "-d",
        "--days",
        type=int,
        default=3,
        help="How many days back to search (0 = all available).",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=25,
        help=f"Max articles to return (1-{MAX_RECORDS}).",
    )
    parser.add_argument(
        "--allow-non-english",
        action="store_true",
        help="Disable the English-only filter (default keeps only English).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(argv or sys.argv[1:])
    if not args_list:
        print("Try one of these commands:")
        for example in EXAMPLE_COMMANDS:
            print(f"  python main.py {example}")
        print("\nUse -h/--help for full options.")
        return 1

    args = parse_args(args_list)

    try:
        keywords, skipped = normalize_keywords(args.keywords)
        if skipped:
            print(
                f"Skipping short keywords (<{MIN_KEYWORD_LEN} chars): {', '.join(skipped)}",
                flush=True,
            )

        articles = fetch_articles(
            symbol=args.symbol,
            keywords=keywords,
            days=args.days,
            limit=args.limit,
            english_only=not args.allow_non_english,
        )
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"Error: {exc}")
        return 1

    print_articles(articles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
