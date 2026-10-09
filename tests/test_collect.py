import io
import json
import sys
import urllib.error
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


def test_collect_continues_after_failed_source():
    def fetcher(url):
        if url == "https://bad.example.com/feed":
            raise urllib.error.HTTPError(url, 403, "Forbidden", None, None)
        return RSS

    sources = [
        {"name": "Bad", "url": "https://bad.example.com/feed", "region": "global"},
        {"name": "Good", "url": "https://good.example.com/feed", "region": "kr"},
    ]
    result = collect.collect(sources, seen=set(), now=NOW, fetcher=fetcher)
    assert result["errors"] == [{"source": "Bad", "error": "HTTP 403"}]
    assert {i["source"] for i in result["items"]} == {"Good"}


def test_collect_records_parse_errors():
    sources = [{"name": "Broken", "url": "https://x.example.com/feed", "region": "kr"}]
    result = collect.collect(sources, seen=set(), now=NOW, fetcher=lambda url: b"garbage")
    assert result["items"] == []
    assert result["errors"][0]["source"] == "Broken"
    assert result["errors"][0]["error"].startswith("ValueError")


def test_collect_skips_seen_and_duplicate_urls():
    sources = [
        {"name": "A", "url": "https://a.example.com/feed", "region": "kr"},
        {"name": "B", "url": "https://b.example.com/feed", "region": "kr"},
    ]
    result = collect.collect(
        sources, seen={"https://example.com/nodate"}, now=NOW, fetcher=lambda url: RSS
    )
    assert [i["url"] for i in result["items"]] == ["https://example.com/a?id=1"]
    assert result["items"][0]["source"] == "A"


def test_load_sources_rejects_bad_region(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        "sources:\n  - name: X\n    url: https://x.example.com/feed\n    region: us\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        collect.load_sources(path)


def test_load_seen_normalizes_and_handles_missing(tmp_path):
    assert collect.load_seen(tmp_path / "none.json") == set()
    path = tmp_path / "seen.json"
    path.write_text('["https://example.com/a/"]', encoding="utf-8")
    assert collect.load_seen(path) == {"https://example.com/a"}


def test_main_writes_raw_json(tmp_path, monkeypatch):
    (tmp_path / "collector").mkdir()
    (tmp_path / "collector" / "sources.yaml").write_text(
        "sources:\n  - name: 샘플\n    url: https://example.com/feed\n    region: kr\n",
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "seen.json").write_text('["https://example.com/seen"]', encoding="utf-8")
    feed = (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
        "<item><title>new</title><link>https://example.com/new</link></item>"
        "<item><title>seen</title><link>https://example.com/seen/</link></item>"
        "</channel></rss>"
    ).encode("utf-8")
    monkeypatch.setattr(collect, "fetch", lambda url: feed)

    assert collect.main(["--date", "2026-10-08", "--root", str(tmp_path)]) == 0

    out = tmp_path / "data" / "raw" / "2026-10-08.json"
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["date"] == "2026-10-08"
    assert [i["url"] for i in result["items"]] == ["https://example.com/new"]
    assert result["errors"] == []


def test_main_survives_non_cp949_console(tmp_path, monkeypatch):
    (tmp_path / "collector").mkdir()
    (tmp_path / "collector" / "sources.yaml").write_text(
        "sources:\n  - name: 샘플\n    url: https://example.com/feed\n    region: kr\n",
        encoding="utf-8",
    )

    def boom(url):
        raise ValueError("깨짐 ☃ \U0001f600")

    monkeypatch.setattr(collect, "fetch", boom)
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp949"))

    assert collect.main(["--date", "2026-10-08", "--root", str(tmp_path)]) == 0

    out = tmp_path / "data" / "raw" / "2026-10-08.json"
    result = json.loads(out.read_text(encoding="utf-8"))
    assert "깨짐 ☃ \U0001f600" in result["errors"][0]["error"]
