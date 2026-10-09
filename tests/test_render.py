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
