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
