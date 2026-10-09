from datetime import datetime, timezone
from pathlib import Path

import pytest

from collector import collect

FIXTURES = Path(__file__).parent / "fixtures"
RSS = (FIXTURES / "sample_rss.xml").read_bytes()
ATOM = (FIXTURES / "sample_atom.xml").read_bytes()
NOW = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
SOURCE = {"name": "샘플", "url": "https://example.com/feed", "region": "kr"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://Example.com/a/?utm_source=x&id=1#frag", "https://example.com/a?id=1"),
        ("https://example.com/", "https://example.com"),
        ("https://example.com/post?b=2&a=1", "https://example.com/post?b=2&a=1"),
    ],
)
def test_normalize_url(raw, expected):
    assert collect.normalize_url(raw) == expected


def test_clean_text_strips_tags_and_entities():
    assert collect.clean_text("<p>본문 &amp; <b>요약</b></p>\n\n끝") == "본문 & 요약 끝"


def test_parse_rss_filters_old_items_and_keeps_undated():
    items = collect.parse_feed(RSS, SOURCE, NOW)
    assert [i["title"] for i in items] == ["최근 기사", "날짜 없는 기사"]
    first = items[0]
    assert first["source"] == "샘플"
    assert first["region"] == "kr"
    assert first["url"] == "https://example.com/a?id=1"
    assert first["published"] == "2026-10-07T21:00:00+09:00"
    assert first["summary"] == "본문 & 요약"
    assert items[1]["published"] is None


def test_parse_atom_uses_updated_time():
    items = collect.parse_feed(ATOM, SOURCE, NOW)
    assert len(items) == 1
    assert items[0]["url"] == "https://atom.example.com/post"
    assert items[0]["published"] == "2026-10-08T05:00:00+09:00"


def test_parse_feed_limits_summary_length():
    long_text = "가" * 600
    feed = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
        f"<item><title>긴 글</title><link>https://example.com/long</link><description>{long_text}</description></item>"
        "</channel></rss>"
    ).encode("utf-8")
    items = collect.parse_feed(feed, SOURCE, NOW)
    assert len(items[0]["summary"]) == 500


def test_parse_feed_rejects_garbage():
    with pytest.raises(ValueError):
        collect.parse_feed(b"this is not a feed", SOURCE, NOW)
