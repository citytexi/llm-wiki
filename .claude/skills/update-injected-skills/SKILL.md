---
name: update-injected-skills
description: 외부 repo에서 벤더링한 스킬을 upstream과 동기화한다. 사용자가 "스킬 업데이트", "벤더 스킬 갱신", "update-injected-skills", "스킬 최신화"라고 할 때 사용. baseline.json의 마지막 SHA 대비 delta(추가·수정·삭제)만 재벤더한다.
---

# update-injected-skills

`.claude/skills-vendor/sources.json`의 소스 repo를 baseline SHA 대비 diff로
업데이트한다. 로직은 `script/vendor.py`.

기본 `sources.json`은 **비어 있다.** 벤더링할 repo를 먼저 등록해야 할 일이 생긴다.

## 절차
1. **dry-run 먼저**: `python3 script/vendor.py --update --dry-run`
   - 출력 `+추가 ~수정 -삭제`와 스킬 목록을 확인한다.
2. delta가 있으면 실제 적용: `python3 script/vendor.py --update`
3. 변경 요약을 사용자에게 보고한다(추가/수정/삭제 스킬명 + baseline SHA 갱신분).
4. `.claude/skills/`와 `.claude/skills-vendor/{baseline,manifest,MANIFEST,CATALOG}`
   변경을 **사용자 확인 후** 커밋한다.

## 주의
- baseline 정본은 `.claude/skills-vendor/baseline.json`. `baseline.md`는 렌더 산출물이다.
  둘 다 첫 벤더링 전에는 없다 — 없으면 빈 상태로 읽으므로 `--update`가 죽지 않고,
  등록한 repo 전부가 add로 분류된다.
- 전량 재설치가 필요하면 `--full`(초기 설치 전용).
- 벤더 스킬 원본은 편집 금지 — 재복사로 덮인다.
- 소스 repo **추가**는 `sources.json`에 넣고 `--update`를 돌린다. baseline에 없는 repo는
  전량 add로 분류된다. `--full`을 쓸 이유가 없다.
- 소스 repo **제거**는 `sources.json`에서 뺀 뒤 `--full`을 돌린다. `--update`는 sources에
  없는 repo를 아예 보지 않아 그 스킬이 디스크에 남는다. `--full`은 이전 manifest의 leaf를
  먼저 지우고 시작하므로 빠진 repo의 산출물까지 정리된다.
- `--full`이 도중에 죽었으면 **`--full`로 다시 돌린다.** `--update`로는 복구되지 않는다.
  중단 시점에 복사되지 못한 스킬이 manifest에는 남아 있는데, `--update`는 baseline SHA가
  같으면 그 repo를 건너뛰고 SHA가 올라도 그 스킬의 diff가 비어 있어 재복사하지 않는다.
  증상은 `MANIFEST.md`에 있는 스킬이 `.claude/skills/`에 없거나 `CATALOG.md`의 설명이
  빈칸인 것이다. `--full`은 manifest의 leaf를 지우고 처음부터 복사하므로 정리된다.
- 벤더링은 남의 코드를 이 저장소에 복사해 넣는 것이다. 소스 repo의 라이선스가 재배포를
  허용하는지 확인하고, `--full`·`--update`가 `.claude/skills-vendor/licenses/`에 받아
  두는 라이선스 파일을 지우지 않는다.
