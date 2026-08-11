---
name: wiki-issue-sync
description: Use when open-questions.md 항목을 추가·해소한 직후, 세션을 마무리할 때, 또는 사용자가 이슈 현행화를 요청할 때 - 미결 항목을 GitHub 이슈로 단방향 투영하고 어긋난 것을 보고한다
---

# 미결 항목 ↔ GitHub 이슈 동기화

`wiki/synthesis/open-questions.md`가 정본이고 이슈는 투영이다. 이슈 본문을 고쳐도
다음 실행에서 덮인다. 해소는 반드시 파일에 기록한다.

## 언제 쓰나

- 미결 항목을 추가하거나 해소한 직후
- 세션을 마무리할 때
- 사용자가 "이슈 현행화"를 요청할 때

## 절차

1. 차이를 계산한다. **저장소 루트에서** 실행한다.

   ```bash
   python3 wiki/script/sync_issues.py
   ```

   종료 코드 `2`면 실행 환경 문제다(루트 아님, `gh` 미인증). 여기서 멈추고 사용자에게 보고한다.

2. 출력을 사용자에게 보고한다. `할 일`·`위반`·`경고`를 그대로 옮기되, 각 항목이 무슨
   뜻인지 한 줄씩 붙인다.

3. 승인을 받고 반영한다.

   ```bash
   python3 wiki/script/sync_issues.py --apply
   ```

4. 파일이 바뀌었으면(`issue` 번호 기입) 커밋한다.

   ```bash
   git add wiki/synthesis/open-questions.md
   git commit -m "chore: 미결 항목 이슈 번호 기입"
   ```

## 보고 유형별 처리

**`[warning/미채택] #N`** — 사람이 템플릿으로 올린 이슈인데 파일에 항목이 없다.

1. `gh issue view N --json title,body` 로 내용을 읽는다.
2. `wiki/conventions.md` §3 형식으로 `open-questions.md`에 항목을 쓴다. `action` 값은
   이슈의 action 필드를 그대로 쓴다(`create-page`·`research`·`skip` 중 하나).
3. 그 항목에 `- **issue**: #N` 을 직접 적는다.
4. 다시 `--apply` 하면 `wiki-sync` 라벨이 붙어 채택된다.

**`[violation/고아이슈] #N`** — `wiki-sync` 이슈인데 참조하는 항목이 없다.
**자동으로 닫지 않는다.** 사용자에게 묻는다: 항목이 해소되어 지워진 것인가, 실수인가.

- 해소였다면 → `gh issue close N` 하고 이유를 코멘트로 남긴다.
- 실수였다면 → 항목을 파일에 되살리고 `- **issue**: #N` 을 적는다.

**`[violation/이슈없음]`** — 항목이 참조하는 번호의 이슈가 조회되지 않았다. 이슈가
삭제되었거나 라벨이 벗겨진 경우다. 사용자에게 확인하고, 이슈가 없으면 항목의
`issue` 줄을 지운 뒤 다시 실행해 새로 만든다.

**`[violation/issue형식]`** — `issue` 값이 `#숫자`가 아니다. 값을 고친다. 어떤 이슈를
가리키는지 모르겠으면 줄을 지워 새로 만들게 한다.

## 하지 않는 것

- 이슈 코멘트를 지우거나 고치지 않는다. 파일에서 재생성할 수 없는 유일한 정보다.
- 고아 이슈를 자동으로 닫지 않는다.
- 파일을 이슈 내용으로 덮지 않는다. 투영은 한 방향뿐이다.
