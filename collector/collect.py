"""RSS/Atom 피드를 수집해 data/raw/YYYY-MM-DD.json으로 저장한다.

사용법: python collector/collect.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser

KST = timezone(timedelta(hours=9))
MAX_AGE = timedelta(hours=48)
SUMMARY_LIMIT = 500


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
