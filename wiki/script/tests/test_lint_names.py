from conftest import page

import lint


def test_duplicate_stem_across_domains_is_violation(make_repo):
    root = make_repo({
        "wiki/domains/a/concepts/토핑.md": page(),
        "wiki/domains/b/concepts/토핑.md": page(),
    })
    found = lint.check_unique_names(root)
    assert [f.code for f in found] == ["파일명중복"]
    assert "토핑" in found[0].message
    assert found[0].level == "violation"


def test_raw_and_source_page_do_not_collide_with_src_prefix(make_repo):
    root = make_repo({
        "raw/a/정책-v1.md": "원본",
        "wiki/domains/a/sources/src-정책-v1.md": page(sources="[정책-v1.md]"),
    })
    assert lint.check_unique_names(root) == []


def test_raw_and_source_page_collide_without_prefix(make_repo):
    root = make_repo({
        "raw/a/정책-v1.md": "원본",
        "wiki/domains/a/sources/정책-v1.md": page(sources="[정책-v1.md]"),
    })
    assert [f.code for f in lint.check_unique_names(root)] == ["파일명중복"]


def test_unique_names_pass(make_repo):
    root = make_repo({
        "wiki/index.md": page(),
        "wiki/domains/a/a-index.md": page(),
        "wiki/domains/b/b-index.md": page(),
    })
    assert lint.check_unique_names(root) == []


def test_skipped_dirs_do_not_participate_in_uniqueness(make_repo):
    """추적되지 않는 작업 부산물이 파일명 중복을 만들면 안 된다."""
    root = make_repo({
        "wiki/domains/a/concepts/토핑.md": page(),
        ".pytest_cache/토핑.md": "부산물",
        ".superpowers/sdd/토핑.md": "부산물",
    })
    assert lint.check_unique_names(root) == []


def test_runtime_bridge_files_may_share_a_stem(make_repo):
    root = make_repo({"CLAUDE.md": "브리지", "wiki/CLAUDE.md": "진입점"})
    assert lint.check_unique_names(root) == []


def test_template_still_collides_with_a_real_page(make_repo):
    root = make_repo({
        "wiki/templates/concept.md": "템플릿",
        "wiki/domains/a/concepts/concept.md": page(sources="[]"),
    })
    assert [f.code for f in lint.check_unique_names(root)] == ["파일명중복"]


def test_ordinary_page_taking_an_exempt_stem_collides(make_repo):
    """면제 파일의 stem을 일반 콘텐츠 페이지가 가져가면 그대로 위반이다.

    그 페이지는 수집되므로 name index에 있고, [[conventions]]는 깨지지 않고
    조용히 그 페이지로 resolve된다 — 이 검사가 아니면 아무도 못 잡는다.
    """
    root = make_repo({
        "wiki/conventions.md": "계약",
        "wiki/domains/a/concepts/conventions.md": page(sources="[]"),
    })
    found = lint.check_unique_names(root)
    assert [f.code for f in found] == ["파일명중복"]
    assert "wiki/domains/a/concepts/conventions.md" in found[0].message


def test_exempt_stem_collision_needs_only_one_ordinary_page(make_repo):
    """면제 파일끼리의 충돌에 일반 페이지가 하나 끼면 전체가 보고된다."""
    root = make_repo({
        "CLAUDE.md": "브리지",
        "wiki/CLAUDE.md": "진입점",
        "wiki/domains/a/concepts/CLAUDE.md": page(sources="[]"),
    })
    found = lint.check_unique_names(root)
    assert [f.code for f in found] == ["파일명중복"]
    assert "3곳" in found[0].message


def test_ordinary_pages_still_collide(make_repo):
    root = make_repo({
        "wiki/domains/a/concepts/토핑.md": page(sources="[]"),
        "wiki/domains/b/concepts/토핑.md": page(sources="[]"),
    })
    assert [f.code for f in lint.check_unique_names(root)] == ["파일명중복"]
