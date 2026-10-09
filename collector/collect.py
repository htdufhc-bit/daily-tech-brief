"""RSS/Atom 피드를 수집해 data/raw/YYYY-MM-DD.json으로 저장한다.

사용법: python collector/collect.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import yaml

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
MAX_AGE = timedelta(hours=48)
SUMMARY_LIMIT = 500
TIMEOUT_SECONDS = 15
USER_AGENT = "Mozilla/5.0 (compatible; daily-tech-brief/1.0)"
REGIONS = {"kr", "global"}


def normalize_url(url: str) -> str:
    """utm_* 쿼리, 프래그먼트, 끝의 '/'를 없애 같은 기사를 같은 문자열로 만든다."""
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), "")
    )


def clean_text(raw: str) -> str:
    """HTML 태그와 엔티티를 없애고 공백을 한 칸으로 줄인다."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_feed(content: bytes, source: dict, now: datetime) -> list[dict]:
    """피드 내용을 기사 목록으로 바꾼다. 48시간보다 오래된 기사는 뺀다."""
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"피드를 읽을 수 없습니다: {parsed.get('bozo_exception')}")
    items = []
    for entry in parsed.entries:
        link = entry.get("link")
        title = clean_text(entry.get("title", ""))
        if not link or not title:
            continue
        published = _entry_time(entry)
        if published is not None and now - published > MAX_AGE:
            continue
        items.append(
            {
                "source": source["name"],
                "region": source["region"],
                "title": title,
                "url": normalize_url(link),
                "published": published.astimezone(KST).isoformat() if published else None,
                "summary": clean_text(entry.get("summary", ""))[:SUMMARY_LIMIT],
            }
        )
    return items


def _entry_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=timezone.utc)
    return None


def load_sources(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
    for source in sources:
        if not source.get("name") or not source.get("url") or source.get("region") not in REGIONS:
            raise ValueError(f"sources.yaml 항목이 잘못되었습니다: {source}")
    return sources


def load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {normalize_url(url) for url in json.loads(path.read_text(encoding="utf-8"))}


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read()


def collect(sources: list[dict], seen: set[str], now: datetime, fetcher=None) -> dict:
    """모든 소스를 수집한다. 한 소스가 실패해도 나머지는 계속 수집한다."""
    fetcher = fetcher or fetch
    items: list[dict] = []
    errors: list[dict] = []
    collected: set[str] = set()
    for source in sources:
        try:
            entries = parse_feed(fetcher(source["url"]), source, now)
        except Exception as exc:  # 소스 하나의 실패가 전체 수집을 멈추지 않도록
            errors.append({"source": source["name"], "error": _describe(exc)})
            continue
        for item in entries:
            if item["url"] in seen or item["url"] in collected:
                continue
            collected.add(item["url"])
            items.append(item)
    return {"items": items, "errors": errors}


def _describe(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    return f"{type(exc).__name__}: {exc}"


def main(argv: list[str] | None = None) -> int:
    # 한국어 Windows 콘솔(cp949)에서 표현할 수 없는 문자가 있어도 출력 때문에 실패하지 않도록
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="RSS 피드를 수집해 data/raw/에 저장한다")
    parser.add_argument("--date", help="저장할 파일 날짜 (기본: 오늘, 한국 시간)")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    root = Path(args.root)
    now = datetime.now(timezone.utc)
    day = args.date or now.astimezone(KST).date().isoformat()
    sources = load_sources(root / "collector" / "sources.yaml")
    seen = load_seen(root / "data" / "seen.json")
    result = {"date": day, **collect(sources, seen, now)}

    out = root / "data" / "raw" / f"{day}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"{out}: 기사 {len(result['items'])}건, 실패한 소스 {len(result['errors'])}개")
    for error in result["errors"]:
        print(f"  - {error['source']}: {error['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
