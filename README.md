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
