"""이슈 템플릿 검사.

PyYAML을 쓰지 않는다. 스크립트에 런타임 의존성을 추가하지 않기로 했고,
여기서 확인할 것은 YAML 문법이 아니라 action 옵션이 lint.ACTION_VALUES와
어긋나지 않는다는 결합뿐이다. 어긋나면 사람이 올린 이슈를 파일로 옮길 때
허용되지 않는 action 값이 들어온다.
"""
import pathlib
import re

import lint

TEMPLATE_DIR = pathlib.Path(__file__).resolve().parents[3] / ".github" / "ISSUE_TEMPLATE"


def test_all_templates_exist():
    names = {"open-question.yml", "source-request.yml", "script-bug.yml", "config.yml"}
    assert names <= {p.name for p in TEMPLATE_DIR.glob("*.yml")}


def test_each_template_declares_its_label():
    expected = {
        "open-question.yml": "open-question",
        "source-request.yml": "source-request",
        "script-bug.yml": "script-bug",
    }
    for name, label in expected.items():
        text = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
        assert re.search(rf"^labels:\s*\[{label}\]\s*$", text, re.M), name


def test_open_question_action_options_match_lint():
    text = (TEMPLATE_DIR / "open-question.yml").read_text(encoding="utf-8")
    assert text.count("options:") == 1, "드롭다운이 하나라는 전제가 깨졌다"
    opts = []
    for line in text.split("options:", 1)[1].split("\n")[1:]:
        m = re.match(r"^\s+- (\S+)\s*$", line)
        if not m:
            break
        opts.append(m.group(1))
    assert tuple(opts) == lint.ACTION_VALUES


def test_blank_issues_enabled():
    text = (TEMPLATE_DIR / "config.yml").read_text(encoding="utf-8")
    assert "blank_issues_enabled: true" in text
