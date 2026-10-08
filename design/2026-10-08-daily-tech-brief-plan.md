# Daily Tech Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매일 아침 국내·해외 IT 뉴스 요약과 "오늘의 기술" 글 1편을 GitHub Pages 웹 페이지로 자동 발행한다.

**Architecture:** Python 수집기(`collector/collect.py`)가 RSS를 JSON으로 모으고, Claude Code 클라우드 루틴이 `ROUTINE.md` 지침에 따라 기사 선별·요약·기술 글을 브리핑 JSON으로 쓴다. `build.py`가 그 JSON을 검사(`validate.py`)하고 Jinja2 템플릿(`render.py`)으로 `docs/`에 HTML을 만든 뒤, 루틴이 `main`에 푸시하면 GitHub Pages가 공개한다.

**Tech Stack:** Python 3 (로컬 3.14, 클라우드는 Ubuntu 기본), feedparser, PyYAML, Jinja2, Markdown, pytest, GitHub Pages, Claude Code routines

**Spec:** `design/2026-10-08-daily-tech-brief-design.md`

## Global Constraints

- 코드는 Python 3.12 이상에서 동작해야 한다 (클라우드 Python 버전이 문서화되어 있지 않음). 모든 모듈 docstring 아래에 `from __future__ import annotations`.
- 외부 패키지는 `feedparser`, `PyYAML`, `Jinja2`, `Markdown`, `pytest`만 쓴다.
- 파일 읽기/쓰기는 항상 `encoding="utf-8"`, 쓰기는 `newline="\n"` (Windows와 Linux 결과를 같게).
- 날짜는 한국 시간(KST, UTC+9) 기준 `YYYY-MM-DD`.
- 사용자에게 보이는 메시지, 주석, 문서는 한국어.
- `docs/` 안의 파일은 `build.py`만 만든다 (예외: Task 7에서 처음 만드는 빈 `docs/.nojekyll`).
- 저장소: `htdufhc-bit/daily-tech-brief` (공개), Pages 주소: `https://htdufhc-bit.github.io/daily-tech-brief/`
- 루틴 실행 시각: 매일 07:07 KST
- 로컬 명령은 Git Bash 기준, 저장소 루트(`/c/Jun_/daily-tech-brief`)에서 가상환경 Python `.venv/Scripts/python` 사용.
- 모든 커밋 메시지는 두 번째 `-m`으로 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`을 붙인다 (루틴의 `brief:` 커밋은 제외).

## File Structure

| 파일 | 책임 |
|---|---|
| `requirements.txt`, `pytest.ini`, `.gitignore`, `.gitattributes` | 의존성, 테스트 설정, Git 설정 |
| `collector/__init__.py` | 패키지 표시 (빈 파일) |
| `collector/collect.py` | URL 정규화, 피드 파싱, 소스별 수집, `data/raw/` 저장 CLI |
| `collector/sources.yaml` | RSS 소스 목록 |
| `validate.py` | 브리핑 JSON 형식 검사 → 오류 문자열 목록 |
| `render.py` | 안전한 마크다운 변환, 날짜 표기, Jinja2로 페이지 문자열 생성 |
| `templates/_layout.html`, `templates/brief.html`, `templates/archive.html`, `templates/style.css` | 페이지 틀과 스타일 |
| `build.py` | 검사 → `docs/` 쓰기 → `seen.json`·`curriculum.yaml` 갱신 CLI |
| `curriculum.yaml` | 오늘의 기술 주제 목록 |
| `data/seen.json` | 이미 소개한 기사 URL |
| `ROUTINE.md` | 클라우드 Claude의 매일 작업 지침 |
| `README.md` | 프로젝트 소개, 로컬 실행법 |
| `tests/__init__.py`, `tests/factories.py` | 테스트 공용 브리핑 예시 |
| `tests/fixtures/sample_rss.xml`, `tests/fixtures/sample_atom.xml` | 피드 샘플 |
| `tests/test_collect.py`, `tests/test_validate.py`, `tests/test_render.py`, `tests/test_build.py` | 단위 테스트 |

---

### Task 1: 프로젝트 뼈대 + URL 정규화·피드 파싱

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `.gitattributes`, `collector/__init__.py`, `collector/collect.py`
- Create: `tests/fixtures/sample_rss.xml`, `tests/fixtures/sample_atom.xml`
- Test: `tests/test_collect.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `collector.collect.KST: timezone` (UTC+9)
  - `collector.collect.normalize_url(url: str) -> str`
  - `collector.collect.clean_text(raw: str) -> str`
  - `collector.collect.parse_feed(content: bytes, source: dict, now: datetime) -> list[dict]` — 각 dict 키: `source`, `region`, `title`, `url`, `published`(ISO8601 KST 문자열 또는 `None`), `summary`(최대 500자). 피드를 전혀 읽을 수 없으면 `ValueError`.

- [ ] **Step 1: 뼈대 파일 만들기**

`requirements.txt`:
```text
feedparser>=6.0
PyYAML>=6.0
Jinja2>=3.1
Markdown>=3.5
pytest>=8.0
```

`pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`.gitignore`:
```text
__pycache__/
.pytest_cache/
.venv/
```

`.gitattributes`:
```text
* text=auto eol=lf
```

`collector/__init__.py`: 빈 파일.

- [ ] **Step 2: 가상환경 만들고 패키지 설치**

Run:
```bash
python -m venv .venv && .venv/Scripts/python -m pip install -q -r requirements.txt && .venv/Scripts/python -c "import feedparser, yaml, jinja2, markdown; print('ok')"
```
Expected: `ok`

- [ ] **Step 3: 피드 샘플 만들기**

`tests/fixtures/sample_rss.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Sample</title>
<link>https://example.com</link>
<description>sample feed</description>
<item>
<title>최근 기사</title>
<link>https://example.com/a/?utm_source=rss&amp;id=1</link>
<description><![CDATA[<p>본문 &amp; 요약</p>]]></description>
<pubDate>Wed, 07 Oct 2026 12:00:00 GMT</pubDate>
</item>
<item>
<title>오래된 기사</title>
<link>https://example.com/old</link>
<description>old</description>
<pubDate>Thu, 01 Oct 2026 12:00:00 GMT</pubDate>
</item>
<item>
<title>날짜 없는 기사</title>
<link>https://example.com/nodate</link>
<description>nodate</description>
</item>
</channel>
</rss>
```

`tests/fixtures/sample_atom.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>Atom Sample</title>
<id>urn:sample</id>
<updated>2026-10-07T20:00:00Z</updated>
<entry>
<title>Atom 기사</title>
<link href="https://atom.example.com/post/"/>
<id>urn:sample:1</id>
<updated>2026-10-07T20:00:00Z</updated>
<summary>atom summary</summary>
</entry>
</feed>
```

- [ ] **Step 4: 실패하는 테스트 작성**

`tests/test_collect.py`:
```python
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
```

- [ ] **Step 5: 테스트가 실패하는지 확인**

Run: `.venv/Scripts/python -m pytest tests/test_collect.py -v`
Expected: FAIL — `ImportError: cannot import name 'collect' from 'collector'` (모듈 없음)

- [ ] **Step 6: 최소 구현 작성**

`collector/collect.py`:
```python
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
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `.venv/Scripts/python -m pytest tests/test_collect.py -v`
Expected: 8 passed

- [ ] **Step 8: 커밋**

```bash
git add requirements.txt pytest.ini .gitignore .gitattributes collector tests
git commit -m "feat: parse RSS/Atom feeds and normalize URLs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 소스별 수집과 수집 CLI

**Files:**
- Modify: `collector/collect.py` (import·상수 교체, 함수와 `main` 추가)
- Test: `tests/test_collect.py` (테스트 추가)

**Interfaces:**
- Consumes: Task 1의 `normalize_url`, `parse_feed`, `KST`
- Produces:
  - `collector.collect.ROOT: Path` (저장소 루트)
  - `collector.collect.load_sources(path: Path) -> list[dict]` — 각 항목 `name`, `url`, `region`(`kr`|`global`), 잘못되면 `ValueError`
  - `collector.collect.load_seen(path: Path) -> set[str]` — 정규화된 URL 집합, 파일 없으면 빈 집합
  - `collector.collect.fetch(url: str) -> bytes` — 15초 타임아웃
  - `collector.collect.collect(sources: list[dict], seen: set[str], now: datetime, fetcher=None) -> dict` — `{"items": [...], "errors": [{"source", "error"}]}`, `fetcher`가 `None`이면 호출 시점의 모듈 함수 `fetch` 사용
  - `collector.collect.main(argv: list[str] | None = None) -> int` — `--date`, 숨김 옵션 `--root`, 항상 0 반환

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/test_collect.py` 맨 위 import에 `import json`, `import urllib.error`를 추가하고, 파일 끝에 다음을 붙인다:
```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `.venv/Scripts/python -m pytest tests/test_collect.py -v`
Expected: 새 테스트 6개 FAIL — `AttributeError: module 'collector.collect' has no attribute 'collect'` 등

- [ ] **Step 3: 구현 추가**

`collector/collect.py`의 `from __future__ import annotations` 아래 import 부분을 다음으로 바꾼다:
```python
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
```

상수 부분을 다음으로 바꾼다:
```python
KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
MAX_AGE = timedelta(hours=48)
SUMMARY_LIMIT = 500
TIMEOUT_SECONDS = 15
USER_AGENT = "Mozilla/5.0 (compatible; daily-tech-brief/1.0)"
REGIONS = {"kr", "global"}
```

파일 끝에 다음을 추가한다:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/Scripts/python -m pytest tests/test_collect.py -v`
Expected: 14 passed

- [ ] **Step 5: 커밋**

```bash
git add collector/collect.py tests/test_collect.py
git commit -m "feat: collect feeds from all sources into daily raw JSON" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 브리핑 JSON 검사

**Files:**
- Create: `validate.py`, `tests/__init__.py`(빈 파일), `tests/factories.py`
- Test: `tests/test_validate.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `validate.validate_brief(brief: dict, expected_date: str, topic_ids: set[str]) -> list[str]` — 문제가 없으면 빈 리스트. 각 오류는 `"<필드 경로>: <설명>"` 형식 (예: `"news[0].summary: 비어 있지 않은 문장 3개여야 합니다"`)
  - `tests.factories.BRIEF: dict`, `tests.factories.make_brief(day: str = "2026-10-08") -> dict` — 검사를 통과하는 브리핑의 깊은 복사본 (국내 1건, 해외 1건, `pick: "curriculum"`, `topic_id: "http-caching"`, `category: "웹"`)

- [ ] **Step 1: 테스트용 예시 브리핑 만들기**

`tests/__init__.py`: 빈 파일.

`tests/factories.py`:
```python
"""테스트와 ROUTINE.md가 참고하는 정상 브리핑 예시."""
import copy

BRIEF = {
    "date": "2026-10-08",
    "headline": "오늘의 핵심 이슈",
    "news": [
        {
            "region": "kr",
            "source": "GeekNews",
            "title": "국내 기사",
            "original_title": None,
            "url": "https://news.hada.io/topic?id=1",
            "summary": ["첫째 요약", "둘째 요약", "셋째 요약"],
        },
        {
            "region": "global",
            "source": "Hacker News",
            "title": "해외 기사",
            "original_title": "Global Story",
            "url": "https://example.com/story?utm_source=hn",
            "summary": ["one", "two", "three"],
        },
    ],
    "tech": {
        "topic_id": "http-caching",
        "title": "HTTP 캐싱",
        "category": "웹",
        "pick": "curriculum",
        "reading_minutes": 7,
        "sections": {
            "definition": "응답을 저장해 두고 다시 쓰는 기법",
            "why": "서버 부하와 **지연 시간**을 줄인다.",
            "how": "1. 서버가 `Cache-Control` 헤더를 보낸다\n2. 브라우저가 응답을 저장한다",
            "example": "```http\nCache-Control: max-age=3600\n```",
            "when": "자주 바뀌지 않는 자원에 쓴다.",
            "further_reading": [
                {"title": "MDN HTTP 캐싱", "url": "https://developer.mozilla.org/ko/docs/Web/HTTP/Caching"}
            ],
        },
    },
    "notes": [],
}


def make_brief(day: str = "2026-10-08") -> dict:
    brief = copy.deepcopy(BRIEF)
    brief["date"] = day
    return brief
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_validate.py`:
```python
import pytest

from tests.factories import make_brief
from validate import validate_brief

TOPICS = {"http-caching", "dns"}


def check(brief):
    return validate_brief(brief, "2026-10-08", TOPICS)


def test_valid_brief_has_no_errors():
    assert check(make_brief()) == []


def test_empty_news_is_allowed():
    brief = make_brief()
    brief["news"] = []
    assert check(brief) == []


def test_trend_pick_may_use_new_topic():
    brief = make_brief()
    brief["tech"].update(pick="trend", topic_id="brand-new-thing")
    assert check(brief) == []


CASES = [
    ("wrong_date", lambda b: b.update(date="2026-10-07"), "date:"),
    ("empty_headline", lambda b: b.update(headline=" "), "headline:"),
    ("news_not_list", lambda b: b.update(news={}), "news:"),
    ("two_line_summary", lambda b: b["news"][0].update(summary=["a", "b"]), "news[0].summary:"),
    ("blank_summary_line", lambda b: b["news"][0].update(summary=["a", "", "c"]), "news[0].summary:"),
    ("bad_region", lambda b: b["news"][0].update(region="us"), "news[0].region:"),
    ("missing_source", lambda b: b["news"][0].pop("source"), "news[0].source:"),
    ("ftp_url", lambda b: b["news"][0].update(url="ftp://x.com/a"), "news[0].url:"),
    ("global_without_original", lambda b: b["news"][1].update(original_title=None), "news[1].original_title:"),
    ("too_many_news", lambda b: b.update(news=b["news"] * 7), "news: 최대"),
    ("missing_tech", lambda b: b.pop("tech"), "tech:"),
    ("missing_category", lambda b: b["tech"].pop("category"), "tech.category:"),
    ("unknown_curriculum_topic", lambda b: b["tech"].update(topic_id="nope"), "tech.topic_id:"),
    ("bad_pick", lambda b: b["tech"].update(pick="random"), "tech.pick:"),
    ("zero_minutes", lambda b: b["tech"].update(reading_minutes=0), "tech.reading_minutes:"),
    ("bool_minutes", lambda b: b["tech"].update(reading_minutes=True), "tech.reading_minutes:"),
    ("missing_section", lambda b: b["tech"]["sections"].pop("how"), "tech.sections.how:"),
    ("no_further_reading", lambda b: b["tech"]["sections"].update(further_reading=[]), "tech.sections.further_reading:"),
    (
        "four_further_reading",
        lambda b: b["tech"]["sections"].update(further_reading=b["tech"]["sections"]["further_reading"] * 4),
        "tech.sections.further_reading:",
    ),
    (
        "javascript_further_link",
        lambda b: b["tech"]["sections"].update(further_reading=[{"title": "x", "url": "javascript:alert(1)"}]),
        "tech.sections.further_reading[0]:",
    ),
    ("notes_not_strings", lambda b: b.update(notes=[1]), "notes:"),
]


@pytest.mark.parametrize(("name", "mutate", "prefix"), CASES, ids=[c[0] for c in CASES])
def test_invalid_brief_reports_path(name, mutate, prefix):
    brief = make_brief()
    mutate(brief)
    errors = check(brief)
    assert any(error.startswith(prefix) for error in errors), errors


def test_reports_all_errors_at_once():
    brief = make_brief()
    brief["headline"] = ""
    brief["news"][0]["url"] = "nope"
    brief["tech"]["reading_minutes"] = 99
    assert len(check(brief)) == 3
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `.venv/Scripts/python -m pytest tests/test_validate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'validate'`

- [ ] **Step 4: 구현 작성**

`validate.py`:
```python
"""브리핑 JSON 형식 검사. 설계 문서 4.4절의 규칙을 따른다."""
from __future__ import annotations

import re

REGIONS = {"kr", "global"}
PICKS = {"trend", "curriculum"}
TEXT_SECTIONS = ("definition", "why", "how", "example", "when")
MAX_NEWS = 12
URL_PATTERN = re.compile(r"^https?://\S+$")


def validate_brief(brief: dict, expected_date: str, topic_ids: set[str]) -> list[str]:
    """문제를 모두 찾아 '<필드 경로>: <설명>' 목록으로 돌려준다. 문제가 없으면 빈 목록."""
    if not isinstance(brief, dict):
        return ["$: JSON 객체여야 합니다"]
    errors: list[str] = []
    if brief.get("date") != expected_date:
        errors.append(f"date: '{expected_date}'여야 합니다 (현재: {brief.get('date')!r})")
    if not _text(brief.get("headline")):
        errors.append("headline: 비어 있지 않은 문자열이어야 합니다")

    news = brief.get("news")
    if not isinstance(news, list):
        errors.append("news: 배열이어야 합니다")
    else:
        if len(news) > MAX_NEWS:
            errors.append(f"news: 최대 {MAX_NEWS}건입니다 (현재: {len(news)}건)")
        for index, item in enumerate(news):
            errors.extend(_check_news(item, f"news[{index}]"))

    tech = brief.get("tech")
    if not isinstance(tech, dict):
        errors.append("tech: 필수 객체입니다")
    else:
        errors.extend(_check_tech(tech, topic_ids))

    notes = brief.get("notes", [])
    if not isinstance(notes, list) or not all(_text(note) for note in notes):
        errors.append("notes: 비어 있지 않은 문자열의 배열이어야 합니다")
    return errors


def _check_news(item, path: str) -> list[str]:
    if not isinstance(item, dict):
        return [f"{path}: 객체여야 합니다"]
    errors = []
    region = item.get("region")
    if region not in REGIONS:
        errors.append(f"{path}.region: 'kr' 또는 'global'이어야 합니다")
    for key in ("source", "title"):
        if not _text(item.get(key)):
            errors.append(f"{path}.{key}: 비어 있지 않은 문자열이어야 합니다")
    if not _url(item.get("url")):
        errors.append(f"{path}.url: http:// 또는 https://로 시작하는 주소여야 합니다")
    summary = item.get("summary")
    if not (isinstance(summary, list) and len(summary) == 3 and all(_text(line) for line in summary)):
        errors.append(f"{path}.summary: 비어 있지 않은 문장 3개여야 합니다")
    if region == "global" and not _text(item.get("original_title")):
        errors.append(f"{path}.original_title: 해외 기사는 원제목이 필요합니다")
    return errors


def _check_tech(tech: dict, topic_ids: set[str]) -> list[str]:
    errors = []
    for key in ("topic_id", "title", "category"):
        if not _text(tech.get(key)):
            errors.append(f"tech.{key}: 비어 있지 않은 문자열이어야 합니다")
    pick = tech.get("pick")
    if pick not in PICKS:
        errors.append("tech.pick: 'trend' 또는 'curriculum'이어야 합니다")
    elif pick == "curriculum" and tech.get("topic_id") not in topic_ids:
        errors.append(f"tech.topic_id: curriculum.yaml에 없는 주제입니다 ({tech.get('topic_id')!r})")
    minutes = tech.get("reading_minutes")
    if not (isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= 30):
        errors.append("tech.reading_minutes: 1~30 사이 정수여야 합니다")

    sections = tech.get("sections")
    if not isinstance(sections, dict):
        errors.append("tech.sections: 필수 객체입니다")
        return errors
    for key in TEXT_SECTIONS:
        if not _text(sections.get(key)):
            errors.append(f"tech.sections.{key}: 비어 있지 않은 문자열이어야 합니다")
    reading = sections.get("further_reading")
    if not (isinstance(reading, list) and 1 <= len(reading) <= 3):
        errors.append("tech.sections.further_reading: 1~3건이어야 합니다")
    else:
        for index, link in enumerate(reading):
            if not (isinstance(link, dict) and _text(link.get("title")) and _url(link.get("url"))):
                errors.append(
                    f"tech.sections.further_reading[{index}]: title과 http(s):// url이 필요합니다"
                )
    return errors


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _url(value) -> bool:
    return isinstance(value, str) and bool(URL_PATTERN.match(value))
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv/Scripts/python -m pytest tests/test_validate.py -v`
Expected: 25 passed

- [ ] **Step 6: 커밋**

```bash
git add validate.py tests/__init__.py tests/factories.py tests/test_validate.py
git commit -m "feat: validate brief JSON with field-level error messages" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: HTML 렌더링 (템플릿, 스타일, 안전한 마크다운)

**Files:**
- Create: `render.py`, `templates/_layout.html`, `templates/brief.html`, `templates/archive.html`, `templates/style.css`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `tests.factories.make_brief` (테스트만)
- Produces:
  - `render.TEMPLATES: Path` (`templates/` 폴더)
  - `render.page_path(day: str) -> str` — `"2026-10-08"` → `"2026/10/08.html"`
  - `render.date_label(day: str) -> str` — `"2026.10.08 (목)"`
  - `render.md_to_html(text: str) -> Markup` — 원본 HTML 태그는 글자로 이스케이프, `http(s)://`·`#`가 아닌 링크·이미지 주소는 제거
  - `render.render_brief_page(brief: dict, *, base: str, prev_day: str | None, next_day: str | None, curriculum_no: int | None) -> str` — `base`는 `docs/` 루트까지의 상대 경로 (`"../../"` 또는 `""`)
  - `render.render_archive(briefs: list[dict]) -> str` — `docs/archive.html` 내용

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_render.py`:
```python
from render import date_label, md_to_html, page_path, render_archive, render_brief_page
from tests.factories import make_brief


def test_page_path():
    assert page_path("2026-10-08") == "2026/10/08.html"


def test_date_label_has_korean_weekday():
    assert date_label("2026-10-08") == "2026.10.08 (목)"


def test_md_to_html_renders_markdown():
    assert "<strong>굵게</strong>" in md_to_html("**굵게**")


def test_md_to_html_escapes_raw_html():
    out = md_to_html("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_md_to_html_escapes_code_block_once():
    out = md_to_html("```python\nif a < b:\n    pass\n```")
    assert "a &lt; b" in out
    assert "&amp;lt;" not in out


def test_md_to_html_drops_unsafe_links():
    out = md_to_html("[누르기](javascript:alert(1)) [안전](https://example.com)")
    assert "javascript:" not in out
    assert 'href="https://example.com"' in out


def test_brief_page_contents():
    out = render_brief_page(
        make_brief(), base="../../", prev_day="2026-10-07", next_day=None, curriculum_no=1
    )
    assert '<link rel="stylesheet" href="../../style.css">' in out
    assert "2026.10.08 (목)" in out
    assert "오늘의 핵심 이슈" in out
    assert "<h3>국내</h3>" in out
    assert "<h3>해외</h3>" in out
    assert "Global Story" in out
    assert "커리큘럼 #1" in out
    assert 'href="../../2026/10/07.html"' in out
    assert '<span class="disabled">다음 ▶</span>' in out
    assert "<strong>지연 시간</strong>" in out
    assert 'href="../../archive.html"' in out


def test_brief_page_hides_empty_region():
    brief = make_brief()
    brief["news"] = [n for n in brief["news"] if n["region"] == "kr"]
    out = render_brief_page(brief, base="", prev_day=None, next_day=None, curriculum_no=1)
    assert "<h3>국내</h3>" in out
    assert "<h3>해외</h3>" not in out


def test_brief_page_without_news_hides_section():
    brief = make_brief()
    brief["news"] = []
    out = render_brief_page(brief, base="", prev_day=None, next_day=None, curriculum_no=1)
    assert "IT 뉴스" not in out


def test_brief_page_trend_badge():
    brief = make_brief()
    brief["tech"]["pick"] = "trend"
    out = render_brief_page(brief, base="", prev_day=None, next_day=None, curriculum_no=None)
    assert "트렌드 픽" in out
    assert "커리큘럼 #" not in out


def test_brief_page_shows_notes():
    brief = make_brief()
    brief["notes"] = ["일부 소스 수집 실패: TechCrunch"]
    out = render_brief_page(brief, base="", prev_day=None, next_day=None, curriculum_no=1)
    assert "일부 소스 수집 실패: TechCrunch" in out


def test_brief_page_escapes_text_fields():
    brief = make_brief()
    brief["headline"] = "<b>위험</b>"
    out = render_brief_page(brief, base="", prev_day=None, next_day=None, curriculum_no=1)
    assert "&lt;b&gt;위험&lt;/b&gt;" in out


def test_archive_orders_newest_first_and_groups_by_category():
    older = make_brief("2026-10-07")
    older["tech"].update(title="DNS 동작 방식", category="네트워크")
    out = render_archive([older, make_brief("2026-10-08")])
    assert out.index("2026.10.08") < out.index("2026.10.07")
    assert 'href="2026/10/08.html"' in out
    assert "<h3>네트워크</h3>" in out
    assert "<h3>웹</h3>" in out
    assert "뉴스 2건" in out
    assert '<link rel="stylesheet" href="style.css">' in out
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `.venv/Scripts/python -m pytest tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 3: 템플릿 작성**

`templates/_layout.html`:
```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}{% endblock %}</title>
<link rel="stylesheet" href="{{ base }}style.css">
<script>
try { var saved = localStorage.getItem("theme"); if (saved) document.documentElement.dataset.theme = saved; } catch (e) {}
</script>
</head>
<body>
<main class="page">
  <header class="masthead">
    <div class="masthead-top">
      <a class="brand" href="{{ base }}index.html">Daily Tech Brief</a>
      <button class="theme-toggle" type="button" aria-label="다크 모드 전환">◐</button>
    </div>
    {% block masthead %}{% endblock %}
  </header>
  {% block content %}{% endblock %}
</main>
<script>
document.querySelector(".theme-toggle").addEventListener("click", function () {
  var root = document.documentElement;
  var dark = root.dataset.theme
    ? root.dataset.theme === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
  try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
});
</script>
</body>
</html>
```

`templates/brief.html`:
```html
{% extends "_layout.html" %}
{% block title %}Daily Tech Brief · {{ date_label }}{% endblock %}
{% block masthead %}
    <p class="date">{{ date_label }}</p>
    <nav class="day-nav">
      {% if prev_path %}<a href="{{ base }}{{ prev_path }}">◀ 이전</a>{% else %}<span class="disabled">◀ 이전</span>{% endif %}
      <a href="{{ base }}archive.html">목록</a>
      {% if next_path %}<a href="{{ base }}{{ next_path }}">다음 ▶</a>{% else %}<span class="disabled">다음 ▶</span>{% endif %}
    </nav>
{% endblock %}
{% block content %}
  <section class="headline">
    <h2>오늘의 한 줄</h2>
    <p>{{ brief.headline }}</p>
  </section>

  {% if kr_news or global_news %}
  <section class="news">
    <h2>IT 뉴스</h2>
    {% for label, items in [("국내", kr_news), ("해외", global_news)] if items %}
    <h3>{{ label }}</h3>
    <ol class="news-list">
      {% for item in items %}
      <li class="news-item">
        <a class="news-title" href="{{ item.url }}" target="_blank" rel="noopener">{{ item.title }}</a>
        <span class="source">{{ item.source }}</span>
        {% if item.original_title %}<p class="original-title">{{ item.original_title }}</p>{% endif %}
        <ul class="summary">
          {% for line in item.summary %}<li>{{ line }}</li>{% endfor %}
        </ul>
      </li>
      {% endfor %}
    </ol>
    {% endfor %}
  </section>
  {% endif %}

  <section class="tech">
    <h2>오늘의 기술</h2>
    <h3 class="tech-title">{{ tech.title }}</h3>
    <p class="tech-meta">
      <span class="badge">{% if tech.pick == "trend" %}트렌드 픽{% else %}커리큘럼 #{{ curriculum_no }}{% endif %}</span>
      <span>{{ tech.category }}</span>
      <span>⏱ {{ tech.reading_minutes }}분</span>
    </p>
    <p class="definition">{{ tech.sections.definition }}</p>
    <h4>왜 필요한가</h4>
    {{ tech.sections.why | md }}
    <h4>동작 원리</h4>
    {{ tech.sections.how | md }}
    <h4>예시</h4>
    {{ tech.sections.example | md }}
    <h4>언제 쓰고 언제 안 쓰나</h4>
    {{ tech.sections.when | md }}
    <h4>더 읽을거리</h4>
    <ul class="further">
      {% for link in tech.sections.further_reading %}<li><a href="{{ link.url }}" target="_blank" rel="noopener">{{ link.title }}</a></li>{% endfor %}
    </ul>
  </section>

  {% if brief.notes %}
  <footer class="notes">
    {% for note in brief.notes %}<p>{{ note }}</p>{% endfor %}
  </footer>
  {% endif %}
{% endblock %}
```

`templates/archive.html`:
```html
{% extends "_layout.html" %}
{% block title %}지난 브리핑 · Daily Tech Brief{% endblock %}
{% block masthead %}
    <p class="date">지난 브리핑</p>
    <nav class="day-nav"><a href="{{ base }}index.html">최신 브리핑</a></nav>
{% endblock %}
{% block content %}
  <section>
    <h2>날짜별</h2>
    <ul class="archive-list">
      {% for entry in entries %}
      <li><a href="{{ base }}{{ entry.path }}">{{ entry.label }}</a> — {{ entry.title }} · 뉴스 {{ entry.news_count }}건</li>
      {% endfor %}
    </ul>
  </section>
  <section>
    <h2>다룬 기술</h2>
    {% for category, items in by_category %}
    <h3>{{ category }}</h3>
    <ul class="archive-list">
      {% for entry in items %}
      <li><a href="{{ base }}{{ entry.path }}">{{ entry.title }}</a> <span class="muted">{{ entry.label }}</span></li>
      {% endfor %}
    </ul>
    {% endfor %}
  </section>
{% endblock %}
```

`templates/style.css`:
```css
:root {
  --bg: #fbfaf7;
  --surface: #ffffff;
  --text: #1f2328;
  --muted: #6a6f76;
  --border: #e4e2dc;
  --accent: #2f6fdb;
  --badge-bg: #e8f0fd;
  --code-bg: #f3f2ee;
  color-scheme: light;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #16181c;
    --surface: #1d2025;
    --text: #e6e6e3;
    --muted: #9aa0a8;
    --border: #2e3238;
    --accent: #7aa7ff;
    --badge-bg: #22314d;
    --code-bg: #24272d;
    color-scheme: dark;
  }
}

:root[data-theme="dark"] {
  --bg: #16181c;
  --surface: #1d2025;
  --text: #e6e6e3;
  --muted: #9aa0a8;
  --border: #2e3238;
  --accent: #7aa7ff;
  --badge-bg: #22314d;
  --code-bg: #24272d;
  color-scheme: dark;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  line-height: 1.7;
  word-break: keep-all;
  overflow-wrap: anywhere;
}

.page { max-width: 720px; margin: 0 auto; padding: 24px 16px 64px; }
a { color: var(--accent); }

.masthead { border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }
.masthead-top { display: flex; justify-content: space-between; align-items: center; }
.brand { font-weight: 800; font-size: 1.25rem; color: var(--text); text-decoration: none; }
.theme-toggle {
  width: 36px; height: 36px; border-radius: 999px; cursor: pointer;
  background: none; border: 1px solid var(--border); color: var(--text); font-size: 1rem;
}
.date { margin: 4px 0 8px; color: var(--muted); }
.day-nav { display: flex; gap: 16px; font-size: 0.95rem; }
.day-nav .disabled { color: var(--muted); opacity: 0.5; }

h2 { font-size: 1.1rem; margin: 32px 0 12px; }
h3 { font-size: 1rem; color: var(--muted); margin: 20px 0 8px; }
h4 { font-size: 1rem; margin: 24px 0 8px; }

.headline p {
  margin: 0; padding: 16px; font-size: 1.15rem; font-weight: 600;
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
}

.news-list { list-style: none; padding: 0; margin: 0; }
.news-item {
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 14px 16px; margin-bottom: 12px;
}
.news-title { font-weight: 700; color: var(--text); text-decoration: none; }
.news-title:hover { color: var(--accent); }
.source { margin-left: 8px; font-size: 0.8rem; color: var(--muted); white-space: nowrap; }
.original-title { margin: 2px 0 0; font-size: 0.85rem; color: var(--muted); }
.summary { margin: 8px 0 0; padding-left: 1.1em; }

.tech {
  margin-top: 32px; padding: 4px 20px 20px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
}
.tech-title { font-size: 1.35rem; color: var(--text); margin: 8px 0; }
.tech-meta {
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  margin: 0 0 12px; color: var(--muted); font-size: 0.85rem;
}
.badge { background: var(--badge-bg); color: var(--accent); border-radius: 999px; padding: 2px 10px; font-weight: 700; }
.definition { font-weight: 600; border-left: 3px solid var(--accent); padding-left: 12px; }

pre {
  background: var(--code-bg); border-radius: 8px; padding: 12px 14px;
  overflow-x: auto; font-size: 0.875rem; line-height: 1.5;
}
code { font-family: "D2Coding", Consolas, "SF Mono", monospace; }
:not(pre) > code { background: var(--code-bg); padding: 1px 5px; border-radius: 4px; font-size: 0.9em; }
table { display: block; overflow-x: auto; border-collapse: collapse; }
th, td { border: 1px solid var(--border); padding: 6px 10px; }

.notes { margin-top: 32px; font-size: 0.8rem; color: var(--muted); }
.archive-list { padding-left: 1.1em; }
.muted { color: var(--muted); font-size: 0.85rem; }
```

- [ ] **Step 4: `render.py` 작성**

`render.py`:
```python
"""브리핑 데이터를 HTML 문자열로 만든다."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markupsafe import Markup

TEMPLATES = Path(__file__).resolve().parent / "templates"
WEEKDAYS = "월화수목금토일"
SAFE_HREF = re.compile(r"^(https?://|#)", re.IGNORECASE)


class _LinkFilter(Treeprocessor):
    """http(s)://나 #로 시작하지 않는 링크·이미지 주소를 지운다."""

    def run(self, root):
        for element in root.iter("a"):
            if not SAFE_HREF.match(element.get("href", "")):
                element.attrib.pop("href", None)
        for element in root.iter("img"):
            if not SAFE_HREF.match(element.get("src", "")):
                element.attrib.pop("src", None)


class _SafeMarkdown(Extension):
    """원본 HTML을 해석하지 않고 글자로 보여 주게 한다."""

    def extendMarkdown(self, md):
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")
        md.treeprocessors.register(_LinkFilter(md), "link_filter", 0)


def md_to_html(text: str) -> Markup:
    return Markup(markdown.markdown(text, extensions=["fenced_code", "tables", _SafeMarkdown()]))


def page_path(day: str) -> str:
    year, month, dd = day.split("-")
    return f"{year}/{month}/{dd}.html"


def date_label(day: str) -> str:
    value = date.fromisoformat(day)
    return f"{value:%Y.%m.%d} ({WEEKDAYS[value.weekday()]})"


def render_brief_page(
    brief: dict,
    *,
    base: str,
    prev_day: str | None,
    next_day: str | None,
    curriculum_no: int | None,
) -> str:
    news = brief["news"]
    return _env().get_template("brief.html").render(
        base=base,
        brief=brief,
        tech=brief["tech"],
        date_label=date_label(brief["date"]),
        kr_news=[item for item in news if item["region"] == "kr"],
        global_news=[item for item in news if item["region"] == "global"],
        prev_path=page_path(prev_day) if prev_day else None,
        next_path=page_path(next_day) if next_day else None,
        curriculum_no=curriculum_no,
    )


def render_archive(briefs: list[dict]) -> str:
    entries = [
        {
            "label": f"{date.fromisoformat(b['date']):%Y.%m.%d}",
            "title": b["tech"]["title"],
            "category": b["tech"]["category"],
            "news_count": len(b["news"]),
            "path": page_path(b["date"]),
        }
        for b in sorted(briefs, key=lambda b: b["date"], reverse=True)
    ]
    by_category: dict[str, list[dict]] = {}
    for entry in entries:
        by_category.setdefault(entry["category"], []).append(entry)
    return _env().get_template("archive.html").render(
        base="", entries=entries, by_category=sorted(by_category.items())
    )


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["md"] = md_to_html
    return env
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv/Scripts/python -m pytest tests/test_render.py -v`
Expected: 13 passed. `test_md_to_html_escapes_raw_html`이 실패하면 설치된 Markdown 버전의 처리기 이름을 `.venv/Scripts/python -c "import markdown; m=markdown.Markdown(); print(list(m.preprocessors), list(m.inlinePatterns))"`로 확인하고 `_SafeMarkdown`에서 지우는 이름을 맞춘다.

- [ ] **Step 6: 커밋**

```bash
git add render.py templates tests/test_render.py
git commit -m "feat: render brief and archive pages with safe markdown" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 빌드 CLI (`build.py`)

**Files:**
- Create: `build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `collector.collect.normalize_url`, `validate.validate_brief`, `render.TEMPLATES`, `render.page_path`, `render.render_brief_page`, `render.render_archive`
- Produces:
  - `build.BuildError(Exception)` — 메시지는 사람이 읽을 오류 설명 (검사 실패 시 오류 목록을 줄바꿈으로 연결)
  - `build.build(day: str, root: Path = ROOT, force: bool = False) -> str` — `"built"` 또는 `"skipped"`
  - `build.main(argv: list[str] | None = None) -> int` — 성공/건너뜀 0, 실패 1. 옵션 `--force`, 숨김 옵션 `--root`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_build.py`:
```python
import json

import pytest
import yaml

import build
from build import BuildError
from tests.factories import make_brief

CURRICULUM = {
    "topics": [
        {"id": "http-caching", "title": "HTTP 캐싱", "category": "웹", "covered_on": None},
        {"id": "dns", "title": "DNS 동작 방식", "category": "네트워크", "covered_on": None},
    ]
}


@pytest.fixture
def site(tmp_path):
    (tmp_path / "curriculum.yaml").write_text(
        yaml.safe_dump(CURRICULUM, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (tmp_path / "data" / "briefs").mkdir(parents=True)
    return tmp_path


def write_brief(root, brief):
    path = root / "data" / "briefs" / f"{brief['date']}.json"
    path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")


def read(path):
    return path.read_text(encoding="utf-8")


def test_build_creates_pages(site):
    write_brief(site, make_brief())
    assert build.build("2026-10-08", site) == "built"
    docs = site / "docs"
    assert 'href="../../style.css"' in read(docs / "2026/10/08.html")
    index = read(docs / "index.html")
    assert "오늘의 핵심 이슈" in index
    assert 'href="style.css"' in index
    assert 'href="2026/10/08.html"' in read(docs / "archive.html")
    assert (docs / "style.css").exists()
    assert (docs / ".nojekyll").exists()


def test_build_skips_existing_page(site):
    write_brief(site, make_brief())
    page = site / "docs/2026/10/08.html"
    page.parent.mkdir(parents=True)
    page.write_text("OLD", encoding="utf-8")
    assert build.build("2026-10-08", site) == "skipped"
    assert read(page) == "OLD"
    assert not (site / "docs/index.html").exists()


def test_build_force_overwrites(site):
    write_brief(site, make_brief())
    page = site / "docs/2026/10/08.html"
    page.parent.mkdir(parents=True)
    page.write_text("OLD", encoding="utf-8")
    assert build.build("2026-10-08", site, force=True) == "built"
    assert read(page) != "OLD"


def test_build_rejects_invalid_brief(site):
    brief = make_brief()
    brief["news"][0]["summary"] = ["하나"]
    write_brief(site, brief)
    with pytest.raises(BuildError) as error:
        build.build("2026-10-08", site)
    assert "news[0].summary" in str(error.value)
    assert not (site / "docs").exists()


def test_build_missing_brief(site):
    with pytest.raises(BuildError, match="파일이 없습니다"):
        build.build("2026-10-08", site)


def test_build_broken_json(site):
    (site / "data/briefs/2026-10-08.json").write_text("{", encoding="utf-8")
    with pytest.raises(BuildError, match="JSON"):
        build.build("2026-10-08", site)


def test_build_links_neighbor_days(site):
    write_brief(site, make_brief("2026-10-07"))
    build.build("2026-10-07", site)
    write_brief(site, make_brief("2026-10-08"))
    build.build("2026-10-08", site)
    docs = site / "docs"
    assert 'href="../../2026/10/08.html"' in read(docs / "2026/10/07.html")
    assert 'href="../../2026/10/07.html"' in read(docs / "2026/10/08.html")
    index = read(docs / "index.html")
    assert "2026.10.08 (목)" in index
    assert 'href="2026/10/07.html"' in index


def test_build_ignores_unpublished_briefs(site):
    write_brief(site, make_brief("2026-10-06"))
    write_brief(site, make_brief("2026-10-08"))
    build.build("2026-10-08", site)
    assert "2026/10/06.html" not in read(site / "docs/2026/10/08.html")
    assert "2026/10/06.html" not in read(site / "docs/archive.html")


def test_build_updates_seen_and_curriculum(site):
    write_brief(site, make_brief())
    build.build("2026-10-08", site)
    seen = json.loads(read(site / "data/seen.json"))
    assert "https://example.com/story" in seen
    assert "https://news.hada.io/topic?id=1" in seen
    topics = yaml.safe_load(read(site / "curriculum.yaml"))["topics"]
    assert topics[0]["covered_on"] == "2026-10-08"
    assert topics[1]["covered_on"] is None


def test_build_trend_pick_leaves_curriculum(site):
    brief = make_brief()
    brief["tech"].update(pick="trend", topic_id="brand-new-thing")
    write_brief(site, brief)
    build.build("2026-10-08", site)
    topics = yaml.safe_load(read(site / "curriculum.yaml"))["topics"]
    assert all(topic["covered_on"] is None for topic in topics)
    assert "트렌드 픽" in read(site / "docs/2026/10/08.html")


def test_main_exit_codes(site, capsys):
    write_brief(site, make_brief())
    assert build.main(["2026-10-08", "--root", str(site)]) == 0
    assert build.main(["2026-10-08", "--root", str(site)]) == 0
    assert "건너뜁니다" in capsys.readouterr().out

    assert build.main(["20261008", "--root", str(site)]) == 1

    bad = make_brief("2026-10-09")
    bad["news"][0]["summary"] = []
    write_brief(site, bad)
    assert build.main(["2026-10-09", "--root", str(site)]) == 1
    assert "news[0].summary" in capsys.readouterr().err
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `.venv/Scripts/python -m pytest tests/test_build.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'build'`

- [ ] **Step 3: 구현 작성**

`build.py`:
```python
"""브리핑 JSON을 검사하고 docs/ 아래에 HTML 페이지를 만든다.

사용법: python build.py YYYY-MM-DD [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import yaml

from collector.collect import normalize_url
from render import TEMPLATES, page_path, render_archive, render_brief_page
from validate import validate_brief

ROOT = Path(__file__).resolve().parent
DAY_BASE = "../../"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class BuildError(Exception):
    """브리핑을 페이지로 만들 수 없을 때 발생한다."""


def build(day: str, root: Path = ROOT, force: bool = False) -> str:
    """하루치 페이지를 만들고 'built'를, 이미 있으면 'skipped'를 돌려준다."""
    docs = root / "docs"
    target = docs / page_path(day)
    if target.exists() and not force:
        return "skipped"

    brief = _load_brief(root / "data" / "briefs" / f"{day}.json")
    topics = _load_topics(root / "curriculum.yaml")
    errors = validate_brief(brief, day, {topic["id"] for topic in topics})
    if errors:
        raise BuildError("\n".join(errors))

    # 페이지가 이미 발행된 날짜와 오늘만 이전/다음 링크와 목록에 넣는다.
    briefs = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (root / "data" / "briefs").glob("*.json")
        if path.stem != day and (docs / page_path(path.stem)).exists()
    }
    briefs[day] = brief
    days = sorted(briefs)
    numbers = {topic["id"]: no for no, topic in enumerate(topics, start=1)}

    def render_day(d: str, base: str) -> str:
        i = days.index(d)
        tech = briefs[d]["tech"]
        return render_brief_page(
            briefs[d],
            base=base,
            prev_day=days[i - 1] if i > 0 else None,
            next_day=days[i + 1] if i + 1 < len(days) else None,
            curriculum_no=numbers.get(tech["topic_id"]) if tech["pick"] == "curriculum" else None,
        )

    _write(target, render_day(day, DAY_BASE))
    position = days.index(day)
    if position > 0:  # 전날 페이지의 '다음' 링크를 새 페이지로 이어 준다
        previous = days[position - 1]
        _write(docs / page_path(previous), render_day(previous, DAY_BASE))
    _write(docs / "index.html", render_day(days[-1], ""))
    _write(docs / "archive.html", render_archive([briefs[d] for d in days]))
    shutil.copyfile(TEMPLATES / "style.css", docs / "style.css")
    (docs / ".nojekyll").touch()

    _add_seen(root / "data" / "seen.json", [item["url"] for item in brief["news"]])
    if brief["tech"]["pick"] == "curriculum":
        _mark_covered(root / "curriculum.yaml", brief["tech"]["topic_id"], day)
    return "built"


def _load_brief(path: Path) -> dict:
    if not path.exists():
        raise BuildError(f"{path} 파일이 없습니다")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BuildError(f"{path.name}: JSON 문법 오류 ({exc})") from exc


def _load_topics(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("topics", [])


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _add_seen(path: Path, urls: list[str]) -> None:
    seen = set(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else set()
    seen.update(normalize_url(url) for url in urls)
    _write(path, json.dumps(sorted(seen), ensure_ascii=False, indent=2) + "\n")


def _mark_covered(path: Path, topic_id: str, day: str) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for topic in data["topics"]:
        if topic["id"] == topic_id and not topic.get("covered_on"):
            topic["covered_on"] = day
    _write(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="브리핑 JSON을 HTML 페이지로 만든다")
    parser.add_argument("date", help="브리핑 날짜 (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="이미 있는 페이지를 덮어쓴다")
    parser.add_argument("--root", default=str(ROOT), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        if not DATE_PATTERN.match(args.date):
            raise ValueError
        date.fromisoformat(args.date)
    except ValueError:
        print(f"날짜 형식이 잘못되었습니다: {args.date} (예: 2026-10-08)", file=sys.stderr)
        return 1

    try:
        status = build(args.date, Path(args.root), args.force)
    except BuildError as exc:
        print("브리핑 검사 실패:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    if status == "skipped":
        print(f"docs/{page_path(args.date)} 페이지가 이미 있어 건너뜁니다 (--force로 덮어쓰기)")
    else:
        print(f"docs/{page_path(args.date)} 생성 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/Scripts/python -m pytest tests/test_build.py -v`
Expected: 11 passed

- [ ] **Step 5: 전체 테스트 확인**

Run: `.venv/Scripts/python -m pytest -q`
Expected: 63 passed

- [ ] **Step 6: 커밋**

```bash
git add build.py tests/test_build.py
git commit -m "feat: build daily pages, archive, and state files from brief JSON" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: RSS 소스 확정과 실제 수집 확인

**Files:**
- Create: `collector/sources.yaml`, `data/seen.json`

**Interfaces:**
- Consumes: `collector.collect.fetch`, `python collector/collect.py`
- Produces: 실제로 응답하는 소스만 담은 `collector/sources.yaml` (Task 10의 네트워크 허용 목록이 이 파일의 도메인에서 나온다)

- [ ] **Step 1: 후보 소스 목록 작성**

`collector/sources.yaml`:
```yaml
sources:
  - name: GeekNews
    url: https://news.hada.io/rss/news
    region: kr
  - name: 요즘IT
    url: https://yozm.wishket.com/magazine/feed/
    region: kr
  - name: 전자신문
    url: https://rss.etnews.com/Section901.xml
    region: kr
  - name: 카카오 기술블로그
    url: https://tech.kakao.com/feed/
    region: kr
  - name: 우아한형제들 기술블로그
    url: https://techblog.woowahan.com/feed/
    region: kr
  - name: 토스 기술블로그
    url: https://toss.tech/rss.xml
    region: kr
  - name: 네이버 D2
    url: https://d2.naver.com/d2.atom
    region: kr
  - name: Hacker News
    url: https://hnrss.org/frontpage?points=100
    region: global
  - name: TechCrunch
    url: https://techcrunch.com/feed/
    region: global
  - name: The Verge
    url: https://www.theverge.com/rss/index.xml
    region: global
  - name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/technology-lab
    region: global
  - name: GitHub Blog
    url: https://github.blog/feed/
    region: global
```

`data/seen.json`:
```json
[]
```

- [ ] **Step 2: 소스별로 피드가 열리는지 확인**

Run:
```bash
.venv/Scripts/python -c "
import feedparser, yaml
from collector.collect import fetch
for s in yaml.safe_load(open('collector/sources.yaml', encoding='utf-8'))['sources']:
    try:
        entries = feedparser.parse(fetch(s['url'])).entries
        print('OK  ' if entries else 'EMPTY', s['name'], len(entries))
    except Exception as e:
        print('FAIL', s['name'], type(e).__name__, e)
"
```
Expected: 소스마다 `OK <이름> <글 수>`, `EMPTY ...`, 또는 `FAIL ...`

- [ ] **Step 3: 실패한 소스 고치기**

`FAIL`이나 `EMPTY`인 소스마다: WebSearch(`"<사이트 이름> RSS"`)나 사이트 HTML의 `<link rel="alternate" type="application/rss+xml">`에서 피드 주소를 찾아 `url`을 바꾸고 Step 2를 다시 실행한다. 찾을 수 없으면 그 항목을 지운다. 국내 `kr` 소스가 최소 3개, 해외 `global` 소스가 최소 3개 남아야 한다.

- [ ] **Step 4: 전체 수집 실행**

Run: `.venv/Scripts/python collector/collect.py`
Expected: `...data/raw/<오늘>.json: 기사 N건, 실패한 소스 0개` (N은 보통 30 이상, 국내 기술블로그는 48시간 안에 글이 없으면 0건이어도 정상)

- [ ] **Step 5: 확인용 수집 파일 지우고 커밋**

확인용 파일은 Task 8에서 다시 만들므로 지운다.
```bash
rm -rf data/raw
git add collector/sources.yaml data/seen.json
git commit -m "feat: add verified RSS sources" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 커리큘럼, 작업 지침, README

**Files:**
- Create: `curriculum.yaml`, `ROUTINE.md`, `README.md`, `docs/.nojekyll`

**Interfaces:**
- Consumes: `build.py`가 읽는 `curriculum.yaml` 형식 (`topics[].id/title/category/covered_on`), `tests/factories.py`의 `BRIEF`(ROUTINE.md가 예시로 가리킴)
- Produces: 클라우드 루틴이 읽을 `ROUTINE.md`

- [ ] **Step 1: `curriculum.yaml` 작성**

분야가 번갈아 나오도록 배치한다. 이 파일은 `build.py`가 다시 쓰므로 주석을 넣지 않는다.

```yaml
topics:
- id: http-caching
  title: HTTP 캐싱
  category: 웹
  covered_on: null
- id: db-index
  title: 데이터베이스 인덱스와 B-Tree
  category: 데이터베이스
  covered_on: null
- id: tcp-handshake
  title: TCP 3-way 핸드셰이크
  category: 네트워크
  covered_on: null
- id: process-thread
  title: 프로세스와 스레드
  category: 운영체제
  covered_on: null
- id: docker
  title: 도커 컨테이너
  category: 클라우드/인프라
  covered_on: null
- id: transformer
  title: 트랜스포머 구조
  category: AI/ML
  covered_on: null
- id: oauth-oidc
  title: OAuth 2.0과 OIDC
  category: 보안
  covered_on: null
- id: git-internals
  title: Git 내부 구조
  category: 언어/도구
  covered_on: null
- id: rest-vs-graphql
  title: REST와 GraphQL
  category: 웹
  covered_on: null
- id: transaction-isolation
  title: 트랜잭션 격리 수준
  category: 데이터베이스
  covered_on: null
- id: dns
  title: DNS 동작 방식
  category: 네트워크
  covered_on: null
- id: virtual-memory
  title: 가상 메모리
  category: 운영체제
  covered_on: null
- id: kubernetes
  title: 쿠버네티스 기초
  category: 클라우드/인프라
  covered_on: null
- id: rag
  title: RAG(검색 증강 생성)
  category: AI/ML
  covered_on: null
- id: jwt
  title: JWT
  category: 보안
  covered_on: null
- id: garbage-collection
  title: 가비지 컬렉션
  category: 언어/도구
  covered_on: null
- id: cors
  title: CORS
  category: 웹
  covered_on: null
- id: nosql-types
  title: NoSQL의 종류
  category: 데이터베이스
  covered_on: null
- id: https-tls
  title: HTTPS와 TLS
  category: 네트워크
  covered_on: null
- id: deadlock
  title: 데드락
  category: 운영체제
  covered_on: null
- id: ci-cd
  title: CI/CD 파이프라인
  category: 클라우드/인프라
  covered_on: null
- id: embedding-vector-db
  title: 임베딩과 벡터 DB
  category: AI/ML
  covered_on: null
- id: owasp-top10
  title: OWASP Top 10
  category: 보안
  covered_on: null
- id: regex
  title: 정규표현식
  category: 언어/도구
  covered_on: null
- id: web-rendering
  title: CSR, SSR, SSG
  category: 웹
  covered_on: null
- id: redis-caching
  title: Redis 캐싱 전략
  category: 데이터베이스
  covered_on: null
- id: load-balancer
  title: 로드 밸런서
  category: 네트워크
  covered_on: null
- id: async-io
  title: 비동기 I/O와 이벤트 루프
  category: 운영체제
  covered_on: null
- id: serverless
  title: 서버리스
  category: 클라우드/인프라
  covered_on: null
- id: ai-agent
  title: AI 에이전트와 도구 호출
  category: AI/ML
  covered_on: null
- id: password-hashing
  title: 비밀번호 해싱
  category: 보안
  covered_on: null
- id: websocket
  title: WebSocket
  category: 웹
  covered_on: null
- id: db-replication-sharding
  title: 복제와 샤딩
  category: 데이터베이스
  covered_on: null
- id: cdn
  title: CDN
  category: 네트워크
  covered_on: null
- id: iac-terraform
  title: IaC와 Terraform
  category: 클라우드/인프라
  covered_on: null
```

- [ ] **Step 2: `ROUTINE.md` 작성**

````markdown
# 매일 브리핑 작업 지침

클라우드 예약 작업에서 Claude가 매일 아침 이 절차를 순서대로 수행한다. 마지막에 7단계 형식으로 짧게 보고한다.
데이터 형식은 `design/2026-10-08-daily-tech-brief-design.md`의 4.4절, 정상 예시는 `tests/factories.py`의 `BRIEF`를 따른다.

## 0. 준비

```bash
python -m pip install -q -r requirements.txt || python -m pip install -q --break-system-packages -r requirements.txt
DAY=$(TZ=Asia/Seoul date +%F)
echo "$DAY"
```

`docs/<YYYY>/<MM>/<DD>.html`(오늘 날짜)이 이미 있으면 "오늘 브리핑은 이미 발행됨"이라고 보고하고 끝낸다.

## 1. 수집

```bash
python collector/collect.py --date "$DAY"
```

실패한 소스가 있으면 이름과 오류를 기억해 둔다. 오류가 `HTTP 403`이거나 `host_not_allowed`가 들어 있으면 네트워크 허용 목록 문제일 가능성이 높으니 보고에 해당 도메인을 적는다.

## 2. 뉴스 선별과 요약

`data/raw/$DAY.json`의 `items`에서 고른다.

- 국내(`kr`) 4~5건, 해외(`global`) 4~5건. 후보가 모자라면 있는 만큼만 쓴다.
- 우선순위: 개발자에게 영향이 큰 소식(새 기술·제품 출시, 주요 서비스 변경, 보안 사고, 업계 큰 흐름) > 깊이 있는 기술 글 > 단순 홍보·인사·투자 소식.
- 같은 사건을 다룬 기사는 하나만 고른다.
- 피드의 `summary`만으로 3문장을 쓰기 어려우면 WebFetch로 원문을 확인한다. 원문을 열 수 없으면 그 기사를 빼고 다음 후보를 쓴다.
- 한쪽 지역 후보가 0건이면 WebSearch로 최근 24시간 이내 해당 지역 IT 뉴스를 찾아 2~3건 보충하고, `notes`에 "국내 소스 수집 실패로 웹 검색 결과를 사용함"(또는 해외)이라고 적는다.
- 수집 실패 소스가 있으면 `notes`에 "일부 소스 수집 실패: 이름1, 이름2"를 적는다.

작성 규칙:

- `title`: 국내 기사는 원제목 그대로. 해외 기사는 자연스러운 한국어로 옮기고 원제목은 `original_title`에 넣는다. 국내 기사의 `original_title`은 `null`.
- `summary`: 정확히 3문장. 기사에 있는 내용만 쓰고, 원문 문장을 옮기지 말고 새로 쓴다. 문장당 80자 안팎.
- `url`: `data/raw`에 있는 `url`을 그대로 쓴다. WebSearch로 보충한 기사는 기사 주소.
- `headline`: 오늘 뉴스 중 가장 중요한 이슈를 한 문장으로.

## 3. 오늘의 기술 선정

1. 오늘 뉴스 여러 건에 반복해 나오거나 큰 발표·출시가 있었던 기술이 **분명히** 있으면 그것을 고른다: `pick: "trend"`, `topic_id`는 영문 소문자와 하이픈으로 새로 짓는다. `data/briefs/`의 지난 브리핑에서 같은 주제를 다뤘다면 고르지 않는다. 애매하면 2번으로 간다.
2. 아니면 `curriculum.yaml`에서 `covered_on`이 `null`인 첫 주제를 고른다: `pick: "curriculum"`, `topic_id`·`title`·`category`는 그 항목 값 그대로.
3. `covered_on`이 `null`인 주제가 하나도 없으면 기존 분야(웹, 데이터베이스, 네트워크, 운영체제, 클라우드/인프라, AI/ML, 보안, 언어/도구)에서 고르게 새 주제 10개를 `curriculum.yaml` 끝에 같은 형식으로 추가한 뒤 2번을 따른다.

## 4. 기술 글 작성

독자는 컴퓨터공학을 공부하는 학생, 난이도는 입문~중급, 분량은 5~10분(한국어 2,000~3,500자).

- `definition`: 한 문장 정의.
- `why`: 어떤 문제를 풀려고 나왔는지, 없으면 무엇이 불편한지.
- `how`: 동작 원리를 단계별로. 번호 목록을 권장.
- `example`: 짧고 실제로 동작하는 코드나 설정 예시. 펜스 코드 블록에 언어를 표시하고 앞뒤에 한두 문장 설명.
- `when`: 쓰면 좋은 경우와 피해야 할 경우.
- `further_reading`: 1~3개. 공식 문서나 신뢰할 수 있는 글. WebFetch로 실제로 열리는지 확인한 주소만.
- `reading_minutes`: 글 전체 글자 수 ÷ 400을 반올림 (1~30).
- 마크다운 안에 HTML 태그를 쓰지 않는다 (글자 그대로 보인다).

## 5. 저장과 빌드

브리핑을 `data/briefs/$DAY.json`에 UTF-8로 저장한 뒤:

```bash
python build.py "$DAY"
```

실패하면 출력된 오류(필드 경로 포함)를 읽고 JSON을 고쳐 다시 실행한다. 최대 2번 재시도하고, 그래도 실패하면 커밋하지 말고 오류를 보고하고 끝낸다.

## 6. 커밋과 푸시

```bash
git add data docs curriculum.yaml
git commit -m "brief: $DAY"
git push origin HEAD:main
```

`main` 푸시가 거부되면:

```bash
git push origin HEAD:claude/brief-$DAY
```

## 7. 보고

- 페이지: https://htdufhc-bit.github.io/daily-tech-brief/
- 뉴스: 국내 N건, 해외 N건
- 오늘의 기술: 제목 (트렌드 픽 / 커리큘럼)
- 실패한 소스와 원인, `main` 대신 다른 브랜치로 푸시했는지 등 특이 사항
````

- [ ] **Step 3: `README.md` 작성**

````markdown
# Daily Tech Brief

매일 아침 국내·해외 IT 뉴스 요약과 "오늘의 기술" 글 한 편을 발행하는 개인 브리핑 페이지.

- 읽기: https://htdufhc-bit.github.io/daily-tech-brief/
- 설계: `design/2026-10-08-daily-tech-brief-design.md`
- 매일 작업 절차: `ROUTINE.md` (Claude Code 클라우드 루틴이 매일 07:07 KST에 실행)

## 로컬에서 실행

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest
.venv/Scripts/python collector/collect.py
.venv/Scripts/python build.py 2026-10-08
```

## 소스와 주제 바꾸기

- 뉴스 소스: `collector/sources.yaml` (새 도메인은 루틴 환경의 네트워크 허용 목록에도 추가)
- 기술 주제: `curriculum.yaml`의 `topics` 끝에 `id`, `title`, `category`, `covered_on: null` 형식으로 추가
````

- [ ] **Step 4: Pages용 빈 파일 만들기**

GitHub Pages에서 `/docs`를 고르려면 폴더가 있어야 하므로 빈 `docs/.nojekyll`을 만든다. 이후에는 `build.py`가 관리한다.

```bash
mkdir -p docs && touch docs/.nojekyll
```

- [ ] **Step 5: 커리큘럼 형식 확인**

Run:
```bash
.venv/Scripts/python -c "
import yaml
t = yaml.safe_load(open('curriculum.yaml', encoding='utf-8'))['topics']
ids = [x['id'] for x in t]
assert len(ids) == len(set(ids)) >= 30, 'id 중복 또는 30개 미만'
assert all(x['covered_on'] is None and x['title'] and x['category'] for x in t)
print(len(ids), 'topics ok')
"
```
Expected: `35 topics ok`

- [ ] **Step 6: 커밋**

```bash
git add curriculum.yaml ROUTINE.md README.md docs/.nojekyll
git commit -m "docs: add curriculum, routine instructions, and README" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 로컬 리허설 (실제 브리핑 1건과 화면 확인)

메인 세션의 Claude가 직접 `ROUTINE.md` 0~5단계를 수행해 지침이 실제로 통하는지 확인한다. 결과물은 확인 후 지운다 (첫 발행은 Task 10의 클라우드 실행이 맡아 전체 경로를 한 번에 검증한다).

**Files:**
- 임시 생성 후 삭제: `data/raw/<오늘>.json`, `data/briefs/<오늘>.json`, `docs/` 생성물
- Create: `.claude/launch.json`
- Modify (필요할 때만): `ROUTINE.md`, `templates/*`

- [ ] **Step 1: `ROUTINE.md` 0~5단계 수행**

`ROUTINE.md`를 읽고 0단계부터 5단계 빌드까지 그대로 수행한다 (Python은 `.venv/Scripts/python`, 날짜는 `DAY=$(TZ=Asia/Seoul date +%F)`). 6단계(커밋·푸시)는 하지 않는다.
Expected: `docs/<YYYY>/<MM>/<DD>.html 생성 완료`

- [ ] **Step 2: 브라우저로 화면 확인**

`.claude/launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "docs",
      "runtimeExecutable": ".venv/Scripts/python",
      "runtimeArgs": ["-m", "http.server", "8765", "--directory", "docs"],
      "port": 8765
    }
  ]
}
```
`preview_start`(name `docs`)로 연 뒤 확인한다:
- 데스크톱 폭: 헤더, 오늘의 한 줄, 국내/해외 뉴스, 오늘의 기술 6개 섹션, 코드 블록이 잘 보인다
- `resize_window` 프리셋 `mobile`: 가로 스크롤이 없고 좌우 여백 16px
- `colorScheme: dark`와 테마 버튼: 색이 바뀌고 글자가 잘 읽힌다
- "목록" 링크로 `archive.html`이 열린다

문제가 있으면 템플릿/CSS를 고치고 `.venv/Scripts/python build.py "$DAY" --force`로 다시 만든 뒤 `.venv/Scripts/python -m pytest -q`가 통과하는지 확인한다. 끝나면 `resize_window` 프리셋 `desktop`으로 되돌리고 `preview_stop`.

- [ ] **Step 3: 지침 보완**

리허설 중 헷갈렸거나 검사에 걸린 부분이 있으면 `ROUTINE.md`에 규칙을 보완한다.

- [ ] **Step 4: 리허설 결과물 지우기**

```bash
rm -rf data/raw data/briefs docs/2* docs/index.html docs/archive.html docs/style.css
git checkout -- data/seen.json curriculum.yaml
git status --short
```
Expected: 생성물이 사라지고 `.claude/launch.json`과 Step 2~3에서 고친 파일만 변경으로 남는다.

- [ ] **Step 5: 커밋**

```bash
git add .claude/launch.json templates ROUTINE.md
git commit -m "chore: add local preview config and refine after rehearsal" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: GitHub 공개 저장소와 Pages

**Files:** 없음 (원격 설정)

- [ ] **Step 1: 사용자 확인**

공개 저장소 생성은 외부에 공개되는 작업이므로 사용자에게 "`htdufhc-bit/daily-tech-brief`를 공개 저장소로 만들고 푸시할까요?"라고 묻고 승인받은 뒤 진행한다.

- [ ] **Step 2: 저장소 만들고 푸시**

Run:
```bash
gh repo create htdufhc-bit/daily-tech-brief --public --source . --remote origin --push --description "매일 아침 IT 뉴스와 오늘의 기술"
```
Expected: 저장소 주소가 출력되고 `main`이 푸시된다.

- [ ] **Step 3: Pages 켜기 (`main` 브랜치 `/docs`)**

Run:
```bash
gh api -X POST repos/htdufhc-bit/daily-tech-brief/pages -f "source[branch]=main" -f "source[path]=/docs"
gh api repos/htdufhc-bit/daily-tech-brief/pages --jq '.html_url'
```
Expected: `https://htdufhc-bit.github.io/daily-tech-brief/` (첫 브리핑 전이라 이 주소는 아직 404가 정상)

---

### Task 10: 클라우드 루틴 만들기와 첫 실행 확인

**Files:** 없음 (루틴 설정)

- [ ] **Step 1: 클라우드가 저장소에 접근할 수 있게 하기**

사용자에게 안내한다: claude.ai/code에서 GitHub 연결(Claude GitHub App을 `daily-tech-brief` 저장소에 설치)을 하거나, 터미널 `claude`에서 `/web-setup`을 실행한다. 사용자가 완료했다고 할 때까지 기다린다.

- [ ] **Step 2: 허용할 도메인 목록 뽑기**

Run:
```bash
.venv/Scripts/python -c "
import yaml
from urllib.parse import urlsplit
sources = yaml.safe_load(open('collector/sources.yaml', encoding='utf-8'))['sources']
print('\n'.join(sorted({urlsplit(s['url']).hostname for s in sources})))
"
```
Expected: 한 줄에 하나씩 도메인 목록

- [ ] **Step 3: 루틴 만들기**

`schedule` 스킬을 불러 지시에 따라 루틴을 만든다:
- 저장소: `htdufhc-bit/daily-tech-brief`
- 일정: 매일 07:07, 한국 시간 (만든 뒤 표시되는 다음 실행 시각이 07:07 KST인지 확인)
- 프롬프트: `저장소의 ROUTINE.md를 읽고 0단계부터 7단계까지 그대로 수행해. 6단계에서는 반드시 main 브랜치에 푸시를 먼저 시도해.`

- [ ] **Step 4: 네트워크 허용 목록 설정 (사용자)**

사용자에게 안내한다: 루틴 편집 → 환경 설정 → Network access를 **Custom**으로 바꾸고 Step 2의 도메인을 한 줄에 하나씩 붙여 넣은 뒤 **"Also include default list of common package managers"**를 체크하고 저장. 기사 원문 확인과 "더 읽을거리" 확인(WebFetch)이 허용 목록에 막히면 **Full**로 바꾸는 것도 선택지로 알려 준다.

- [ ] **Step 5: 지금 실행으로 첫 발행**

루틴을 "Run now"로 실행하고 끝난 뒤 확인한다:
```bash
git fetch origin && git log origin/main --oneline -3
gh api repos/htdufhc-bit/daily-tech-brief/pages/builds/latest --jq '.status'
```
Expected: 맨 위 커밋이 `brief: <오늘>`, Pages 빌드 상태 `built`. 브라우저로 `https://htdufhc-bit.github.io/daily-tech-brief/`를 열어 오늘 브리핑이 보이는지 확인한다.

- [ ] **Step 6: 실패 시 판단 지점**

- 수집 실패가 `HTTP 403`/`host_not_allowed`: Step 4의 허용 목록을 다시 확인하고 다시 실행.
- `main` 푸시 거부로 `claude/brief-<오늘>` 브랜치에 올라감: 사용자에게 알리고 선택지를 제시한다 — (a) 저장소 브랜치 보호·루틴 설정을 바꿔 `main` 푸시 허용, (b) 루틴이 PR을 만들고 병합하도록 `ROUTINE.md` 6단계 수정.
- 그 밖의 오류: 루틴 실행 기록을 읽고 원인을 보고한다.

- [ ] **Step 7: 로컬 저장소 맞추기**

```bash
git pull --ff-only origin main
```
다음 날 07:07 이후 자동 실행으로 새 브리핑이 올라왔는지 한 번 더 확인한다.
