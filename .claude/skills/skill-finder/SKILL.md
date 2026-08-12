---
name: skill-finder
description: 이 저장소의 스킬을 자연어로 검색해 적재적소 스킬을 찾는다. spec/plan 작성 중이거나 구현 중에 "어떤 스킬 써야 하지", "이 주제 스킬 찾아", "스킬 검색"이 필요할 때 사용. SKILL.md frontmatter를 키워드 가중 랭킹해 상위 후보를 돌려준다.
---

# skill-finder

`.claude/skills/`의 스킬을 쿼리로 랭킹한다(이름 4점 > description 2점 > 제목 1점).
로직은 `script/search.py`.

## 사용
`python3 script/search.py "<자연어 쿼리>" [--top N]`

예: `python3 script/search.py "미결 항목 이슈 동기화" --top 5`

## 언제
- **spec/plan 작성 시**: 다룰 주제를 쿼리해 관련 스킬을 찾은 뒤, 그 스킬을 네이티브
  `Skill`로 호출해 설계·계획에 반영한다.
- 구현 중 특정 문제에 맞는 스킬을 모를 때.

## 참고
- 검색은 후보 랭킹만 — 실제 지침은 해당 스킬을 `Skill`로 호출해 로드한다.
- 검색 대상은 `.claude/skills/` 전체다. 자작 스킬과 벤더 스킬을 가리지 않는다.
- 벤더 스킬을 붙였다면 전체 목차가 `.claude/skills-vendor/CATALOG.md`에 생긴다.
  벤더링 전에는 없는 파일이다.
- 벤더 스킬 갱신은 `update-injected-skills` 스킬이 정본이다.
