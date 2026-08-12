# script

이 저장소의 **저장소 툴링 홈**. 스킬(`.claude/skills/*`)이 호출하는 로직을 모은다.

`wiki/script/`와 역할이 다르다. 그쪽은 위키 데이터 툴링(`route.py`·`lint.py`·
`sync_issues.py`)이고 `wiki/CLAUDE.md`·`wiki/conventions.md`가 규약을 소유한다.
여기는 위키 데이터와 무관한 저장소 운영 도구다.

## 규약
- **stdlib 전용** — pip 의존성 0. `python3 script/<name>.py`로 실행.
- **경로**: repo 루트 = `Path(__file__).resolve().parents[1]`(= `script/x.py` → 루트) 기준.
  저장소 위치 이동에 무관하다.
- 각 스크립트 상단에 용법 docstring을 둔다.
- 스킬이 호출하는 스크립트는 SKILL.md에서 `python3 script/<name>.py`로 참조(cwd = repo 루트).
- 테스트는 `script/tests/test_<name>.py`(pytest).

## 인덱스
| 스크립트 | 용도 | 호출 스킬 |
|---|---|---|
| `vendor.py` | `.claude/skills-vendor/sources.json`에 등록한 repo의 스킬 벤더링 + baseline/diff 갱신 | `update-injected-skills` |
| `search.py` | `.claude/skills/` 자연어 검색 랭킹 | `skill-finder` |

`sources.json`의 기본값은 빈 배열이다. 벤더링을 쓰지 않으면 `search.py`가 자작 스킬만
검색하고 `vendor.py`는 할 일이 없다고 보고한다.

## 테스트
    python3 -m pytest script/tests -v

저장소 전체(위키 툴링 포함)는 루트에서 `python3 -m pytest`. 경로 설정은 `pytest.ini`에 있다.
