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

    # 1) 쓰기 전에 모든 결과를 메모리에서 먼저 계산한다. 여기서 실패하면 디스크는 그대로다.
    position = days.index(day)
    previous_page = None
    if position > 0:  # 전날 페이지의 '다음' 링크를 새 페이지로 이어 준다
        previous = days[position - 1]
        previous_page = (docs / page_path(previous), render_day(previous, DAY_BASE))
    day_html = render_day(day, DAY_BASE)
    index_html = render_day(days[-1], "")
    archive_html = render_archive([briefs[d] for d in days])
    seen_path = root / "data" / "seen.json"
    seen_text = _seen_text(seen_path, [item["url"] for item in brief["news"]])
    curriculum_path = root / "curriculum.yaml"
    curriculum_text = (
        _covered_text(curriculum_path, brief["tech"]["topic_id"], day)
        if brief["tech"]["pick"] == "curriculum"
        else None
    )

    # 2) 상태 파일 -> 보조 페이지 -> 날짜 페이지 순으로 쓴다.
    #    날짜 페이지가 "발행됨" 표시이므로 반드시 마지막에 쓴다. 그 앞의 쓰기는 모두
    #    다시 실행해도 같은 결과가 나오므로, 중간에 실패해도 재실행으로 복구된다.
    _write(seen_path, seen_text)
    if curriculum_text is not None:
        _write(curriculum_path, curriculum_text)
    if previous_page:
        _write(*previous_page)
    _write(docs / "index.html", index_html)
    _write(docs / "archive.html", archive_html)
    shutil.copyfile(TEMPLATES / "style.css", docs / "style.css")
    (docs / ".nojekyll").touch()
    _write(target, day_html)
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


def _seen_text(path: Path, urls: list[str]) -> str:
    seen = set(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else set()
    seen.update(normalize_url(url) for url in urls)
    return json.dumps(sorted(seen), ensure_ascii=False, indent=2) + "\n"


def _covered_text(path: Path, topic_id: str, day: str) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for topic in data["topics"]:
        if topic["id"] == topic_id and not topic.get("covered_on"):
            topic["covered_on"] = day
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def main(argv: list[str] | None = None) -> int:
    # 한국어 Windows 콘솔(cp949)에서 표현할 수 없는 문자가 있어도 출력 때문에 실패하지 않도록
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="replace")
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
