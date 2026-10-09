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
