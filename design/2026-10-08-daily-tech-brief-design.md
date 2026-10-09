# Daily Tech Brief 설계

- 작성일: 2026-10-08
- 상태: 승인됨 (구현 계획 작성 전)

## 1. 목표

매일 아침 웹 페이지 하나로 다음 두 가지를 읽는다.

1. **IT 뉴스**: 국내 4~5건 + 해외 4~5건, 기사마다 한국어 3줄 요약과 원문 링크
2. **오늘의 기술**: 하루 1개 주제, 입문~중급 난이도, 5~10분 분량의 설명 글

PC가 꺼져 있어도 매일 자동으로 발행되어야 하고, PC와 폰 어디서나 같은 주소로 읽을 수 있어야 한다. API 키나 추가 결제 없이 Claude 구독 사용량만으로 동작해야 한다.

### 범위 밖 (YAGNI)

- 로그인, 댓글, 검색, 푸시 알림
- 기사 본문 전체 저장이나 번역 (요약 + 링크만)
- 비공개 저장소 (무료 GitHub Pages는 공개 저장소 필요)

## 2. 실행 환경

| 항목 | 선택 |
|---|---|
| 저장소 | GitHub 공개 저장소 `htdufhc-bit/daily-tech-brief` |
| 로컬 경로 | `C:\Jun_\daily-tech-brief` |
| 자동 실행 | Claude Code 클라우드 예약 작업(routine), 매일 07:07 KST |
| 웹 공개 | GitHub Pages, `main` 브랜치의 `docs/` 폴더 |
| 언어 | Python 3 (로컬 3.14, 클라우드는 Ubuntu 기본 Python 3) |
| 외부 패키지 | `feedparser`, `PyYAML`, `Jinja2`, `markdown`, 테스트용 `pytest` |

### 클라우드 루틴 제약 (공식 문서 기준, 2026-10-08 확인)

- 네트워크 기본값은 Trusted(패키지 저장소, GitHub 등만 허용). RSS 도메인은 환경 설정의 **Custom 허용 목록**에 추가해야 한다.
- 기본 푸시 대상은 `claude/` 접두사 브랜치. 프롬프트로 `main` 푸시를 지시하되, 실제 가능 여부는 테스트 실행으로 확인한다.
- 최소 실행 간격 1시간. 정각은 지연될 수 있어 07:07로 잡는다.
- 루틴은 매 실행마다 저장소를 새로 clone하므로 상태(이미 소개한 기사, 커리큘럼 진행)는 모두 저장소 안 파일로 관리한다.

## 3. 구조

```
daily-tech-brief/
├─ collector/
│   ├─ sources.yaml        # RSS 소스 목록 (region: kr | global)
│   └─ collect.py          # RSS 수집 → data/raw/YYYY-MM-DD.json
├─ curriculum.yaml         # 오늘의 기술 주제 목록 + 다룬 날짜
├─ data/
│   ├─ raw/                # 날짜별 수집 원본
│   ├─ briefs/             # 날짜별 브리핑 JSON (Claude 작성)
│   └─ seen.json           # 이미 소개한 기사 URL 목록
├─ templates/
│   ├─ brief.html          # 하루치 페이지 템플릿
│   └─ archive.html        # 목록 페이지 템플릿
├─ build.py                # 브리핑 JSON 검사 → HTML 생성, 상태 파일 갱신
├─ tests/                  # pytest
├─ docs/                   # GitHub Pages 공개 폴더 (생성물만)
│   ├─ index.html          # 가장 최근 브리핑 (그날 페이지와 같은 내용)
│   ├─ archive.html        # 날짜 목록 + 다룬 기술 주제 모음
│   ├─ style.css
│   └─ YYYY/MM/DD.html
├─ design/                 # 설계 문서
├─ ROUTINE.md              # 클라우드 Claude의 매일 작업 지침
└─ requirements.txt
```

### 역할 분리

- **Python이 하는 일 (결정적)**: RSS 수집, 중복 제거, JSON 형식 검사, HTML 렌더링, `seen.json`·`curriculum.yaml` 갱신
- **Claude가 하는 일 (판단)**: 기사 선별, 한국어 요약, 오늘의 기술 선정과 글 작성, 브리핑 JSON 작성
- Claude는 HTML을 직접 쓰지 않는다. 브리핑 JSON만 쓰고 렌더링은 `build.py`가 한다.

## 4. 구성 요소

### 4.1 `collector/sources.yaml`

소스마다 `name`, `url`(RSS/Atom 주소), `region`(`kr`/`global`)을 가진다. 초기 후보:

- 국내: GeekNews, 요즘IT, 카카오 기술블로그, 우아한형제들 기술블로그, 토스 기술블로그, 네이버 D2
- 해외: Hacker News(hnrss), TechCrunch, The Verge, Ars Technica, GitHub Blog

정확한 피드 주소는 구현 중 실제 접속으로 확인하고, 응답하지 않는 소스는 목록에서 뺀다.

### 4.2 `collector/collect.py`

- 입력: `sources.yaml`, `data/seen.json`, 날짜(기본값 오늘 KST)
- 동작: 소스별로 피드를 받아 최근 48시간 기사만 남기고(발행일이 없는 기사는 포함), URL을 정규화(쿼리의 `utm_*` 제거, 끝 `/` 제거)한 뒤 `seen.json`에 있는 URL은 제외한다.
- 출력: `data/raw/YYYY-MM-DD.json`

```json
{
  "date": "2026-10-08",
  "items": [
    {"source": "GeekNews", "region": "kr", "title": "...", "url": "...",
     "published": "2026-10-08T06:12:00+09:00", "summary": "피드에 있는 설명(최대 500자)"}
  ],
  "errors": [{"source": "TechCrunch", "error": "HTTP 403"}]
}
```

- 소스 하나가 실패해도 나머지는 계속 수집하고 실패는 `errors`에 기록한다. 소스당 타임아웃 15초.
- 소스 수집 결과와 상관없이 종료 코드는 0 (수집 결과 판단은 Claude 몫). 단 `sources.yaml`·`seen.json`이 깨졌거나 파일을 쓸 수 없으면 오류로 종료한다.

### 4.3 `curriculum.yaml`

```yaml
topics:
  - id: http-caching
    title: HTTP 캐싱
    category: 웹
    covered_on: null        # 다룬 날짜, build.py가 기록
```

분야: 웹, 데이터베이스, 네트워크, 운영체제, 클라우드/인프라, AI/ML, 보안, 언어/도구. 초기 30개 이상. 목록을 다 돌면 Claude가 새 주제를 추가해 커밋한다. 트렌드 픽으로 다룬 주제는 `curriculum.yaml`에 넣지 않고 브리핑 JSON에만 남는다.

### 4.4 브리핑 JSON (`data/briefs/YYYY-MM-DD.json`)

```json
{
  "date": "2026-10-08",
  "headline": "오늘 가장 중요한 이슈 한 문장",
  "news": [
    {"region": "kr", "source": "GeekNews", "title": "한국어 제목",
     "original_title": null,
     "url": "https://...", "summary": ["요약 1", "요약 2", "요약 3"]}
  ],
  "tech": {
    "topic_id": "http-caching",
    "title": "HTTP 캐싱",
    "category": "웹",
    "pick": "curriculum",
    "reading_minutes": 7,
    "sections": {
      "definition": "한 줄 정의",
      "why": "마크다운",
      "how": "마크다운",
      "example": "마크다운 (코드 블록 포함)",
      "when": "마크다운",
      "further_reading": [{"title": "...", "url": "https://..."}]
    }
  },
  "notes": ["일부 소스 수집 실패: TechCrunch"]
}
```

검사 규칙 (`build.py`):

- `date`는 파일명 날짜와 같아야 함
- `news`는 0~12건, 각 `url`은 `http://` 또는 `https://`로 시작, `summary`는 비어 있지 않은 문장 정확히 3개
- `region`은 `kr`/`global`, 해외(`global`) 기사는 `original_title` 필수(비어 있지 않은 문자열)
- `tech`는 필수, `pick`은 `trend`/`curriculum`, `curriculum`이면 `topic_id`가 `curriculum.yaml`에 있어야 함
- `reading_minutes`는 1~30 정수, `sections`의 6개 항목 모두 필수, `further_reading`은 1~3건
- 검사 실패 시 무엇이 틀렸는지 경로와 함께 모두 출력하고 종료 코드 1

### 4.5 `build.py`

- 사용법: `python build.py YYYY-MM-DD [--force]`
- 순서: 브리핑 JSON 검사 → `docs/YYYY/MM/DD.html` 생성 → `docs/index.html` 갱신 → `docs/archive.html` 재생성 → `seen.json`에 뉴스 URL 추가 → `pick`이 `curriculum`이면 `curriculum.yaml`의 `covered_on` 기록
- 이미 `docs/YYYY/MM/DD.html`이 있으면 아무것도 하지 않고 종료 코드 0 (`--force`면 덮어쓰기)
- `archive.html`과 이전/다음 링크는 `data/briefs/`의 모든 브리핑 JSON에서 만든다. 새 페이지가 생기면 바로 전날 페이지의 "다음" 링크도 갱신한다.
- 마크다운 섹션은 `markdown` 패키지로 HTML 변환하되, 원본에 들어 있는 HTML 태그는 이스케이프한다. 일반 문자열 필드는 Jinja2 자동 이스케이프를 쓴다.

### 4.6 `ROUTINE.md`

클라우드 Claude가 매일 따르는 절차. 루틴 프롬프트는 "ROUTINE.md를 읽고 그대로 수행하라" 한 줄로 둔다.

1. `pip install -r requirements.txt`
2. `python collector/collect.py`
3. `data/raw/오늘.json`을 읽고 국내·해외 각각 중요도 순 4~5건 선별. 피드 설명만으로 부족하면 WebFetch로 원문 확인. 한쪽이 0건이면 WebSearch로 보충하고 `notes`에 기록
4. 오늘의 기술 선정: 뉴스에 반복 등장하거나 큰 발표가 있는 기술이면 `trend`, 아니면 `curriculum.yaml`에서 `covered_on`이 비어 있는 첫 주제. 커리큘럼이 바닥나면 새 주제 10개를 추가
5. `data/briefs/오늘.json` 작성 → `python build.py 오늘` 실행. 실패하면 오류를 읽고 고쳐 최대 2회 재시도
6. `git add` → 커밋 메시지 `brief: YYYY-MM-DD` → `main`에 푸시. 실패하면 `claude/brief-YYYY-MM-DD`로 푸시

작성 규칙: 요약은 기사 내용에 근거한 것만, 원문 문장 복사 금지, 모든 기사에 원문 링크.

## 5. 페이지 구성

### 하루치 페이지

1. 헤더: 제목, 날짜(요일), 이전/목록/다음 링크, 다크모드 전환 버튼
2. 오늘의 한 줄 (`headline`)
3. IT 뉴스: [국내], [해외] 순서. 제목(링크) + 출처 + 요약 3줄, 해외는 원제목을 작게 표시. 한쪽이 0건이면 그 소제목은 숨김
4. 오늘의 기술: 제목, `트렌드 픽`/`커리큘럼 #N` 배지, 읽는 시간, 6개 섹션
5. `notes`가 있으면 하단에 작게 표시

### 목록 페이지

- 날짜 역순: `10.08 — HTTP 캐싱 · 뉴스 9건`
- 다룬 기술 주제를 분야(`category`)별로 모아 보기

### 디자인 원칙

- 한 칸짜리 세로 레이아웃, 본문 최대 폭 720px, 폰 기준 좌우 여백 16px
- 시스템 다크모드 자동 적용 + 버튼으로 전환 (선택은 localStorage에 저장, 실패해도 동작)
- 외부 스크립트 없음. CSS는 `docs/style.css` 하나

## 6. 오류 처리

| 상황 | 처리 |
|---|---|
| RSS 소스 일부 실패 | 나머지 계속 수집, `errors` 기록, 페이지 `notes`에 표시 |
| 국내 또는 해외 전부 실패 | Claude가 WebSearch로 보충 |
| 전체 0건 | 뉴스 없이 오늘의 기술만 발행 |
| 브리핑 JSON 검사 실패 | 오류 메시지 보고 수정, 최대 2회 재시도 |
| 같은 날짜 재실행 | 기존 페이지 유지, 아무것도 안 함 |
| `main` 푸시 실패 | `claude/brief-YYYY-MM-DD` 브랜치로 푸시 |
| 루틴 자체 실패 | Claude 앱의 루틴 실행 기록에서 확인 |

## 7. 테스트

### 자동 테스트 (pytest, 네트워크 없음)

- `collect.py`: 샘플 RSS/Atom 파일 파싱, 48시간 필터, URL 정규화, `seen.json` 제외, 실패 소스 기록
- `build.py`: 정상 JSON → HTML 생성, 검사 실패 케이스별 오류, `index.html`·`archive.html` 갱신, 이전/다음 링크, 같은 날짜 건너뛰기, `seen.json`·`curriculum.yaml` 갱신, HTML 이스케이프

### 실제 동작 확인

1. 로컬에서 실제 RSS 수집 → 브리핑 1건 작성 → HTML 생성 → 브라우저에서 PC/폰 폭, 다크모드 확인
2. GitHub 공개 저장소 생성, 푸시, Pages(`main`/`docs`) 활성화 후 주소 접속 확인
3. 클라우드 루틴 생성 → 네트워크 허용 목록에 RSS 도메인 추가 → "지금 실행"으로 수집, `main` 푸시, Pages 반영 확인

### 사용자가 직접 해야 할 수 있는 일

- 루틴 환경의 네트워크 설정을 Custom으로 바꾸고 RSS 도메인 추가
