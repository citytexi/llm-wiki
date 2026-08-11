<!--
3단계에서 `graphify install --project`가 이 파일에 자기 절을 쓴다(스펙 §5.4).
덮어쓰지 말고 아래 위임 규칙을 유지한 채 병합한다. 위임이 우선한다.
-->

# 저장소 안내 (Claude Code)

이 저장소는 LLM이 운영하는 멀티 도메인 마크다운 위키다.

위키 관련 작업을 시작하기 전에 `wiki/CLAUDE.md`를 먼저 읽는다.

라우터 실행:

    python3 wiki/script/route.py --intent <의도> [--domain <도메인>] [--seed <저장소상대경로> ...] [--json]

규칙은 여기 없다 — `wiki/CLAUDE.md`와 `wiki/conventions.md`가 정본이다.
