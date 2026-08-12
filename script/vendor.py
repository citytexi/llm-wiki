#!/usr/bin/env python3
"""외부 스킬 repo를 .claude/skills/로 벤더링하고 baseline 대비 delta로 갱신한다.

용법:
    python3 script/vendor.py --full [--dry-run]     # 전량 벤더(초기 설치)
    python3 script/vendor.py --update [--dry-run]   # baseline 대비 delta 업데이트

규약: stdlib 전용. repo 루트 = Path(__file__).resolve().parents[1].
"""
import argparse
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]   # script/vendor.py → repo 루트
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
VENDOR_DIR = REPO_ROOT / ".claude" / "skills-vendor"
CACHE = VENDOR_DIR / ".cache"
SOURCES = VENDOR_DIR / "sources.json"
BASELINE_JSON = VENDOR_DIR / "baseline.json"
MANIFEST_JSON = VENDOR_DIR / "manifest.json"
LICENSES = VENDOR_DIR / "licenses"


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True).stdout


def leaf_name(skill_md_path):
    return Path(skill_md_path).parent.name


def _is_skill_path(p):
    return p.endswith("SKILL.md") and not any(seg.startswith(".") for seg in p.split("/"))


def affected(diff_text):
    res = {}
    for line in diff_text.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        if not _is_skill_path(path) or "/" not in path:
            continue
        res[leaf_name(path)] = "del" if status.startswith("D") else "mod"
    return res


def _topic(path):
    segs = Path(path).parts
    top = segs[0]
    if top == "skills" and len(segs) >= 2:      # skills/<이름>/ 로 평평하게 담은 repo
        return "skills"
    return top


def default_branch(url):
    out = run(["git", "ls-remote", "--symref", url, "HEAD"])
    m = re.search(r"ref:\s+refs/heads/(\S+)\s+HEAD", out)
    return m.group(1) if m else "main"


def sync_cache(repo):
    dest = CACHE / repo["name"]
    if not dest.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--filter=blob:none", repo["url"], str(dest)])
    branch = repo.get("branch") or default_branch(repo["url"])
    run(["git", "fetch", "origin", branch], cwd=dest)
    run(["git", "checkout", branch], cwd=dest)
    run(["git", "reset", "--hard", f"origin/{branch}"], cwd=dest)
    sha = run(["git", "rev-parse", "HEAD"], cwd=dest).strip()
    return dest, branch, sha


def discover(cache, ref):
    out = run(["git", "ls-tree", "-r", "--name-only", ref], cwd=cache)
    return [p for p in out.splitlines() if _is_skill_path(p) and "/" in p]


def copy_skill(cache, skill_md_rel, leaf):
    src = cache / Path(skill_md_rel).parent
    dst = SKILLS_DIR / leaf
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git*"))


def _copy_license(cache, name):
    for lic in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        p = cache / lic
        if p.exists():
            LICENSES.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, LICENSES / f"{name}.LICENSE")
            return


def _load_prior_manifest():
    """디스크의 manifest.json. --full이 자작 스킬과 이전 벤더 산출물을 구별하는 근거."""
    if MANIFEST_JSON.exists():
        return json.loads(MANIFEST_JSON.read_text())
    return {}


def _load_prior_baseline():
    """디스크의 baseline.json. --full이 중단돼도 미처리 repo의 SHA를 잃지 않게 하는 근거."""
    if BASELINE_JSON.exists():
        return json.loads(BASELINE_JSON.read_text())
    return {}


MAX_PREFIX_RETRY = 64   # 접두사 회피 시도 상한. 점유 이름이 유한하므로 실제로는 도달하지 않는다.


def _resolve_leaf(md, repo_name, seen, taken):
    """leaf 이름을 결정한다. --full과 --update가 공유하는 단일 규칙.

    seen  : 이번 실행에서 이미 배정한 {leaf: repo}. 같은 repo 안의 basename 중복도 여기서 걸린다.
    taken : (leaf, repo_name) -> bool. 이 실행 밖에서 그 이름이 점유돼 있으면 True.

    점유된 이름이면 `<repo접두사>-`를 붙이고, 그 이름도 점유돼 있으면 다시 붙인다(2차 충돌).
    """
    prefix = repo_name.split("-")[0]
    leaf = leaf_name(md)
    for _ in range(MAX_PREFIX_RETRY):
        if leaf not in seen and not taken(leaf, repo_name):
            seen[leaf] = repo_name
            return leaf
        leaf = f"{prefix}-{leaf}"
    raise RuntimeError(f"leaf 이름 충돌을 회피하지 못했다: {md} ({repo_name})")


def _taken_after_prune(pruned):
    """--full용 점유 판정. prune 대상을 뺀 나머지 디스크 디렉토리는 전부 자작 스킬이다."""
    def taken(leaf, repo_name):
        return leaf not in pruned and (SKILLS_DIR / leaf).exists()
    return taken


def _taken_by_manifest(manifest):
    """--update용 점유 판정. 다른 repo 소유이거나, manifest에 없는데 디스크에 있으면 점유."""
    def taken(leaf, repo_name):
        owner = manifest.get(leaf, {}).get("repo")
        if owner is not None:
            return owner != repo_name
        return (SKILLS_DIR / leaf).exists()
    return taken


def _write_state(baseline, manifest):
    BASELINE_JSON.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n")
    MANIFEST_JSON.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


def _desc_of(leaf):
    md = SKILLS_DIR / leaf / "SKILL.md"
    if not md.exists():
        return ""
    m = re.search(r"^description:\s*(.+)$", md.read_text(encoding="utf-8", errors="ignore"), re.M)
    return (m.group(1).strip().strip("\"'")[:140]) if m else ""


def render_docs(baseline, manifest):
    today = date.today().isoformat()
    lines = ["# 벤더 스킬 baseline (SoT = baseline.json)", "",
             f"> 갱신: {today}", "", "| repo | branch | SHA |", "|---|---|---|"]
    for name, info in baseline.items():
        lines.append(f"| {name} | {info['branch']} | `{info['sha'][:9]}` |")
    (VENDOR_DIR / "baseline.md").write_text("\n".join(lines) + "\n")

    ml = ["# 벤더 스킬 MANIFEST (SoT = manifest.json)", "",
          f"> 갱신: {today} | 총 {len(manifest)}개", "", "| skill | repo | 원본 경로 |", "|---|---|---|"]
    for leaf in sorted(manifest):
        i = manifest[leaf]
        ml.append(f"| {leaf} | {i['repo']} | `{i['path']}` |")
    (VENDOR_DIR / "MANIFEST.md").write_text("\n".join(ml) + "\n")

    groups = {}
    for leaf, i in manifest.items():
        groups.setdefault((i["repo"], _topic(i["path"])), []).append(leaf)
    cl = ["# 벤더 스킬 CATALOG (주제별)", "",
          f"> 갱신: {today} | spec/plan 작성 시 `skill-finder`로 검색, 목차는 아래.", ""]
    for key in sorted(groups):
        cl.append(f"## {key[0]} / {key[1]}")
        for leaf in sorted(groups[key]):
            cl.append(f"- **{leaf}** — {_desc_of(leaf)}")
        cl.append("")
    (VENDOR_DIR / "CATALOG.md").write_text("\n".join(cl) + "\n")


def prune_prior(prior, dry=False):
    """이전 manifest에 있던 leaf 디렉토리를 지운다. 벤더 소유임이 확정된 것들이라 안전하다.

    "디스크 = manifest" 불변식을 --full이 스스로 지키게 하는 장치다. 지우지 않으면 upstream이
    삭제한 스킬·sources.json에서 뺀 repo의 산출물이 고아로 남아 이후 자작 스킬로 오분류된다.
    반환값은 지웠거나(dry면 지울) leaf 집합으로, 그대로 점유 판정에서 제외된다.
    """
    pruned = set(prior)
    if not dry:
        for leaf in sorted(pruned):
            d = SKILLS_DIR / leaf
            if d.is_dir():
                shutil.rmtree(d)
    return pruned


def full_vendor(dry=False):
    sources = json.loads(SOURCES.read_text())["repos"]
    prior = _load_prior_manifest()
    prior_baseline = _load_prior_baseline()

    synced, baseline = [], {}
    for repo in sources:            # 네트워크 단계를 먼저 끝낸다 — 중간 실패 시 디스크를 건드리지 않는다
        cache, branch, sha = sync_cache(repo)
        synced.append((repo, cache, sha))
        baseline[repo["name"]] = {"sha": sha, "branch": branch, "url": repo["url"]}

    taken = _taken_after_prune(prune_prior(prior, dry=dry))
    manifest, seen, renamed = {}, {}, []
    done = {}
    pending = {repo["name"] for repo in sources}   # 이번 sources.json에 있고 아직 처리하지 않은 repo

    def checkpoint():
        """증분 기록. 아직 처리하지 않은 repo의 기존 기록을 시드로 깔아 절삭을 막는다.

        시드 대상은 pending, 즉 "이번 sources.json에 있는데 아직 처리 안 한 repo"뿐이다.
        sources.json에서 뺀 repo는 pending에 없으므로 시드에도 없고, 그래서 제거 시 정리
        동작은 그대로다. 이번 실행이 배정한 것(done·manifest)이 항상 시드를 이긴다.
        """
        seed_b = {n: i for n, i in prior_baseline.items() if n in pending}
        seed_m = {leaf: i for leaf, i in prior.items() if i.get("repo") in pending}
        _write_state({**seed_b, **done}, {**seed_m, **manifest})

    for repo, cache, sha in synced:
        for md in discover(cache, "HEAD"):
            leaf = _resolve_leaf(md, repo["name"], seen, taken)
            if leaf != leaf_name(md):
                renamed.append((leaf_name(md), leaf, repo["name"]))
            manifest[leaf] = {"repo": repo["name"], "path": md, "sha": sha}
            if not dry:
                checkpoint()          # 복사 전에 기록한다 — 복사 도중 죽어도 소유권이 남는다
                copy_skill(cache, md, leaf)
        if not dry:
            _copy_license(cache, repo["name"])
            done[repo["name"]] = baseline[repo["name"]]
            pending.discard(repo["name"])
            checkpoint()   # repo 단위 증분 기록 — 도중에 죽어도 다음 실행이 정리한다
    if not dry:
        _write_state(baseline, manifest)   # pending이 비었으므로 절삭이 아니라 제거분 정리다
        render_docs(baseline, manifest)
    return baseline, manifest, renamed


def update(dry=False):
    # 없으면 빈 상태로 읽는다 — 아직 한 번도 벤더하지 않은 새 클론에서 --update가
    # 트레이스백으로 죽지 않게 한다. 빈 baseline에서는 sources.json의 모든 repo가
    # base=None이 되어 전량 add로 분류되며, 그것이 맞는 판정이다.
    baseline = _load_prior_baseline()
    manifest = _load_prior_manifest()
    sources = json.loads(SOURCES.read_text())["repos"]
    changes = {"added": [], "modified": [], "deleted": [], "renamed": []}
    taken = _taken_by_manifest(manifest)   # manifest는 루프 중 갱신되고, 판정은 그 최신 상태를 본다
    seen = {}                              # 실행 전체에서 공유한다 — repo 간·repo 내 충돌을 같이 막는다
    for repo in sources:
        name = repo["name"]
        cache, branch, head = sync_cache(repo)
        base = baseline.get(name, {}).get("sha")
        if base == head:
            continue
        if not dry:
            _copy_license(cache, name)
        cur = {}
        for md in discover(cache, "HEAD"):
            leaf = _resolve_leaf(md, name, seen, taken)
            if leaf != leaf_name(md):
                changes["renamed"].append((leaf_name(md), leaf, name))
            cur[leaf] = md
        prev = {leaf for leaf, i in manifest.items() if i["repo"] == name}
        for leaf in list(prev):                       # 삭제분
            if leaf not in cur:
                changes["deleted"].append(leaf)
                if not dry and (SKILLS_DIR / leaf).exists():
                    shutil.rmtree(SKILLS_DIR / leaf)
                manifest.pop(leaf, None)
        for leaf, md in cur.items():                   # 추가/수정분
            d = str(Path(md).parent)
            diff = run(["git", "diff", "--name-only", f"{base}..HEAD", "--", d], cwd=cache) if base else "x"
            if leaf not in manifest:
                changes["added"].append(leaf)
            elif diff.strip():
                changes["modified"].append(leaf)
            else:
                continue
            if not dry:
                copy_skill(cache, md, leaf)
            manifest[leaf] = {"repo": name, "path": md, "sha": head}
        baseline[name] = {"sha": head, "branch": branch, "url": repo["url"]}
    if not dry:
        _write_state(baseline, manifest)
        render_docs(baseline, manifest)
    return changes


def main():
    ap = argparse.ArgumentParser(description="스킬 벤더링/갱신")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--full", action="store_true", help="전량 벤더(초기 설치)")
    g.add_argument("--update", action="store_true", help="baseline 대비 delta 업데이트")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.full:
        b, m, renamed = full_vendor(dry=a.dry_run)
        print(f"[full] {len(b)} repos, {len(m)} skills{' (dry)' if a.dry_run else ''}")
        _print_renamed(renamed)
    else:
        c = update(dry=a.dry_run)
        print(f"[update] +{len(c['added'])} ~{len(c['modified'])} -{len(c['deleted'])}{' (dry)' if a.dry_run else ''}")
        for k in ("added", "modified", "deleted"):
            if c[k]:
                print(f"  {k}: {', '.join(sorted(c[k]))}")
        _print_renamed(c["renamed"])


def _print_renamed(renamed):
    """이름 충돌 회피는 조용히 넘기지 않는다 — 어떤 스킬이 어떤 이름으로 들어갔는지 보인다."""
    for orig, leaf, repo in sorted(renamed):
        print(f"  이름 충돌 회피: {orig} → {leaf} ({repo})")


if __name__ == "__main__":
    main()
