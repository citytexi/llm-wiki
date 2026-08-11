import pathlib

from conftest import page

import wikilib


def test_split_frontmatter_returns_none_when_absent():
    fm, body = wikilib.split_frontmatter("# 제목\n본문")
    assert fm is None
    assert body == "# 제목\n본문"


def test_split_frontmatter_extracts_block():
    fm, body = wikilib.split_frontmatter("---\ntags: [a]\n---\n\n본문")
    assert fm == "tags: [a]"
    assert body.strip() == "본문"


def test_split_frontmatter_unterminated_is_none():
    fm, _ = wikilib.split_frontmatter("---\ntags: [a]\n본문")
    assert fm is None


def test_parse_fm_reads_scalar_and_list():
    fm = wikilib.parse_fm("tags: [연구, 개인]\nupdated: 2026-08-10\nstatus: current")
    assert fm["tags"] == ["연구", "개인"]
    assert fm["updated"] == "2026-08-10"
    assert fm["status"] == "current"


def test_strip_noise_removes_comments_and_fences():
    t = "앞 <!-- [[숨은링크]] --> 뒤\n```\n[[펜스링크]]\n```\n끝"
    out = wikilib.strip_noise(t)
    assert "숨은링크" not in out
    assert "펜스링크" not in out
    assert "앞" in out and "끝" in out


def test_find_links_handles_alias_and_anchor():
    links = wikilib.find_links("[[개념]] [[개념|별칭]] [[개념#절]]")
    assert links == ["개념", "개념", "개념"]


def test_load_pages_skips_uncollected(make_repo):
    root = make_repo({
        "wiki/index.md": page(body="[[a-index]]"),
        "wiki/CLAUDE.md": "지시문",
        "wiki/conventions.md": "계약",
        "wiki/templates/concept.md": "템플릿",
        "wiki/script/lint.py": "코드",
        "wiki/references/lint-rules.md": "참고",
        "wiki/synthesis/routing-misses.md": "기록",
        "wiki/domains/a/a-index.md": page(),
        "docs/llm-wiki.md": "원리",
    })
    rels = {str(p.path) for p in wikilib.load_pages(root)}
    assert rels == {"wiki/index.md", "wiki/domains/a/a-index.md"}


def test_load_pages_marks_missing_frontmatter(make_repo):
    root = make_repo({"wiki/domains/a/concepts/x.md": "frontmatter 없음"})
    pg = wikilib.load_pages(root)[0]
    assert pg.has_fm is False
    assert pg.fm == {}


def test_all_markdown_covers_raw_and_docs_but_not_dotdirs(make_repo):
    root = make_repo({
        "wiki/index.md": page(),
        "raw/a/원본.md": "원본",
        "docs/llm-wiki.md": "원리",
        ".obsidian/notes.md": "무시",
    })
    rels = {p.relative_to(root).as_posix() for p in wikilib.all_markdown(root)}
    assert rels == {"wiki/index.md", "raw/a/원본.md", "docs/llm-wiki.md"}


def test_build_name_index_groups_duplicates(make_repo):
    root = make_repo({
        "wiki/domains/a/concepts/토핑.md": page(),
        "wiki/domains/b/concepts/토핑.md": page(),
    })
    idx = wikilib.build_name_index(wikilib.load_pages(root))
    assert len(idx["토핑"]) == 2


def test_nfc_normalizes_korean(make_repo):
    decomposed = "가"  # ㄱ + ㅏ
    assert wikilib.nfc(decomposed) == "가"


BLOCK_FM = "tags:\n  - t\nupdated: 2026-08-10\nsources:\n  - src-정책"


def test_parse_fm_reads_block_list():
    fm = wikilib.parse_fm(BLOCK_FM)
    assert fm["tags"] == ["t"]
    assert fm["sources"] == ["src-정책"]
    assert fm["updated"] == "2026-08-10"


def test_parse_fm_block_and_inline_agree():
    block = wikilib.parse_fm("tags:\n  - 연구\n  - 개인")
    inline = wikilib.parse_fm("tags: [연구, 개인]")
    assert block == inline == {"tags": ["연구", "개인"]}


def test_parse_fm_mixed_block_and_inline_keys():
    fm = wikilib.parse_fm(
        "tags:\n  - 연구\nsources: [src-가, src-나]\nstatus: current")
    assert fm == {"tags": ["연구"], "sources": ["src-가", "src-나"],
                  "status": "current"}


def test_parse_fm_empty_value_stays_empty_string():
    fm = wikilib.parse_fm("tags:\nupdated: 2026-08-10")
    assert fm["tags"] == ""
    assert fm["updated"] == "2026-08-10"


def test_parse_fm_block_list_keeps_korean_items():
    fm = wikilib.parse_fm("sources:\n  - src-개인정보보호법\n  - src-정책-v2")
    assert fm["sources"] == ["src-개인정보보호법", "src-정책-v2"]
    assert all(x == wikilib.nfc(x) for x in fm["sources"])


def test_as_list_treats_empty_value_as_empty():
    assert wikilib.as_list("") == []
    assert wikilib.as_list(None) == []
    assert wikilib.as_list([""]) == []
    assert wikilib.as_list("src-가") == ["src-가"]
    assert wikilib.as_list(["src-가"]) == ["src-가"]


def test_all_markdown_skips_scratch_dirs(make_repo):
    root = make_repo({
        "wiki/index.md": page(),
        ".pytest_cache/README.md": "부산물",
        ".superpowers/sdd/메모.md": "부산물",
    })
    rels = {p.relative_to(root).as_posix() for p in wikilib.all_markdown(root)}
    assert rels == {"wiki/index.md"}


def test_all_markdown_skips_dot_dirs_but_not_graphify_out(make_repo):
    """.claude는 점(.) 디렉토리라 Obsidian이 vault 탐색에서 통째로 숨긴다 —
    안의 마크다운(CLAUDE.md·SKILL.md)은 링크 resolve 대상이 될 수 없으므로
    파일명 유일성 검사에서 빠져야 한다. graphify-out은 점 디렉토리가 아니라
    Obsidian이 정상적으로 vault에 포함시키므로 GRAPH_REPORT.md는 여전히
    유일성 검사 대상이어야 한다 — SKIP_DIRS에 넣으면 향후 같은 이름의
    페이지가 생겨도 아무도 잡아내지 못하는 구멍이 된다."""
    root = make_repo({
        "wiki/index.md": page(),
        ".claude/CLAUDE.md": "도구 설정",
        ".claude/skills/graphify/SKILL.md": "도구 스킬",
        "graphify-out/GRAPH_REPORT.md": "그래프 산출물",
    })
    rels = {p.relative_to(root).as_posix() for p in wikilib.all_markdown(root)}
    assert rels == {"wiki/index.md", "graphify-out/GRAPH_REPORT.md"}


def test_finding_lives_in_wikilib():
    f = wikilib.Finding("violation", "코드", "wiki/x.md", "메시지")
    assert (f.level, f.code, f.path, f.message) == ("violation", "코드", "wiki/x.md", "메시지")
    assert "[위반/코드]" in str(f)
    assert "[경고/코드]" in str(wikilib.Finding("warning", "코드", "wiki/x.md", "메시지"))


def test_finding_is_frozen():
    import dataclasses
    f = wikilib.Finding("violation", "코드", "wiki/x.md", "메시지")
    try:
        f.level = "warning"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("Finding은 frozen이어야 한다")
