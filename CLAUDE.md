<!--
도구 설치기가 이 파일 끝에 자기 절을 덧붙일 수 있다(지식 그래프 도구 등).
덮어쓰지 말고 아래 위임 규칙을 유지한 채 병합한다. 위임이 우선한다.
AGENTS.md는 이 파일을 가리키는 심볼릭 링크다 — 여기만 고치면 둘 다 바뀐다.
-->

# 저장소 안내

이 저장소는 LLM이 운영하는 멀티 도메인 마크다운 위키다.

위키 관련 작업을 시작하기 전에 `wiki/CLAUDE.md`를 먼저 읽는다.

라우터 실행:

    python3 wiki/script/route.py --intent <의도> [--domain <도메인>] [--seed <저장소상대경로> ...] [--json]

규칙은 여기 없다 — `wiki/CLAUDE.md`와 `wiki/conventions.md`가 정본이다. 아래 절도
규칙이 아니라 도구 사용 메모이며, 이 위임에 종속된다.

## 스킬 벤더링 사용 메모

`.claude/skills-vendor/`가 외부 repo에서 가져올 스킬의 목록·출처·기준 SHA를 들고
있다. 기본 `sources.json`은 비어 있다 — 벤더링을 쓰지 않으면 이 절은 해당 없다.

- 설계·계획을 확정하기 전에 다룰 주제를 `python3 script/search.py "<주제>"`로 먼저
  검색한다. 상위 후보 중 관련 있는 것을 네이티브 `Skill`로 로드한 뒤 설계를
  마무리한다. 검색은 후보 랭킹일 뿐이라 로드하지 않으면 지침을 읽은 것이 아니다.
- 벤더 스킬을 붙였다면 전체 목차가 `.claude/skills-vendor/CATALOG.md`에 생긴다.
  넓게 훑어야 할 때만 읽는다.
- 벤더 스킬을 upstream과 맞추는 절차는 `update-injected-skills` 스킬이 정본이다.
- `.claude/skills/` 아래 벤더 산출물은 편집하지 않는다. 갱신이 재복사라 수정이
  소리 없이 사라진다.
