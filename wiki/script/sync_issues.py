#!/usr/bin/env python3
"""미결 항목 → GitHub 이슈 단방향 투영.

사용: python3 wiki/script/sync_issues.py            (차이만 보고, 기본 dry-run)
      python3 wiki/script/sync_issues.py --apply    (실제로 반영)
종료 코드: 0 일치 / 1 반영할 차이·위반 / 2 실행 환경 불가.

정본은 wiki/synthesis/open-questions.md 다. 이슈는 그 파일의 투영이며,
사람이 이슈 본문을 고쳐도 다음 실행에서 덮인다. 코멘트는 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

import lint

SOURCE_PATH = "wiki/synthesis/open-questions.md"
SYNC_LABEL = "wiki-sync"
KIND_LABEL = "open-question"
# gh issue list 한 번에 읽는 최대 건수. 이 수에 닿으면 목록이 잘렸을 수 있다고 경고한다.
LIST_LIMIT = 500

ITEM_HEAD = re.compile(r"^### \[(\d{4}-\d{2}-\d{2})\]\s*(.*?)\s*$")
FIELD_LINE = re.compile(r"^- \*\*(.+?)\*\*:\s*(.*?)\s*$")


@dataclass(frozen=True)
class Entry:
    date: str
    summary: str
    line: int  # 1-based. 항목 위치를 사람에게 보고하고 issue 줄을 끼워 넣는 데 쓴다.
    fields: tuple[tuple[str, str], ...]

    def get(self, name: str) -> str | None:
        for key, value in self.fields:
            if key == name:
                return value
        return None


def parse_entries(text: str) -> list[Entry]:
    """open-questions.md를 항목 리스트로. 필드 순서는 문서 순서를 그대로 보존한다.

    순서를 지키는 이유는 이슈 본문이 파일을 그대로 비추게 하기 위해서다.
    정렬해 버리면 파일에서 순서만 바꿔도 본문 차이가 생겨 매번 갱신이 발생한다.
    """
    entries: list[Entry] = []
    cur: dict | None = None
    for i, line in enumerate(text.split("\n"), 1):
        head = ITEM_HEAD.match(line)
        if head:
            if cur is not None:
                entries.append(_finish(cur))
            cur = {"date": head.group(1), "summary": head.group(2), "line": i, "fields": []}
            continue
        field = FIELD_LINE.match(line)
        if field and cur is not None:
            cur["fields"].append((field.group(1).strip(), field.group(2).strip()))
    if cur is not None:
        entries.append(_finish(cur))
    return entries


def _finish(cur: dict) -> Entry:
    return Entry(cur["date"], cur["summary"], cur["line"], tuple(cur["fields"]))


def issue_ref(entry: Entry) -> tuple[str, int | None]:
    """('none'|'ok'|'bad', 번호). 'bad'는 값이 있는데 '#숫자'가 아닌 경우다.

    'bad'를 'none'과 구별하는 이유는, 형식이 깨진 값을 '아직 이슈 없음'으로 처리하면
    같은 미결에 이슈가 하나 더 생기기 때문이다. 빈 값도 마찬가지로 'bad'다 —
    'none'으로 처리하면 매 실행마다 이슈를 새로 만들고 앞 이슈를 고아로 남긴다.
    'none'은 issue 줄이 아예 없는 상태만 뜻한다.
    """
    raw = entry.get("issue")
    if raw is None:
        return "none", None
    if lint.ISSUE_VALUE.match(raw):
        return "ok", int(raw[1:])
    return "bad", None


STATE_RESOLVED = "해소됨"
BODY_WARNING = ("<!-- 자동 생성. 여기를 고쳐도 다음 동기화에 덮인다.\n"
                f"     해소는 {SOURCE_PATH} 에 기록한다. -->")


@dataclass(frozen=True)
class IssueSpec:
    title: str
    body: str
    labels: tuple[str, ...]
    state: str  # "open" | "closed"


def render_issue(entry: Entry) -> IssueSpec:
    """항목 하나를 이슈 제목·본문·라벨·개폐 상태로.

    위키 내부 링크 [[페이지]]는 GitHub에서 링크로 해석되지 않지만 그대로 둔다.
    경로를 붙여 GitHub용 링크로 바꾸면 conventions §4의 링크 규칙과 어긋난
    문자열이 이슈에 남아, 이슈에서 파일로 되옮길 때 그대로 새어 들어간다.
    """
    lines = [BODY_WARNING, "", f"제기일: {entry.date}", ""]
    lines += [f"- **{key}**: {value}" for key, value in entry.fields if key != "issue"]
    lines += ["", f"정본: `{SOURCE_PATH}`"]

    labels = [SYNC_LABEL, KIND_LABEL]
    action = entry.get("action")
    if action:
        labels.append(f"action:{action}")

    state = "closed" if entry.get("상태") == STATE_RESOLVED else "open"
    return IssueSpec(f"[미결] {entry.summary}", "\n".join(lines), tuple(labels), state)


ACTION_PREFIX = "action:"


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    labels: tuple[str, ...]
    state: str  # "open" | "closed"


@dataclass(frozen=True)
class Action:
    kind: str  # "create" | "update" | "close" | "reopen"
    line: int  # 대응하는 항목의 ### 줄 번호 (1-based)
    number: int | None
    spec: IssueSpec
    remove_labels: tuple[str, ...] = ()
    note: str = ""


def owned_labels(labels) -> set[str]:
    """스크립트가 관리하는 라벨만. 사람이 붙인 라벨(P1 등)은 건드리지 않는다."""
    return {lb for lb in labels
            if lb in (SYNC_LABEL, KIND_LABEL) or lb.startswith(ACTION_PREFIX)}


def diff(entries: list[Entry], issues: list[Issue]) -> tuple[list[Action], list[lint.Finding]]:
    """(할 일, 보고할 것). issues는 wiki-sync 또는 open-question 라벨이 붙은 것만 들어온다."""
    by_number = {i.number: i for i in issues}
    actions: list[Action] = []
    findings: list[lint.Finding] = []
    referenced: set[int] = set()

    for entry in entries:
        kind, number = issue_ref(entry)
        spec = render_issue(entry)
        where = f"{SOURCE_PATH}:{entry.line}"
        if kind == "bad":
            findings.append(lint.Finding(
                "violation", "issue형식", where,
                f"'{entry.summary}' 항목의 "
                f"{lint.issue_value_message(entry.get('issue') or '')}"
                f" — 이슈를 새로 만들지 않고 건너뛴다"))
            continue
        if kind == "none":
            actions.append(Action("create", entry.line, None, spec,
                                  note=f"신규 생성: {entry.summary}"))
            continue

        if number in referenced:
            # 같은 번호를 두 항목이 가리키면 양쪽이 서로 다른 본문으로 update를 내고
            # 매 실행마다 상대를 덮는다. 수렴하지 않아 종료 코드 1이 영구히 남고,
            # 미결 하나는 GitHub에서 조용히 남의 내용으로 표시된다.
            findings.append(lint.Finding(
                "violation", "중복참조", where,
                f"'{entry.summary}' 항목이 참조하는 #{number} 이슈를 앞의 다른 항목이 "
                f"이미 참조한다 — 이슈 하나는 미결 하나만 비춘다. 건너뛴다"))
            continue
        referenced.add(number)
        current = by_number.get(number)
        if current is None:
            findings.append(lint.Finding(
                "violation", "이슈없음", where,
                f"'{entry.summary}' 항목이 참조하는 #{number} 이슈를 찾을 수 없다"))
            continue

        stale = tuple(sorted(owned_labels(current.labels) - set(spec.labels)))
        if (current.title, current.body) != (spec.title, spec.body) or stale or \
                not set(spec.labels) <= set(current.labels):
            actions.append(Action("update", entry.line, number, spec, stale,
                                  f"내용 갱신: {entry.summary}"))
        if current.state != spec.state:
            actions.append(Action("close" if spec.state == "closed" else "reopen",
                                  entry.line, number, spec,
                                  note=f"상태 변경({current.state} → {spec.state}): {entry.summary}"))

    for issue in issues:
        if issue.number in referenced:
            continue
        if SYNC_LABEL in issue.labels:
            findings.append(lint.Finding(
                "violation", "고아이슈", f"#{issue.number}",
                f"'{issue.title}' 이슈를 참조하는 항목이 {SOURCE_PATH} 에 없다. "
                f"자동으로 닫지 않는다 — 해소인지 실수로 지운 것인지 사람이 판단해야 한다"))
        else:
            findings.append(lint.Finding(
                "warning", "미채택", f"#{issue.number}",
                f"'{issue.title}' 이슈가 아직 {SOURCE_PATH} 에 항목으로 옮겨지지 않았다"))
    return actions, findings


def insert_issue_line(text: str, head_line: int, number: int) -> str:
    """항목의 action 줄 바로 뒤에 `- **issue**: #N` 을 끼워 넣는다.

    action 줄을 기준으로 삼는 이유는 conventions §3의 필드 순서(action 다음 issue,
    그다음 해소 메모)와 맞추기 위해서다. action이 없으면(그 자체가 lint 위반이다)
    항목의 마지막 필드 줄 뒤에 붙인다.
    """
    lines = text.split("\n")
    action_at = last_field_at = None
    i = head_line  # head_line은 1-based라 이 인덱스가 제목 다음 줄이다.
    while i < len(lines):
        if ITEM_HEAD.match(lines[i]):
            break
        if FIELD_LINE.match(lines[i]):
            last_field_at = i
            if lines[i].startswith("- **action**:"):
                action_at = i
        i += 1
    at = action_at if action_at is not None else last_field_at
    if at is None:
        at = head_line - 1
    lines.insert(at + 1, f"- **issue**: #{number}")
    return "\n".join(lines)


def apply_actions(actions: list[Action], adapter, path) -> None:
    """계산된 동작을 실행하고, 새로 만든 이슈 번호를 파일에 기입한다.

    이슈 생성은 문서 순서(위→아래)대로 호출한다. gh가 매기는 번호는 호출 순서를
    따라가므로, 문서 순서와 다르게 호출하면 파일 위쪽 항목이 아래쪽 항목보다 더
    큰 번호를 받아 사람이 보기에 뒤집힌다.

    반면 파일에 issue 줄을 끼워 넣는 것은 줄 번호가 큰 항목부터 거꾸로 처리한다.
    위에서부터 끼워 넣으면 아래 항목의 줄 번호가 하나씩 밀려 issue 줄이 남의
    항목에 들어간다. 그래서 번호를 받는 순서와 줄에 쓰는 순서를 분리했다.
    """
    creates = [a for a in actions if a.kind == "create"]
    for action in actions:
        if action.kind == "update":
            adapter.update(action.number, action.spec, action.remove_labels)
        elif action.kind == "close":
            adapter.set_state(action.number, "closed")
        elif action.kind == "reopen":
            adapter.set_state(action.number, "open")

    if not creates:
        return
    numbered = []
    try:
        for action in creates:
            number = adapter.create(action.spec)
            # 번호를 먼저 기록한다. 뒤이은 set_state가 실패해도 이미 발급된 번호는
            # 파일에 남아야 한다.
            numbered.append((action.line, number))
            if action.spec.state == "closed":
                adapter.set_state(number, "closed")
    finally:
        # 도중에 실패해도 그때까지 받은 번호는 반드시 파일에 쓴다. 번호를 잃으면
        # 이슈는 GitHub에 남았는데 파일은 '아직 이슈 없음'이라, 다음 실행이 같은
        # 미결에 이슈를 하나 더 만들고 앞 이슈는 고아가 된다.
        if numbered:
            text = path.read_text(encoding="utf-8")
            for line, number in sorted(numbered, key=lambda pair: pair[0], reverse=True):
                text = insert_issue_line(text, line, number)
            path.write_text(text, encoding="utf-8")


class GhError(RuntimeError):
    pass


class GhAdapter:
    """gh CLI 호출만 담당한다. 순수 계층이 이 클래스를 몰라야 테스트가 네트워크에서 자유롭다."""

    def __init__(self, repo_root: pathlib.Path):
        self.cwd = repo_root

    def _run(self, args: list[str]) -> str:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=self.cwd)
        if proc.returncode != 0:
            raise GhError((proc.stderr or proc.stdout).strip())
        return proc.stdout

    def available(self) -> bool:
        try:
            proc = subprocess.run(["gh", "auth", "status"], capture_output=True,
                                  text=True, cwd=self.cwd)
        except OSError:
            return False
        return proc.returncode == 0

    def list_candidates(self) -> list[Issue]:
        out = self._run(["issue", "list", "--state", "all", "--limit", str(LIST_LIMIT),
                         "--json", "number,title,body,labels,state"])
        raw_issues = json.loads(out or "[]")
        if len(raw_issues) == LIST_LIMIT:
            # 잘린 목록에서는 항목이 참조하는 이슈가 빠져 '이슈없음' 위반이 거짓으로
            # 뜬다. 조용히 잘리면 그 위반을 보고 사람이 멀쩡한 issue 줄을 지운다.
            print(f"경고: 이슈를 {LIST_LIMIT}건까지만 읽었다 — 목록이 잘렸을 수 있고, "
                  f"'이슈없음' 위반이 사실이 아닐 수 있다.", file=sys.stderr)
        issues = []
        for raw in raw_issues:
            labels = tuple(sorted(lb["name"] for lb in raw.get("labels", [])))
            if SYNC_LABEL not in labels and KIND_LABEL not in labels:
                continue
            issues.append(Issue(raw["number"], raw["title"], raw.get("body") or "",
                                labels, raw["state"].lower()))
        return issues

    def create(self, spec: IssueSpec) -> int:
        args = ["issue", "create", "--title", spec.title, "--body", spec.body]
        for label in spec.labels:
            args += ["--label", label]
        out = self._run(args)
        # gh 출력이 예상과 다르면 여기서 IndexError/ValueError가 난다. 그대로 두면
        # main의 `except GhError`를 빠져나가 파이썬 예외로 죽거나 종료 코드 1이 된다.
        # 1은 '반영할 차이가 남았다'는 뜻이라, 이슈를 막 만든 직후에 그 코드가 나오면
        # 실패가 정상 진행으로 읽힌다. GhError로 바꿔 2(실행 불가)로 흐르게 한다.
        try:
            url = out.strip().splitlines()[-1]
            return int(url.rstrip("/").split("/")[-1])
        except (IndexError, ValueError) as err:
            raise GhError(f"issue create 출력에서 이슈 번호를 읽지 못했다: {out!r}") from err

    def update(self, number: int, spec: IssueSpec, remove_labels=()) -> None:
        args = ["issue", "edit", str(number), "--title", spec.title, "--body", spec.body]
        for label in spec.labels:
            args += ["--add-label", label]
        for label in remove_labels:
            args += ["--remove-label", label]
        self._run(args)

    def set_state(self, number: int, state: str) -> None:
        self._run(["issue", "close" if state == "closed" else "reopen", str(number)])


def main(argv=None, adapter=None) -> int:
    parser = argparse.ArgumentParser(
        description="미결 항목을 GitHub 이슈로 투영한다 (파일이 정본).")
    parser.add_argument("--apply", action="store_true",
                        help="실제로 이슈를 만들고 고친다. 기본은 차이만 보고하는 dry-run이다.")
    ns = parser.parse_args(argv)

    repo_root = pathlib.Path.cwd()
    if not lint.repo_root_ok(repo_root):
        print(lint.wrong_root_message(repo_root), file=sys.stderr)
        return 2

    adapter = adapter if adapter is not None else GhAdapter(repo_root)
    if not adapter.available():
        print("gh 를 쓸 수 없다 (설치·인증 확인). 이슈를 하나도 못 읽은 상태를 "
              "'차이 없음'으로 보고하면 잘못된 안심을 준다.", file=sys.stderr)
        return 2

    path = repo_root / SOURCE_PATH
    if not path.exists():
        print(f"{SOURCE_PATH} 이 없다.", file=sys.stderr)
        return 2

    entries = parse_entries(path.read_text(encoding="utf-8"))
    try:
        issues = adapter.list_candidates()
    except GhError as err:
        print(f"gh 호출 실패: {err}", file=sys.stderr)
        return 2

    actions, findings = diff(entries, issues)
    violations = [f for f in findings if f.level == "violation"]
    warnings = [f for f in findings if f.level == "warning"]

    print(f"항목 {len(entries)}건, 대상 이슈 {len(issues)}건")
    print(f"\n## 할 일 {len(actions)}건" + ("" if ns.apply else " (dry-run — 반영하지 않음)"))
    for action in actions:
        number = f"#{action.number}" if action.number else "신규"
        print(f"- [{action.kind}] {number} {action.note}")
    print(f"\n## 위반 {len(violations)}건")
    for finding in violations:
        print(f"- {finding}")
    print(f"\n## 경고 {len(warnings)}건 (종료 코드에 영향 없음)")
    for finding in warnings:
        print(f"- {finding}")

    if ns.apply and actions:
        # gh 호출 도중 실패해도 apply_actions가 그때까지 발급된 번호는 파일에 쓰고
        # 나서 예외를 올린다. 그래서 남는 부분 반영은 '이슈는 있는데 번호가 없다'가
        # 아니라 '아직 안 만든 것이 남았다'뿐이고, 다음 실행이 나머지만 이어서 만든다.
        try:
            apply_actions(actions, adapter, path)
        except GhError as err:
            print(f"gh 호출 실패: {err}", file=sys.stderr)
            return 2
        print(f"\n반영 완료. 파일이 바뀌었으면 커밋한다: {SOURCE_PATH}")
        return 1 if violations else 0
    return 1 if (actions or violations) else 0


if __name__ == "__main__":
    sys.exit(main())
