# add-domain 절차

## 1. 도메인 이름 정하기

영문 kebab-case. 다른 도메인 이름의 접두사가 되어도 된다 — `ai`와 `ai-safety`는
공존한다. 어느 검사도 도메인을 접두사로 매칭하지 않는다. `lint.check_layout`은
디렉토리 이름에서 허용 파일명 집합(`<도메인>-purpose|index|overview.md`)을
만들어 문자 그대로 대조하고, `check_status.check_index_projection`은
`wiki/domains/<도메인>/<도메인>-index.md` 경로를 그대로 조립한다. `ai-index.md`와
`ai-safety-index.md`는 서로 다른 stem이다.

실제로 걸리는 제약은 하나다. **파일명은 vault 전역에서 유일해야 한다**
(`lint.check_unique_names`, `conventions.md` §4). 도메인 이름이 구조 파일 stem에
그대로 들어가므로, 도메인 이름이 같으면 구조 파일 3종이 통째로 충돌한다. 비교는
NFC 정규화 후 이뤄진다.

## 2. 디렉토리 생성

- `wiki/domains/<도메인>/` 아래 5개 콘텐츠 디렉토리: `sources/`, `concepts/`,
  `entities/`, `queries/`, `synthesis/`
- `raw/<도메인>/`

## 3. 구조 파일 3종 생성

템플릿에서 아래 3개를 만든다.

- `wiki/templates/domain-purpose.md` → `wiki/domains/<도메인>/<도메인>-purpose.md`
- `wiki/templates/domain-index.md` → `wiki/domains/<도메인>/<도메인>-index.md`
- `wiki/templates/domain-overview.md` → `wiki/domains/<도메인>/<도메인>-overview.md`

`<도메인>-purpose.md`의 **목표·핵심 질문·범위는 사용자에게 물어서 채운다.
비워 두지 않는다.** 템플릿만 복사하고 내용을 채우지 않으면, 이 도메인의
Deep Research 워크플로우가 검색 주제를 생성할 근거를 잃는다 — 빈 purpose는
"무엇을 찾아야 하는지" 자체가 정의되지 않은 상태다.

frontmatter 필수 필드(`tags`, `updated`)는 세 파일 모두에 채운다. 필드 목록은
`conventions.md` §6.

## 4. routing.json 등록

`wiki/routing.json`의 `domains`에 새 항목을 추가한다. 세 키
(`paths`·`required`·`reference`)를 모두 채운다.

```json
"<도메인>": {
  "paths": ["wiki/domains/<도메인>/**", "raw/<도메인>/**"],
  "required": ["wiki/domains/<도메인>/<도메인>-purpose.md",
               "wiki/domains/<도메인>/<도메인>-index.md"],
  "reference": ["wiki/domains/<도메인>/<도메인>-overview.md"]
}
```

## 5. 허브 갱신

`wiki/index.md`의 도메인 표에 새 도메인 한 줄을 추가한다.

## 6. 검증

```bash
python3 wiki/script/route.py --intent query --domain <새 도메인>
python3 wiki/script/lint.py
```

`route.py`가 종료 코드 0으로 끝나야 새 도메인이 `routing.json`에서 실제로
조회 가능하다는 뜻이다(4번 등록이 유효한 경로를 가리키는지까지 확인된다).
`lint.py`는 위반 0건을 확인한다 — 구조 파일 3종의 frontmatter 누락이 이
시점에서 가장 흔한 위반이다.

그 다음 그래프를 1회 다시 만든다 — 시점과 명령은 `wiki/CLAUDE.md`의 "작업 후"
절이 정본이다. 새 도메인의 구조 파일 3종은 그래프가 본 적 없는 페이지라, 돌리지
않으면 다음 lint부터 `그래프stale` 하나만 뜨고 나머지 세 그래프 신호는 판정
자체가 생략된다.

## 참고: 이슈 투영은 도메인 단위가 아니다

새 도메인을 만들어도 GitHub 이슈 투영 설정은 도메인마다 따로 필요하지 않다. 미결
항목은 `wiki/synthesis/open-questions.md` 전역 파일 하나에서만 관리되며
(`wiki/conventions.md` §3), 투영은 `wiki/script/sync_issues.py`가 도맡는다.

## 연관

- `wiki/conventions.md` §4(파일명), §5(디렉토리 배치), §6(frontmatter 필수
  필드), §3(미결 항목)
- `wiki/templates/domain-purpose.md`, `domain-index.md`, `domain-overview.md`
- `wiki/routing.json`
- `wiki/references/lint-rules.md`
- `wiki/script/sync_issues.py`
