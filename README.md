# llm-wiki

LLM이 읽고 쓰고 유지보수하는 마크다운 위키의 골격이다. 클론해서 자기 위키를 시작하도록
만들어졌다.

Andrej Karpathy의 [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
패턴을 구현한 것이다. 원문은 `docs/llm-wiki.md`에 그대로 보관돼 있다.

## 무엇이 다른가

원문은 의도적으로 추상적이다. "당신의 에이전트와 함께 구체화하라"고 말한다. 이 저장소는
그 구체화를 한 벌 끝내 둔 것이며, 한 가지를 더 얹었다.

**규약을 문서로만 두지 않고 스크립트로 강제한다.**

LLM에게 "규약을 읽고 따르라"고 시키면 읽었다는 보고는 돌아오지만 지켰는지는 확률적이다.
세션이 길어지고 컨텍스트가 차면 먼저 흐려지는 것이 규약이다. 그래서 두 지점을 결정적으로
만들었다.

- **작업 전** — `wiki/script/route.py`가 의도와 도메인을 받아 이번 작업에 읽어야 할 문서
  목록을 낸다. LLM이 "이건 알 것 같다"고 판단해 건너뛰는 자리를 없앤다.
- **작업 후** — `wiki/script/lint.py`가 결과물을 계약과 대조한다. 위반이 있으면 종료 코드
  1을 반환한다. Claude Code에서는 Stop 훅으로 자동 실행된다.

검사는 문서 품질을 보지 않는다. 기계가 판정할 수 있는 것만 본다 — frontmatter 필수 필드,
디렉토리 배치, 파일명 유일성, 링크 정합, 판본 체인, 고아 페이지, 자격증명 패턴.
모순 감지나 stale 서술 판별은 여전히 사람과 LLM의 몫이다.

## 세 계층

| 계층 | 위치 | 소유자 |
|---|---|---|
| 원본 | `raw/` | 사람. **불변**이다. LLM은 읽기만 하고 지우지 않는다 |
| 위키 | `wiki/domains/` | LLM. 페이지 생성·갱신·상호참조를 전부 맡는다 |
| 스키마 | `wiki/CLAUDE.md`, `wiki/conventions.md` | 둘이 함께 키운다 |

`wiki/CLAUDE.md`는 **절차**를 정의한다 — 작업 전에 무엇을 하고, 언제 멈추고, 끝나면 무엇을
확인하는지. `wiki/conventions.md`는 **데이터 계약**을 정의한다 — 어떤 필드가 필수고, 값이
무엇이고, 파일이 어디에 놓이는지. 둘이 어긋나면 `conventions.md`가 옳다.

## 시작하기

### 1. 클론

```
git clone https://github.com/citytexi/llm-wiki.git my-wiki
cd my-wiki
rm -rf .git && git init
```

### 2. 환경 준비

`docs/setup.md`를 따른다. 요약하면 python3 3.11 이상이 전부다 — 스크립트는 표준
라이브러리만 쓴다. 테스트를 돌리려면 pytest, 이슈 동기화를 쓰려면 `gh` CLI가 추가로 필요하다.

### 3. Obsidian으로 열기 (선택)

**저장소 루트**를 vault로 연다. `[[파일명]]` 링크가 루트 기준으로 해석되는 것이
파일명 유일성 규칙(`conventions.md` §4)의 전제다. `wiki/`만 vault로 열면 링크 해석이
달라진다.

Obsidian 없이도 동작한다. 위키는 그냥 마크다운 파일 묶음이다.

### 4. 목적 적기

`wiki/purpose.md`를 자기 것으로 고친다. 이 위키가 무엇을 담고 무엇을 담지 않는지 적는
자리다. LLM이 매 ingest마다 이 문서를 읽고 판단 기준으로 쓴다.

### 5. 첫 도메인 만들기

기본 상태에는 `inbox` 도메인 하나만 있다. 아직 분류가 안 된 소스의 대기열이다. 주제가
정해져 있다면 바로 도메인을 만든다.

에이전트에게 이렇게 시킨다:

> `<이름>` 도메인을 추가해줘

에이전트는 `route.py --intent add-domain`을 돌려 `wiki/references/add-domain.md`를 받고
그 절차대로 디렉토리 5종·구조 파일 3종·`routing.json` 항목·허브 등록까지 처리한다.

### 6. 첫 소스 넣기

원본을 `raw/<도메인>/`에 두고 시킨다:

> `raw/<도메인>/<파일>` ingest 해줘

에이전트가 원본을 읽고 요약 페이지를 만들고, 개념·엔티티 페이지를 갱신하고, 카탈로그와
로그에 반영한다. 한 소스가 10~15개 페이지를 건드릴 수 있다.

### 7. 확인

```
python3 wiki/script/lint.py
```

위반 0건이면 종료 코드 0이다. 경고는 판단이 필요하다는 뜻이며 종료 코드에 영향을 주지
않는다.

## 디렉토리

```
raw/                    원본. 불변
  <도메인>/
    research/           Deep Research 산출물만 여기에 추가 가능
wiki/
  CLAUDE.md             운영 진입점 — 라우팅 7단계, 의도 8종, 멈출 조건
  conventions.md        데이터 계약 정본 — 10개 절
  index.md              허브. 도메인 목록만 담는다
  purpose.md            위키 전체 목적
  overview.md           전역 논지
  log.md                append-only 작업 로그
  routing.json          의도·도메인 → 읽을 문서 매핑
  domains/<도메인>/
    <도메인>-purpose.md   도메인 목적
    <도메인>-index.md     도메인 카탈로그
    <도메인>-overview.md  도메인 논지
    sources/            원본 요약. 파일명은 src- 접두사
    concepts/           개념 페이지
    entities/           인물·조직·제품
    queries/            질의 응답 산출물
    synthesis/          도메인 종합
  references/           긴 절차 4종. route.py가 필요할 때 알려준다
  synthesis/            open-questions.md, routing-misses.md
  templates/            페이지 템플릿 9종
  script/               검사·라우팅 스크립트 + 테스트
docs/
  llm-wiki.md           Karpathy 원문
  setup.md              환경 준비
.github/ISSUE_TEMPLATE/ 미결 항목·소스 요청·스크립트 결함 폼
.claude/                Claude Code 훅과 스킬
```

## 스크립트

전부 저장소 루트에서 실행한다. 루트가 아니면 검사 대상이 0건이 되어 위반을 통과로
오인하므로, 스크립트가 종료 코드 2로 막는다.

| 스크립트 | 하는 일 |
|---|---|
| `route.py` | 의도·도메인을 받아 읽을 문서를 낸다. 자연어 분류는 하지 않는다 — 판정은 LLM이 하고 인자로 넘긴다 |
| `lint.py` | 계약 위반 전수 검사. frontmatter·배치·파일명·링크·raw 정합·자격증명 |
| `check_status.py` | 판본 체인(`status`/`superseded_by`) 무결성과 카탈로그 투영 대조 |
| `ingest_cache.py` | `raw/` 원본의 SHA256을 기록해 재처리를 막는다 |
| `sync_issues.py` | 미결 항목을 GitHub 이슈로 단방향 투영. 기본 dry-run |
| `wikilib.py` | 공용 유틸. 페이지 수집·frontmatter 파싱·링크 추출 |

## 처음 고칠 곳

| 파일 | 무엇을 |
|---|---|
| `wiki/purpose.md` | 이 위키의 목적과 범위 |
| `wiki/conventions.md` §9 | 민감 데이터 등급. 기본값은 private 운영 기준이다 |
| `wiki/routing.json` | 도메인을 추가하면 여기에도 등록한다 |
| `LICENSE` | 저작권 표기 |

규약 자체가 안 맞으면 고쳐도 된다. 다만 `conventions.md`를 바꾸면 `lint.py`와 그 테스트도
같이 바꿔야 한다 — 문서와 검사가 갈라지면 강제가 무너진다. 그 작업은 `schema-change`
의도로 라우팅한다.

## 더 읽을 곳

- **패턴의 원리** — `docs/llm-wiki.md`
- **운영 절차** — `wiki/CLAUDE.md`
- **데이터 계약** — `wiki/conventions.md`
- **환경 준비** — `docs/setup.md`

## 라이선스

MIT. `LICENSE` 참조.
