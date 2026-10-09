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
