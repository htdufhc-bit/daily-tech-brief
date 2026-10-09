# 매일 브리핑 작업 지침

클라우드 예약 작업에서 Claude가 매일 아침 이 절차를 순서대로 수행한다. 마지막에 7단계 형식으로 짧게 보고한다.
데이터 형식은 `design/2026-10-08-daily-tech-brief-design.md`의 4.4절, 정상 예시는 `tests/factories.py`의 `BRIEF`를 따른다.

## 0. 준비

```bash
python -m pip install -q -r requirements.txt || python -m pip install -q --break-system-packages -r requirements.txt
DAY=$(TZ=Asia/Seoul date +%F)
echo "$DAY"
```

셸 변수는 명령 실행 사이에 유지되지 않으므로, 출력된 날짜(예: 2026-10-09)를 기억해 두고 이후 모든 명령과 파일 경로에서 `$DAY` 대신 그 날짜 문자열을 직접 쓴다 (또는 각 명령 앞에 `DAY=$(TZ=Asia/Seoul date +%F);`를 다시 붙인다).

오늘 브리핑이 이미 발행됐는지 확인한다:

```bash
test -f "docs/$(TZ=Asia/Seoul date +%Y/%m/%d).html" && echo "이미 발행됨"
```

`이미 발행됨`이 출력되면 "오늘 브리핑은 이미 발행됨"이라고 보고하고 끝낸다.

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
- `summary`: 문자열 3개의 JSON 배열. 정확히 3문장이며, 예: `"summary": ["첫 문장", "둘째 문장", "셋째 문장"]`. 기사에 있는 내용만 쓰고, 원문 문장을 옮기지 말고 새로 쓴다. 문장당 80자 안팎.
- `url`: `data/raw`에 있는 `url`을 그대로 쓴다. WebSearch로 보충한 기사는 기사 주소.
- WebSearch로 보충한 기사: `source`는 기사를 낸 매체 이름, `region`은 `kr` 또는 `global`을 명시적으로 쓰고, `url`은 기사 주소(`http://` 또는 `https://`로 시작)여야 한다.
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
- 섹션 안에서 마크다운 제목(`#`, `##` 등)을 쓰지 않는다 (페이지의 제목 구조가 깨진다). 강조가 필요하면 **굵게**를 쓴다.

## 5. 저장과 빌드

저장하기 전에 `tests/factories.py`를 열어 `BRIEF`의 구조를 정확히 따른다.

- 최상위: `date`(오늘 날짜와 같은 `YYYY-MM-DD` 문자열), `headline`, `news`(배열), `tech`(객체), `notes`.
- `notes`는 문자열 배열이다. 해당 없으면 `[]`.
- `tech`: `topic_id`, `title`, `category`, `pick`, `reading_minutes`(정수), `sections`(객체). 4. 기술 글 작성 섹션의 항목(`definition`, `why`, `how`, `example`, `when`, `further_reading`)은 `tech.sections` 안에 들어간다.
- `further_reading`은 `{"title": ..., "url": ...}` 객체의 배열이다.

브리핑을 `data/briefs/$DAY.json`에 UTF-8로 저장한 뒤 (날짜 문자열은 0번 준비 단계에서 확인한 값을 쓴다):

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
