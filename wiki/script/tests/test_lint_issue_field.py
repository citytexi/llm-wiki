import lint

HEAD = "### [2026-08-10] 주제"


def _oq(body: str) -> dict:
    return {"wiki/synthesis/open-questions.md": body}


def test_valid_issue_value_passes(make_repo):
    root = make_repo(_oq(f"{HEAD}\n- **action**: research\n- **issue**: #12\n"))
    assert lint.check_issue_field(root) == []


def test_missing_issue_field_is_not_a_violation(make_repo):
    root = make_repo(_oq(f"{HEAD}\n- **action**: research\n"))
    assert lint.check_issue_field(root) == []


def test_non_hash_number_value_is_violation(make_repo):
    root = make_repo(_oq(f"{HEAD}\n- **issue**: 12\n"))
    found = lint.check_issue_field(root)
    assert [f.code for f in found] == ["issue"]
    assert found[0].path == "wiki/synthesis/open-questions.md:2"


def test_empty_issue_value_is_violation(make_repo):
    # 값 없는 issue 줄은 sync가 '아직 이슈 없음'으로 읽어 매 실행마다 이슈를
    # 새로 만든다. 줄이 아예 없는 것과 달라서 여기서 잡아야 한다.
    root = make_repo(_oq(f"{HEAD}\n- **issue**:\n- **action**: research\n"))
    found = lint.check_issue_field(root)
    assert [f.code for f in found] == ["issue"]
    assert found[0].path == "wiki/synthesis/open-questions.md:2"
    assert "비어 있다" in found[0].message


def test_issue_value_with_only_spaces_is_violation(make_repo):
    root = make_repo(_oq(f"{HEAD}\n- **issue**:   \n"))
    assert [f.code for f in lint.check_issue_field(root)] == ["issue"]


def test_url_value_is_violation(make_repo):
    root = make_repo(_oq(f"{HEAD}\n- **issue**: https://github.com/a/b/issues/12\n"))
    assert [f.level for f in lint.check_issue_field(root)] == ["violation"]


def test_missing_file_is_not_a_violation(make_repo):
    root = make_repo({"wiki/conventions.md": "계약"})
    assert lint.check_issue_field(root) == []


def test_run_all_includes_issue_field_check(make_repo):
    root = make_repo(_oq(f"{HEAD}\n- **action**: research\n- **issue**: 12\n"))
    assert "issue" in {f.code for f in lint.run_all(root)}
