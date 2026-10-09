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


def test_build_failure_before_target_page_allows_clean_rerun(site):
    # 상태 파일(seen.json) 처리에 실패하면 날짜 페이지가 만들어지지 않아야 한다.
    # 그래야 다시 실행했을 때 "skipped"로 넘어가지 않고 상태까지 갱신된다.
    write_brief(site, make_brief())
    seen_path = site / "data/seen.json"
    seen_path.write_text("{", encoding="utf-8")

    with pytest.raises(Exception):
        build.build("2026-10-08", site)
    assert not (site / "docs/2026/10/08.html").exists()

    seen_path.write_text("[]", encoding="utf-8")
    assert build.build("2026-10-08", site) == "built"
    assert (site / "docs/2026/10/08.html").exists()
    assert "https://example.com/story" in json.loads(read(seen_path))
    topics = yaml.safe_load(read(site / "curriculum.yaml"))["topics"]
    assert topics[0]["covered_on"] == "2026-10-08"
