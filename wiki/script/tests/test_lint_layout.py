from conftest import page

import lint
import wikilib


def _layout(root):
    return lint.check_layout(wikilib.load_pages(root))


def test_accepted_shapes_pass(make_repo):
    root = make_repo({
        "wiki/index.md": page(),
        "wiki/synthesis/open-questions.md": page(),
        "wiki/domains/a/a-purpose.md": page(),
        "wiki/domains/a/a-index.md": page(),
        "wiki/domains/a/a-overview.md": page(),
        "wiki/domains/a/sources/src-정책.md": page(sources="[정책.md]"),
        "wiki/domains/a/concepts/개념.md": page(sources="[]"),
        "wiki/domains/a/entities/인물.md": page(sources="[]"),
        "wiki/domains/a/queries/질의-2026-08-10.md": page(),
        "wiki/domains/a/synthesis/분석.md": page(),
    })
    assert _layout(root) == []


def test_subdirectory_of_content_dir_is_violation(make_repo):
    root = make_repo({
        "wiki/domains/a/concepts/sub/깊은개념.md": page(sources="[]"),
    })
    found = _layout(root)
    assert [f.code for f in found] == ["배치"]
    assert found[0].level == "violation"
    assert found[0].path == "wiki/domains/a/concepts/sub/깊은개념.md"
    assert "하위 폴더" in found[0].message


def test_loose_file_at_domain_root_is_violation(make_repo):
    root = make_repo({"wiki/domains/a/아무거나.md": page()})
    found = _layout(root)
    assert [f.path for f in found] == ["wiki/domains/a/아무거나.md"]
    assert "도메인 루트" in found[0].message


def test_wrong_domain_prefix_on_structure_file_is_violation(make_repo):
    root = make_repo({"wiki/domains/a/b-index.md": page()})
    found = _layout(root)
    assert [f.code for f in found] == ["배치"]


def test_unknown_directory_is_violation(make_repo):
    root = make_repo({"wiki/domains/a/notes/메모.md": page()})
    found = _layout(root)
    assert [f.code for f in found] == ["배치"]
    assert "콘텐츠 디렉토리가 아님" in found[0].message


def test_file_directly_under_domains_is_violation(make_repo):
    root = make_repo({"wiki/domains/떠돌이.md": page()})
    found = _layout(root)
    assert [f.code for f in found] == ["배치"]
    assert "도메인 디렉토리 없이" in found[0].message


def test_sources_page_without_src_prefix_is_violation(make_repo):
    root = make_repo({
        "wiki/domains/a/sources/정책.md": page(sources="[정책.md]"),
    })
    found = _layout(root)
    assert [f.code for f in found] == ["배치"]
    assert "src-" in found[0].message


def test_src_prefix_only_required_in_sources(make_repo):
    root = make_repo({"wiki/domains/a/concepts/정책.md": page(sources="[]")})
    assert _layout(root) == []


def test_layout_ignores_pages_outside_domains(make_repo):
    root = make_repo({
        "wiki/log.md": "# 로그",
        "wiki/synthesis/open-questions.md": page(),
    })
    assert _layout(root) == []


def test_run_all_reports_layout_violations(make_repo):
    """배치 위반은 run_all에 배선되어 있다 — 규정 밖 페이지가 조용히 통과하면 안 된다."""
    root = make_repo({
        "wiki/index.md": page(body="[[깊은개념]] [[아무거나]]"),
        "wiki/domains/a/concepts/sub/깊은개념.md": "frontmatter 없음",
        "wiki/domains/a/아무거나.md": "frontmatter 없음",
    })
    codes = {f.code for f in lint.run_all(root) if f.level == "violation"}
    assert "배치" in codes
