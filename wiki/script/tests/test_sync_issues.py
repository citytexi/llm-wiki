import pytest

import sync_issues as si

SAMPLE = """---
tags: [open-questions]
updated: 2026-08-11
---

# 미결 항목

### [2026-08-10] 정년 기준이 다르다
- **출처 A**: [[src-정책-2024]] — 60세
- **출처 B**: [[src-정책-2026]] — 65세
- **상태**: 미해결
- **action**: research
- **issue**: #12

### [2026-08-11] 조직도 부서명 불일치
- **출처 A**: [[src-조직도]] — 기획팀
- **상태**: 해소됨
- **action**: create-page
- **해소 메모**: 2026 개편으로 전략기획팀이 맞다
"""


def test_parses_each_heading_as_one_entry():
    entries = si.parse_entries(SAMPLE)
    assert [e.summary for e in entries] == ["정년 기준이 다르다", "조직도 부서명 불일치"]
    assert [e.date for e in entries] == ["2026-08-10", "2026-08-11"]


def test_records_one_based_heading_line():
    first, second = si.parse_entries(SAMPLE)
    assert SAMPLE.split("\n")[first.line - 1].startswith("### [2026-08-10]")
    assert SAMPLE.split("\n")[second.line - 1].startswith("### [2026-08-11]")


def test_fields_keep_document_order():
    first = si.parse_entries(SAMPLE)[0]
    assert [k for k, _ in first.fields] == ["출처 A", "출처 B", "상태", "action", "issue"]
    assert first.get("상태") == "미해결"
    assert first.get("없는필드") is None


def test_fields_before_first_heading_are_ignored():
    entries = si.parse_entries("- **상태**: 미해결\n\n### [2026-08-10] 주제\n- **action**: skip\n")
    assert len(entries) == 1
    assert [k for k, _ in entries[0].fields] == ["action"]


def test_no_entries_when_file_has_none():
    assert si.parse_entries("# 미결 항목\n\n아직 항목이 없다.\n") == []


def test_issue_ref_reads_number():
    first = si.parse_entries(SAMPLE)[0]
    assert si.issue_ref(first) == ("ok", 12)


def test_issue_ref_none_when_field_absent():
    second = si.parse_entries(SAMPLE)[1]
    assert si.issue_ref(second) == ("none", None)


def test_issue_ref_bad_when_format_wrong():
    entry = si.parse_entries("### [2026-08-10] 주제\n- **issue**: 12\n")[0]
    assert si.issue_ref(entry) == ("bad", None)


def test_issue_ref_bad_when_value_is_empty():
    # 'none'으로 처리하면 매 실행마다 이슈를 새로 만들고 앞 이슈를 고아로 남긴다.
    entry = si.parse_entries("### [2026-08-10] 주제\n- **issue**:\n- **action**: skip\n")[0]
    assert entry.get("issue") == ""
    assert si.issue_ref(entry) == ("bad", None)


def test_title_is_prefixed_summary_without_date():
    spec = si.render_issue(si.parse_entries(SAMPLE)[0])
    assert spec.title == "[미결] 정년 기준이 다르다"


def test_body_starts_with_overwrite_warning():
    spec = si.render_issue(si.parse_entries(SAMPLE)[0])
    assert spec.body.startswith("<!-- 자동 생성")
    assert "wiki/synthesis/open-questions.md" in spec.body


def test_body_keeps_fields_but_drops_issue_pointer():
    spec = si.render_issue(si.parse_entries(SAMPLE)[0])
    assert "- **출처 A**: [[src-정책-2024]] — 60세" in spec.body
    assert "- **상태**: 미해결" in spec.body
    # issue 번호는 이 이슈 자신을 가리키는 포인터라 본문에 넣으면 순환이고,
    # 번호가 붙는 순간 본문이 달라져 매번 갱신이 발생한다.
    assert "**issue**" not in spec.body


def test_body_records_the_entry_date():
    spec = si.render_issue(si.parse_entries(SAMPLE)[0])
    assert "제기일: 2026-08-10" in spec.body


def test_labels_include_sync_kind_and_action():
    spec = si.render_issue(si.parse_entries(SAMPLE)[0])
    assert spec.labels == ("wiki-sync", "open-question", "action:research")


def test_label_omits_action_when_field_missing():
    entry = si.parse_entries("### [2026-08-10] 주제\n- **상태**: 미해결\n")[0]
    assert si.render_issue(entry).labels == ("wiki-sync", "open-question")


def test_state_is_open_for_unresolved():
    assert si.render_issue(si.parse_entries(SAMPLE)[0]).state == "open"


def test_state_is_closed_only_for_the_exact_resolved_value():
    entries = si.parse_entries(SAMPLE)
    assert si.render_issue(entries[1]).state == "closed"
    other = si.parse_entries("### [2026-08-10] 주제\n- **상태**: 거의 해소\n")[0]
    assert si.render_issue(other).state == "open"


def test_rendering_is_stable_for_the_same_entry():
    entry = si.parse_entries(SAMPLE)[0]
    assert si.render_issue(entry) == si.render_issue(entry)


def _issue(number=12, title="[미결] 정년 기준이 다르다", body=None,
           labels=("wiki-sync", "open-question", "action:research"), state="open"):
    """SAMPLE 첫 항목과 일치하는 이슈. body를 안 주면 렌더링 결과를 그대로 쓴다."""
    if body is None:
        body = si.render_issue(si.parse_entries(SAMPLE)[0]).body
    return si.Issue(number, title, body, tuple(labels), state)


def test_entry_without_issue_number_becomes_create():
    entries = si.parse_entries("### [2026-08-11] 새 미결\n- **action**: skip\n")
    actions, findings = si.diff(entries, [])
    assert [a.kind for a in actions] == ["create"]
    assert actions[0].number is None
    assert actions[0].line == 1
    assert findings == []


def test_matching_entry_and_issue_produce_no_action():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, findings = si.diff(entries, [_issue()])
    assert actions == [] and findings == []


def test_title_change_produces_update():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, _ = si.diff(entries, [_issue(title="[미결] 옛 제목")])
    assert [a.kind for a in actions] == ["update"]
    assert actions[0].number == 12


def test_body_change_produces_update():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, _ = si.diff(entries, [_issue(body="사람이 손댄 본문")])
    assert [a.kind for a in actions] == ["update"]


def test_stale_action_label_is_removed_on_update():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, _ = si.diff(entries, [_issue(
        labels=("wiki-sync", "open-question", "action:skip"))])
    assert actions[0].kind == "update"
    assert actions[0].remove_labels == ("action:skip",)


def test_foreign_labels_are_left_alone():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, _ = si.diff(entries, [_issue(
        labels=("wiki-sync", "open-question", "action:research", "P1"))])
    assert actions == []


def test_resolved_entry_closes_open_issue():
    text = ("### [2026-08-11] 조직도 부서명 불일치\n"
            "- **출처 A**: [[src-조직도]] — 기획팀\n"
            "- **상태**: 해소됨\n"
            "- **action**: create-page\n"
            "- **issue**: #20\n")
    entry = si.parse_entries(text)[0]
    spec = si.render_issue(entry)
    issue = si.Issue(20, spec.title, spec.body, spec.labels, "open")
    actions, findings = si.diff([entry], [issue])
    assert [a.kind for a in actions] == ["close"]
    assert findings == []


def test_unresolved_entry_reopens_closed_issue():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, _ = si.diff(entries, [_issue(state="closed")])
    assert [a.kind for a in actions] == ["reopen"]


def test_synced_issue_with_no_entry_is_orphan_violation():
    actions, findings = si.diff([], [_issue(number=99)])
    assert actions == []
    assert [(f.level, f.code) for f in findings] == [("violation", "고아이슈")]
    assert "#99" in findings[0].path


def test_unadopted_human_issue_is_only_a_warning():
    human = si.Issue(7, "[미결] 사람이 올린 것", "본문", ("open-question",), "open")
    actions, findings = si.diff([], [human])
    assert actions == []
    assert [(f.level, f.code) for f in findings] == [("warning", "미채택")]


def test_referenced_human_issue_is_adopted_as_update():
    entries = [si.parse_entries(SAMPLE)[0]]
    human = si.Issue(12, "[미결] 정년 기준이 다르다", "사람이 쓴 본문",
                     ("open-question",), "open")
    actions, findings = si.diff(entries, [human])
    assert [a.kind for a in actions] == ["update"]
    assert si.SYNC_LABEL in actions[0].spec.labels
    assert findings == []


def test_bad_issue_value_is_violation_and_creates_nothing():
    entries = si.parse_entries("### [2026-08-10] 주제\n- **issue**: 12\n")
    actions, findings = si.diff(entries, [])
    assert actions == []
    assert [f.code for f in findings] == ["issue형식"]


def test_empty_issue_value_creates_nothing():
    entries = si.parse_entries("### [2026-08-10] 주제\n- **issue**:\n- **action**: skip\n")
    actions, findings = si.diff(entries, [])
    assert actions == []
    assert [f.code for f in findings] == ["issue형식"]
    assert "비어 있다" in findings[0].message


def test_two_entries_on_the_same_number_is_a_duplicate_violation():
    first = si.parse_entries(SAMPLE)[0]
    dup = si.parse_entries("### [2026-08-12] 같은 번호를 가리키는 다른 미결\n"
                           "- **상태**: 미해결\n- **action**: skip\n- **issue**: #12\n")[0]
    actions, findings = si.diff([first, dup], [_issue()])
    # 뒤 항목은 어떤 동작도 내지 않는다. 두 항목이 같은 이슈에 서로 다른 본문으로
    # update를 내면 매 실행마다 상대를 덮어 영원히 수렴하지 않는다.
    assert actions == []
    assert [(f.level, f.code) for f in findings] == [("violation", "중복참조")]
    assert "#12" in findings[0].message


def test_missing_referenced_issue_is_violation():
    entries = [si.parse_entries(SAMPLE)[0]]
    actions, findings = si.diff(entries, [])
    assert actions == []
    assert [f.code for f in findings] == ["이슈없음"]


def test_insert_issue_line_goes_right_after_action():
    text = "### [2026-08-10] 주제\n- **상태**: 미해결\n- **action**: research\n- **해소 메모**: \n"
    out = si.insert_issue_line(text, 1, 7)
    assert out.split("\n")[3] == "- **issue**: #7"


def test_insert_issue_line_falls_back_to_last_field():
    text = "### [2026-08-10] 주제\n- **상태**: 미해결\n\n### [2026-08-11] 다른 주제\n"
    out = si.insert_issue_line(text, 1, 7)
    assert out.split("\n")[2] == "- **issue**: #7"
    assert out.split("\n")[4].startswith("### [2026-08-11]")


def test_insert_issue_line_does_not_touch_other_entries():
    lines = si.insert_issue_line(SAMPLE, 15, 21).split("\n")
    # 개수만 세면 줄이 엉뚱한 항목에 들어가도 통과한다. 위치를 못 박는다:
    # 새 줄은 둘째 항목의 action 바로 뒤여야 하고, 첫 항목의 줄은 제자리에 있어야 한다.
    assert lines[12] == "- **issue**: #12"
    assert lines[17] == "- **action**: create-page"
    assert lines[18] == "- **issue**: #21"
    assert lines.index("### [2026-08-11] 조직도 부서명 불일치") == 14


class FakeGh:
    """GhAdapter와 같은 인터페이스. 네트워크 없이 호출 순서를 기록한다."""

    def __init__(self, issues=(), next_number=100):
        self._issues = list(issues)
        self.next_number = next_number
        self.calls = []

    def available(self):
        return True

    def list_candidates(self):
        return list(self._issues)

    def create(self, spec):
        number = self.next_number
        self.next_number += 1
        self.calls.append(("create", number, spec.title))
        return number

    def update(self, number, spec, remove_labels=()):
        self.calls.append(("update", number, tuple(remove_labels)))

    def set_state(self, number, state):
        self.calls.append(("set_state", number, state))


def _write_oq(tmp_path, text):
    path = tmp_path / "wiki" / "synthesis" / "open-questions.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    (tmp_path / "wiki" / "conventions.md").write_text("계약", encoding="utf-8")
    return path


def test_apply_writes_issue_number_back_to_the_file(tmp_path):
    path = _write_oq(tmp_path, "### [2026-08-11] 새 미결\n- **action**: skip\n")
    entries = si.parse_entries(path.read_text(encoding="utf-8"))
    actions, _ = si.diff(entries, [])
    gh = FakeGh()
    si.apply_actions(actions, gh, path)
    assert "- **issue**: #100" in path.read_text(encoding="utf-8")
    assert gh.calls == [("create", 100, "[미결] 새 미결")]


def test_apply_numbers_multiple_new_entries_without_shifting_lines(tmp_path):
    path = _write_oq(tmp_path,
                     "### [2026-08-11] 하나\n- **action**: skip\n\n"
                     "### [2026-08-11] 둘\n- **action**: skip\n")
    actions, _ = si.diff(si.parse_entries(path.read_text(encoding="utf-8")), [])
    si.apply_actions(actions, FakeGh(), path)
    out = path.read_text(encoding="utf-8").split("\n")
    assert out[1:3] == ["- **action**: skip", "- **issue**: #100"]
    # 두 항목 사이에 빈 줄이 하나 있어서, 앞 항목에 줄이 하나 끼어들면
    # 뒤 항목의 줄 번호도 그만큼 밀린다 — 삽입인 이상 피할 수 없는 결과다.
    assert out[5:7] == ["- **action**: skip", "- **issue**: #101"]


def test_apply_closes_resolved_entry_and_leaves_file_alone(tmp_path):
    body_text = ("### [2026-08-10] 주제\n- **상태**: 해소됨\n"
                 "- **action**: skip\n- **issue**: #5\n")
    path = _write_oq(tmp_path, body_text)
    entry = si.parse_entries(body_text)[0]
    issue = si.Issue(5, si.render_issue(entry).title, si.render_issue(entry).body,
                     ("wiki-sync", "open-question", "action:skip"), "open")
    actions, _ = si.diff([entry], [issue])
    gh = FakeGh([issue])
    si.apply_actions(actions, gh, path)
    assert gh.calls == [("set_state", 5, "closed")]
    assert path.read_text(encoding="utf-8") == body_text


def test_apply_creates_then_closes_a_resolved_new_entry(tmp_path):
    """issue 줄이 없는 '해소됨' 항목은 만들고 곧바로 닫아야 한다.

    생성과 상태 변경을 함께 하는 유일한 경로다. 여기가 깨지면 갓 만든 미결이
    조용히 닫히거나(반대로) 해소된 미결이 열린 채 남는다.
    """
    path = _write_oq(tmp_path, "### [2026-08-11] 이미 해소된 미결\n"
                               "- **상태**: 해소됨\n- **action**: skip\n")
    actions, _ = si.diff(si.parse_entries(path.read_text(encoding="utf-8")), [])
    gh = FakeGh()
    si.apply_actions(actions, gh, path)
    assert gh.calls == [("create", 100, "[미결] 이미 해소된 미결"),
                        ("set_state", 100, "closed")]
    assert "- **issue**: #100" in path.read_text(encoding="utf-8")


def test_apply_keeps_numbers_already_allocated_when_a_later_create_fails(tmp_path):
    """두 번째 create가 터져도 첫 번째 번호는 파일에 남아야 한다.

    번호를 잃으면 이슈는 GitHub에 있는데 파일은 '아직 이슈 없음'이라, 다음 실행이
    같은 미결에 이슈를 하나 더 만들고 앞 이슈는 고아가 된다.
    """
    path = _write_oq(tmp_path,
                     "### [2026-08-11] 하나\n- **action**: skip\n\n"
                     "### [2026-08-11] 둘\n- **action**: skip\n")

    class FailsOnSecond(FakeGh):
        def create(self, spec):
            if [c[0] for c in self.calls].count("create") >= 1:
                raise si.GhError("두 번째 issue create 실패")
            return super().create(spec)

    actions, _ = si.diff(si.parse_entries(path.read_text(encoding="utf-8")), [])
    with pytest.raises(si.GhError):
        si.apply_actions(actions, FailsOnSecond(), path)
    out = path.read_text(encoding="utf-8").split("\n")
    assert out[1:3] == ["- **action**: skip", "- **issue**: #100"]
    assert "#101" not in "\n".join(out)


def test_main_apply_reports_2_but_still_records_the_first_number(tmp_path, monkeypatch,
                                                                capsys):
    path = _write_oq(tmp_path,
                     "### [2026-08-11] 하나\n- **action**: skip\n\n"
                     "### [2026-08-11] 둘\n- **action**: skip\n")
    monkeypatch.chdir(tmp_path)

    class FailsOnSecond(FakeGh):
        def create(self, spec):
            if [c[0] for c in self.calls].count("create") >= 1:
                raise si.GhError("두 번째 issue create 실패")
            return super().create(spec)

    assert si.main(["--apply"], adapter=FailsOnSecond()) == 2
    assert "gh 호출 실패" in capsys.readouterr().err
    assert "- **issue**: #100" in path.read_text(encoding="utf-8")


def test_main_dry_run_reports_diff_and_returns_1(tmp_path, monkeypatch, capsys):
    path = _write_oq(tmp_path, "### [2026-08-11] 새 미결\n- **action**: skip\n")
    monkeypatch.chdir(tmp_path)
    gh = FakeGh()
    assert si.main([], adapter=gh) == 1
    assert gh.calls == []
    assert path.read_text(encoding="utf-8").count("issue") == 0
    assert "신규 생성" in capsys.readouterr().out


def test_main_apply_performs_actions_and_returns_0(tmp_path, monkeypatch, capsys):
    _write_oq(tmp_path, "### [2026-08-11] 새 미결\n- **action**: skip\n")
    monkeypatch.chdir(tmp_path)
    gh = FakeGh()
    assert si.main(["--apply"], adapter=gh) == 0
    assert [c[0] for c in gh.calls] == ["create"]


def test_main_returns_0_when_already_in_sync(tmp_path, monkeypatch, capsys):
    text = ("### [2026-08-10] 정년 기준이 다르다\n"
            "- **출처 A**: [[src-정책-2024]] — 60세\n"
            "- **출처 B**: [[src-정책-2026]] — 65세\n"
            "- **상태**: 미해결\n- **action**: research\n- **issue**: #12\n")
    _write_oq(tmp_path, text)
    monkeypatch.chdir(tmp_path)
    entry = si.parse_entries(text)[0]
    spec = si.render_issue(entry)
    issue = si.Issue(12, spec.title, spec.body, spec.labels, "open")
    assert si.main([], adapter=FakeGh([issue])) == 0


def test_main_returns_1_on_orphan_even_with_apply(tmp_path, monkeypatch, capsys):
    _write_oq(tmp_path, "# 미결 항목\n\n아직 항목이 없다.\n")
    monkeypatch.chdir(tmp_path)
    orphan = si.Issue(9, "[미결] 사라진 항목", "본문", ("wiki-sync",), "open")
    assert si.main(["--apply"], adapter=FakeGh([orphan])) == 1
    assert "고아이슈" in capsys.readouterr().out


def test_main_returns_2_outside_repo_root(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert si.main([], adapter=FakeGh()) == 2


def test_main_returns_2_when_gh_unavailable(tmp_path, monkeypatch, capsys):
    _write_oq(tmp_path, "# 미결 항목\n")
    monkeypatch.chdir(tmp_path)

    class Down(FakeGh):
        def available(self):
            return False

    assert si.main([], adapter=Down()) == 2


def test_main_returns_2_when_apply_call_fails(tmp_path, monkeypatch, capsys):
    path = _write_oq(tmp_path, "### [2026-08-11] 새 미결\n- **action**: skip\n")
    original = path.read_text(encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    class Failing(FakeGh):
        def create(self, spec):
            raise si.GhError("issue create 실패")

    assert si.main(["--apply"], adapter=Failing()) == 2
    assert "gh 호출 실패" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == original
