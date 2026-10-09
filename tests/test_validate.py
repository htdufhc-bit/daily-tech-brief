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
