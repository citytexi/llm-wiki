# 환경 준비

클론한 저장소를 실제로 굴리기 위해 필요한 것들. 전부 선택은 아니지만, 필수는 python3
하나뿐이다.

## 1. python3 (필수)

검사·라우팅 스크립트 6종이 python3로 돌아간다. **런타임 의존성은 0이다** — 표준
라이브러리만 쓴다. `pip install`이 필요한 것은 테스트뿐이다.

```
python3 --version
python3 wiki/script/lint.py
```

`lint.py`가 종료 코드 0을 내면 준비 끝이다.

python 3.9.6에서 동작을 확인했다. 그보다 낮은 버전은 확인하지 않았다. 3.11 이상을
권한다.

**반드시 저장소 루트에서 실행한다.** 루트가 아니면 수집 대상이 0건이 되어 "위반 0건"이
거짓으로 나온다. 그래서 스크립트가 `wiki/`와 `wiki/conventions.md`가 안 보이면 검사하지
않고 종료 코드 2로 막는다.

## 2. pytest (테스트를 돌릴 때)

스크립트를 고칠 계획이 있으면 필요하다. 그대로 쓰기만 할 거면 건너뛴다.

```
pip install pytest
python3 -m pytest wiki/script/tests -q
```

테스트는 `tmp_path`에 가짜 저장소를 만들어 돈다. 실제 저장소나 네트워크를 건드리지
않는다 (`wiki/script/tests/conftest.py`의 `make_repo` 픽스처).

`conventions.md`를 고쳤다면 `lint.py`와 이 테스트도 같이 고쳐야 한다. 문서와 검사가
갈라지면 강제가 무너진다.

## 3. Obsidian (선택, 권장)

위키를 읽는 쪽 도구다. 없어도 동작한다.

**저장소 루트를 vault로 연다.** `wiki/`나 하위 디렉토리를 열지 않는다.

이유는 `[[파일명]]` 링크 때문이다. Obsidian은 경로 없는 위키링크를 vault 전역의 파일명
인덱스로 해석한다. vault 범위가 달라지면 같은 링크가 다른 파일로 해석되거나 끊긴다.
`conventions.md` §4의 "파일명은 vault 전역에서 유일하다" 규칙과 `lint.py`의 유일성 검사가
모두 루트 vault를 전제한다.

`.gitignore`가 `/wiki/.obsidian/`과 `/raw/.obsidian/`을 막아 둔 것도 같은 이유다 — 실수로
하위 디렉토리를 vault로 열어도 그 설정이 커밋되지 않는다.

설정은 `.obsidian/`에 이미 들어 있다.

- `app.json` — 첨부 경로 `raw/assets`, 링크 형식 `shortest`, 마크다운 링크 끄기
- `core-plugins.json` — file-explorer, global-search, switcher, graph, backlink,
  outgoing-link, tag-pane, page-preview, templates

`workspace.json`과 `graph.json`은 로컬 상태라 무시된다.

### 이미지 함께 받기

Settings → Hotkeys에서 "Download attachments for current file"에 단축키를 지정한다.
웹 클리핑 후 그 키를 누르면 이미지가 `raw/assets`로 내려온다. URL이 깨져도 LLM이 이미지를
직접 볼 수 있다.

## 4. gh CLI (이슈 동기화를 쓸 때)

`wiki/script/sync_issues.py`만 필요로 한다. 미결 항목을 GitHub 이슈로 투영하는 기능이며,
안 쓰면 이 절을 통째로 건너뛴다.

```
brew install gh          # macOS
gh auth login
gh label create wiki-sync --description "open-questions.md에서 투영된 이슈"
gh label create open-question --description "미해결 항목"
```

대상 저장소는 git remote에서 `gh`가 추론한다. 저장소 이름을 어디에도 적지 않는다.

동작 방식:

- 정본은 `wiki/synthesis/open-questions.md`다. 이슈는 그 파일의 투영이다
- 사람이 이슈 본문을 고쳐도 다음 실행에서 덮인다. 코멘트는 건드리지 않는다
- 해소는 이슈가 아니라 파일에 기록한다
- 기본이 dry-run이다. 실제 반영은 `--apply`

```
python3 wiki/script/sync_issues.py           # 차이만 보고
python3 wiki/script/sync_issues.py --apply   # 반영
```

## 5. 에이전트 설정

### Claude Code

`.claude/settings.json`에 훅 둘이 들어 있다.

- **SessionStart** — 세션이 시작될 때 "이 저장소는 LLM이 운영하는 멀티 도메인 위키다"라는
  안내를 낸다. 컨텍스트에 규약의 존재를 먼저 심는다
- **Stop** — 응답이 끝날 때 `lint.py`를 돌린다. `|| true`가 붙어 있어 위반이 있어도 세션을
  막지는 않지만, 위반 목록이 눈에 들어온다

`.claude/skills/wiki-issue-sync/` 스킬은 미결 항목을 고친 직후 이슈 동기화를 시키는
절차다.

훅이 싫으면 `.claude/settings.json`을 지운다. 규약 강제는 `wiki/CLAUDE.md`와 스크립트가
하는 것이고 훅은 편의 장치다.

### Codex / 그 외

`AGENTS.md`가 루트에 있다. 내용은 `CLAUDE.md`와 같다 — 둘 다 `wiki/CLAUDE.md`를 먼저
읽으라고 넘기는 얇은 브리지다.

다른 에이전트를 쓴다면 그 런타임이 읽는 파일 이름으로 같은 내용을 하나 더 두면 된다.
`conventions.md` §4가 이 진입 파일들끼리는 stem이 겹쳐도 되도록 예외를 두고 있다.

## 6. 공개 범위 정하기

`wiki/conventions.md` §9의 민감 데이터 등급표는 **private 운영을 기준으로** 매겨져 있다.

| 패턴 | private 기준 |
|---|---|
| API 키·secret·password·token·JWT·private key | 위반 (커밋 차단) |
| 이메일·전화번호·주민등록번호 | 경고 |
| 로컬 절대경로 | 경고 |

public으로 운영한다면 아래 두 줄을 위반으로 올린다. 문서(§9 표)와 `lint.py`를 **둘 다**
고쳐야 한다. 문서만 고치면 강제되지 않는다.

자격증명은 공개 범위와 무관하게 위반이다.

검사 범위는 `wiki/`와 `raw/` 둘 다이다. `raw/`는 손대지 않은 제3자 원본이 쌓이는
곳이라 붙여넣은 자격증명이 가장 먼저 닿는 자리다.

## 7. 첫 실행 점검

```
python3 wiki/script/lint.py            # 종료 코드 0
python3 wiki/script/check_status.py    # 종료 코드 0
python3 wiki/script/route.py --intent ingest --domain inbox --json
```

셋 다 0이면 골격이 온전하다. `route.py`가 낸 `required` 목록이 에이전트가 ingest 전에
읽어야 할 문서다.
