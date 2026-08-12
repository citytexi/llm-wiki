import json

import pytest

import vendor


class TestLeafName:
    def test_중첩_경로는_마지막_디렉토리명(self):
        assert vendor.leaf_name("jetpack-compose/theming/styles/SKILL.md") == "styles"

    def test_skills_래퍼도_마지막_디렉토리명(self):
        assert vendor.leaf_name("skills/compose-state-hoisting/SKILL.md") == "compose-state-hoisting"

    def test_루트_SKILL은_빈_문자열(self):
        assert vendor.leaf_name("SKILL.md") == ""


class TestIsSkillPath:
    def test_SKILL_md로_끝나야_한다(self):
        assert vendor._is_skill_path("a/b/SKILL.md")
        assert not vendor._is_skill_path("a/b/README.md")

    def test_점으로_시작하는_경로_조각은_제외(self):
        assert not vendor._is_skill_path(".claude-plugin/x/SKILL.md")
        assert not vendor._is_skill_path("a/.hidden/SKILL.md")


class TestAffected:
    def test_추가와_삭제를_분류한다(self):
        diff = "A\tskills/new-skill/SKILL.md\nD\tskills/old-skill/SKILL.md\nM\tsrc/other.kt"
        res = vendor.affected(diff)
        assert res["new-skill"] == "mod"
        assert res["old-skill"] == "del"
        assert "other" not in res

    def test_점_디렉토리는_결과에_없다(self):
        assert vendor.affected("A\t.claude-plugin/x/SKILL.md") == {}


class TestTopic:
    def test_주제_디렉토리를_쓰는_repo(self):
        assert vendor._topic("jetpack-compose/theming/styles/SKILL.md") == "jetpack-compose"

    def test_skills_래퍼를_쓰는_repo(self):
        assert vendor._topic("skills/compose-state-hoisting/SKILL.md") == "skills"


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    d = tmp_path / ".claude" / "skills"
    d.mkdir(parents=True)
    monkeypatch.setattr(vendor, "SKILLS_DIR", d)
    return d


class TestResolveLeafFull:
    """--full 경로: prune 후의 디스크가 점유 판정 근거다."""

    def test_충돌_없으면_그대로(self, skills_dir):
        seen = {}
        taken = vendor._taken_after_prune(set())
        assert vendor._resolve_leaf("a/styles/SKILL.md", "android-skills", seen, taken) == "styles"
        assert seen == {"styles": "android-skills"}

    def test_같은_실행_내_repo_간_충돌은_접두사(self, skills_dir):
        seen = {}
        taken = vendor._taken_after_prune(set())
        vendor._resolve_leaf("a/styles/SKILL.md", "android-skills", seen, taken)
        got = vendor._resolve_leaf("b/styles/SKILL.md", "chrisbanes-skills", seen, taken)
        assert got == "chrisbanes-styles"

    def test_자작_스킬_이름은_침범하지_않는다(self, skills_dir):
        (skills_dir / "graphify").mkdir()
        taken = vendor._taken_after_prune(set())
        assert vendor._resolve_leaf("a/graphify/SKILL.md", "android-skills", {}, taken) == "android-graphify"

    def test_이전_벤더_산출물은_덮어쓴다(self, skills_dir):
        (skills_dir / "styles").mkdir()
        taken = vendor._taken_after_prune({"styles"})   # prune 대상 = 이전 manifest의 leaf
        assert vendor._resolve_leaf("a/styles/SKILL.md", "android-skills", {}, taken) == "styles"

    def test_같은_repo_안의_basename_중복도_회피한다(self, skills_dir):
        seen = {}
        taken = vendor._taken_after_prune(set())
        first = vendor._resolve_leaf("a/dup/SKILL.md", "android-skills", seen, taken)
        second = vendor._resolve_leaf("b/dup/SKILL.md", "android-skills", seen, taken)
        assert (first, second) == ("dup", "android-dup")


class TestResolveLeafUpdate:
    """--update 경로: manifest 소유권이 점유 판정 근거다. --full과 같은 함수를 쓴다."""

    def test_같은_repo_소유면_그대로(self, skills_dir):
        manifest = {"styles": {"repo": "android-skills", "path": "a/styles/SKILL.md", "sha": "x"}}
        taken = vendor._taken_by_manifest(manifest)
        assert vendor._resolve_leaf("a/styles/SKILL.md", "android-skills", {}, taken) == "styles"

    def test_다른_repo가_소유하면_접두사(self, skills_dir):
        manifest = {"styles": {"repo": "android-skills", "path": "a/styles/SKILL.md", "sha": "x"}}
        taken = vendor._taken_by_manifest(manifest)
        assert vendor._resolve_leaf("b/styles/SKILL.md", "chrisbanes-skills", {}, taken) == "chrisbanes-styles"

    def test_manifest에_없는데_디렉토리가_있으면_자작_스킬이라_접두사(self, skills_dir):
        (skills_dir / "graphify").mkdir()
        taken = vendor._taken_by_manifest({})
        assert vendor._resolve_leaf("a/graphify/SKILL.md", "android-skills", {}, taken) == "android-graphify"

    def test_I2_같은_repo_안의_basename_중복이_서로를_덮지_않는다(self, skills_dir):
        """seen 없이 dict comprehension을 돌리면 뒤엣것이 앞엣것을 덮어써 스킬이 소실됐다."""
        manifest = {
            "dup": {"repo": "android-skills", "path": "a/dup/SKILL.md", "sha": "x"},
            "android-dup": {"repo": "android-skills", "path": "b/dup/SKILL.md", "sha": "x"},
        }
        taken = vendor._taken_by_manifest(manifest)
        seen = {}
        leaves = [vendor._resolve_leaf(md, "android-skills", seen, taken)
                  for md in ("a/dup/SKILL.md", "b/dup/SKILL.md")]
        assert leaves == ["dup", "android-dup"]


class TestSecondaryCollision:
    """I3: 접두사를 붙인 이름이 또 점유돼 있으면 계속 회피해야 한다."""

    def test_full_경로의_2차_충돌(self, skills_dir):
        (skills_dir / "shared").mkdir()          # 자작 스킬
        (skills_dir / "beta-shared").mkdir()     # 역시 자작 스킬
        taken = vendor._taken_after_prune(set())
        got = vendor._resolve_leaf("skills/shared/SKILL.md", "beta-skills", {}, taken)
        assert got == "beta-beta-shared"
        assert (skills_dir / "shared").is_dir() and (skills_dir / "beta-shared").is_dir()

    def test_update_경로의_2차_충돌(self, skills_dir):
        (skills_dir / "shared").mkdir()
        (skills_dir / "beta-shared").mkdir()
        taken = vendor._taken_by_manifest({})
        assert vendor._resolve_leaf("skills/shared/SKILL.md", "beta-skills", {}, taken) == "beta-beta-shared"

    def test_같은_접두사를_쓰는_두_repo가_섞여도_서로를_덮지_않는다(self, skills_dir):
        """android-skills와 android-testing-skills는 접두사가 둘 다 'android'다."""
        seen = {}
        taken = vendor._taken_after_prune(set())
        a = vendor._resolve_leaf("x/styles/SKILL.md", "android-skills", seen, taken)
        b = vendor._resolve_leaf("y/styles/SKILL.md", "android-testing-skills", seen, taken)
        assert (a, b) == ("styles", "android-styles")
        c = vendor._resolve_leaf("z/styles/SKILL.md", "android-testing-skills", seen, taken)
        assert c == "android-android-styles"
        assert len({a, b, c}) == 3

    def test_회피_불가능하면_무한_루프_대신_예외(self, skills_dir, monkeypatch):
        monkeypatch.setattr(vendor, "MAX_PREFIX_RETRY", 5)
        with pytest.raises(RuntimeError):
            vendor._resolve_leaf("a/x/SKILL.md", "beta-skills", {}, lambda leaf, repo: True)


class TestLoadPriorManifest:
    def test_파일_없으면_빈_딕셔너리(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vendor, "MANIFEST_JSON", tmp_path / "manifest.json")
        assert vendor._load_prior_manifest() == {}

    def test_있으면_읽는다(self, tmp_path, monkeypatch):
        p = tmp_path / "manifest.json"
        p.write_text('{"styles": {"repo": "android-skills"}}', encoding="utf-8")
        monkeypatch.setattr(vendor, "MANIFEST_JSON", p)
        assert vendor._load_prior_manifest()["styles"]["repo"] == "android-skills"


# --- C1/I2: 디스크 정리와 delta 갱신을 네트워크 없이 검증한다 --------------------


@pytest.fixture
def env(tmp_path, monkeypatch):
    """SKILLS_DIR·VENDOR_DIR을 tmp_path로 갈아끼우고 sync_cache/discover를 가짜 upstream에 붙인다."""
    skills = tmp_path / ".claude" / "skills"
    vend = tmp_path / ".claude" / "skills-vendor"
    upstream = tmp_path / "upstream"
    skills.mkdir(parents=True)
    vend.mkdir(parents=True)
    for name, path in [("SKILLS_DIR", skills), ("VENDOR_DIR", vend),
                       ("SOURCES", vend / "sources.json"),
                       ("BASELINE_JSON", vend / "baseline.json"),
                       ("MANIFEST_JSON", vend / "manifest.json"),
                       ("LICENSES", vend / "licenses"),
                       ("CACHE", tmp_path / "cache")]:
        monkeypatch.setattr(vendor, name, path)

    shas = {}

    def write_skill(repo, rel, body):
        d = upstream / repo / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\nname: x\ndescription: {body}\n---\n", encoding="utf-8")
        shas[repo] = shas.get(repo, 0) + 1

    def set_sources(*names):
        (vend / "sources.json").write_text(
            json.dumps({"repos": [{"name": n, "url": f"https://example.invalid/{n}.git"} for n in names]}),
            encoding="utf-8")

    def fake_sync(repo):
        return upstream / repo["name"], "main", f"sha-{repo['name']}-{shas.get(repo['name'], 0)}"

    monkeypatch.setattr(vendor, "sync_cache", fake_sync)
    monkeypatch.setattr(vendor, "discover", lambda cache, ref: sorted(
        str(p.parent.relative_to(cache) / "SKILL.md") for p in cache.rglob("SKILL.md")))
    monkeypatch.setattr(vendor, "run", lambda cmd, cwd=None: "changed\n")

    def leaves():
        return sorted(p.name for p in skills.iterdir() if p.is_dir())

    return type("Env", (), {
        "skills": skills, "vendor_dir": vend, "upstream": upstream,
        "write_skill": staticmethod(write_skill), "set_sources": staticmethod(set_sources),
        "leaves": staticmethod(leaves),
        "manifest": staticmethod(lambda: json.loads((vend / "manifest.json").read_text())),
        "bump": staticmethod(lambda repo: shas.__setitem__(repo, shas.get(repo, 0) + 1)),
    })()


class TestFullVendorPrune:
    def test_C1a_중간_실패_후_재실행해도_접두사가_붙지_않는다(self, env, monkeypatch):
        env.set_sources("alpha-skills", "beta-skills")
        env.write_skill("alpha-skills", "skills/one", "a")
        env.write_skill("alpha-skills", "skills/shared", "a")
        env.write_skill("beta-skills", "skills/one", "b")
        (env.skills / "graphify").mkdir()        # 자작 스킬

        real_copy = vendor.copy_skill

        def flaky(cache, md, leaf):
            if cache.name == "beta-skills":
                raise RuntimeError("복사 중 실패")
            real_copy(cache, md, leaf)

        monkeypatch.setattr(vendor, "copy_skill", flaky)
        with pytest.raises(RuntimeError):
            vendor.full_vendor()
        assert env.manifest()                     # repo 단위 증분 기록이 남았다

        monkeypatch.setattr(vendor, "copy_skill", real_copy)
        _, manifest, renamed = vendor.full_vendor()
        assert env.leaves() == ["beta-one", "graphify", "one", "shared"]
        assert sorted(manifest) == ["beta-one", "one", "shared"]
        assert renamed == [("one", "beta-one", "beta-skills")]

    @staticmethod
    def _flaky_copy(monkeypatch, fail_on):
        """leaf `fail_on`을 복사할 때만 죽는 copy_skill. repo 경계가 아니라 repo 내부에서 끊긴다."""
        real = vendor.copy_skill

        def flaky(cache, md, leaf):
            if leaf == fail_on:
                raise RuntimeError(f"복사 중 실패: {leaf}")
            real(cache, md, leaf)

        monkeypatch.setattr(vendor, "copy_skill", flaky)
        return real

    def test_C1d_repo_내부_중단_후_재실행해도_고아와_접두사가_남지_않는다(self, env, monkeypatch):
        """증분 기록이 절삭이면 이미 복사한 디렉토리가 기록에서 빠져 영구 고아가 된다."""
        env.set_sources("alpha-skills", "beta-skills")
        for repo, rel in [("alpha-skills", "skills/one"), ("alpha-skills", "skills/two"),
                          ("beta-skills", "skills/three"), ("beta-skills", "skills/four")]:
            env.write_skill(repo, rel, "v1")
        vendor.full_vendor()
        assert env.leaves() == ["four", "one", "three", "two"]

        real = self._flaky_copy(monkeypatch, "three")   # beta의 four를 복사한 뒤 three에서 죽는다
        with pytest.raises(RuntimeError):
            vendor.full_vendor()
        assert env.leaves() == ["four", "one", "two"]
        assert set(env.leaves()) <= set(env.manifest())   # 기록이 디스크를 덮는다

        monkeypatch.setattr(vendor, "copy_skill", real)
        _, manifest, renamed = vendor.full_vendor()
        assert env.leaves() == ["four", "one", "three", "two"]
        assert sorted(manifest) == ["four", "one", "three", "two"]
        assert renamed == []

        vendor.full_vendor()                              # 한 번 더 돌려도 그대로다
        assert env.leaves() == ["four", "one", "three", "two"]

    def test_C1e_중단_직전에_복사한_새_스킬도_기록된다(self, env, monkeypatch):
        """이전 manifest에 없던 이름이라 시드로는 못 덮는다 — 복사 전 기록이 필요하다."""
        env.set_sources("alpha-skills", "beta-skills")
        env.write_skill("alpha-skills", "skills/one", "v1")
        env.write_skill("beta-skills", "skills/three", "v1")
        vendor.full_vendor()

        env.write_skill("beta-skills", "skills/four", "새 스킬")
        real = self._flaky_copy(monkeypatch, "three")
        with pytest.raises(RuntimeError):
            vendor.full_vendor()
        assert "four" in env.manifest()

        monkeypatch.setattr(vendor, "copy_skill", real)
        _, manifest, renamed = vendor.full_vendor()
        assert env.leaves() == ["four", "one", "three"]
        assert sorted(manifest) == ["four", "one", "three"]
        assert renamed == []

    def test_C1f_중단_시_미처리_repo의_baseline이_보존된다(self, env, monkeypatch):
        """baseline이 절삭되면 이어서 도는 --update가 미처리 repo 전체를 added로 재분류한다."""
        env.set_sources("alpha-skills", "beta-skills")
        env.write_skill("alpha-skills", "skills/one", "v1")
        env.write_skill("beta-skills", "skills/three", "v1")
        env.write_skill("beta-skills", "skills/four", "v1")
        vendor.full_vendor()

        self._flaky_copy(monkeypatch, "three")
        with pytest.raises(RuntimeError):
            vendor.full_vendor()
        baseline = json.loads((env.vendor_dir / "baseline.json").read_text())
        assert sorted(baseline) == ["alpha-skills", "beta-skills"]
        assert vendor.update(dry=True)["added"] == []

    def test_C1g_시드가_sources에서_뺀_repo를_되살리지_않는다(self, env, monkeypatch):
        """"아직 처리 안 한 repo"와 "이번 sources.json에 없는 repo"는 다르다."""
        env.set_sources("alpha-skills", "beta-skills")
        env.write_skill("alpha-skills", "skills/one", "v1")
        env.write_skill("alpha-skills", "skills/two", "v1")
        env.write_skill("beta-skills", "skills/three", "v1")
        vendor.full_vendor()

        env.set_sources("alpha-skills")                 # beta를 뺀다
        self._flaky_copy(monkeypatch, "two")            # alpha 내부에서 죽는다
        with pytest.raises(RuntimeError):
            vendor.full_vendor()
        manifest = env.manifest()
        assert [leaf for leaf, i in manifest.items() if i["repo"] == "beta-skills"] == []
        assert "three" not in manifest
        assert "beta-skills" not in json.loads((env.vendor_dir / "baseline.json").read_text())

    def test_C1b_upstream이_지운_스킬은_디스크에서도_사라진다(self, env):
        env.set_sources("alpha-skills")
        env.write_skill("alpha-skills", "skills/one", "a")
        env.write_skill("alpha-skills", "skills/two", "a")
        vendor.full_vendor()
        assert env.leaves() == ["one", "two"]

        import shutil as _sh
        _sh.rmtree(env.upstream / "alpha-skills" / "skills" / "two")
        env.bump("alpha-skills")
        vendor.full_vendor()
        assert env.leaves() == ["one"]
        assert sorted(env.manifest()) == ["one"]

    def test_C1c_sources에서_뺀_repo의_스킬이_남지_않는다(self, env):
        env.set_sources("alpha-skills", "beta-skills")
        env.write_skill("alpha-skills", "skills/one", "a")
        env.write_skill("beta-skills", "skills/two", "b")
        vendor.full_vendor()
        assert env.leaves() == ["one", "two"]

        env.set_sources("alpha-skills")
        vendor.full_vendor()
        assert env.leaves() == ["one"]

        env.set_sources("alpha-skills", "beta-skills")   # 되돌려도 이중 접두사가 생기지 않는다
        vendor.full_vendor()
        assert env.leaves() == ["one", "two"]

    def test_자작_스킬은_prune에도_full에도_살아남는다(self, env):
        env.set_sources("alpha-skills")
        env.write_skill("alpha-skills", "skills/graphify", "a")
        (env.skills / "graphify").mkdir()
        (env.skills / "graphify" / "SKILL.md").write_text("자작", encoding="utf-8")
        vendor.full_vendor()
        vendor.full_vendor()
        assert env.leaves() == ["alpha-graphify", "graphify"]
        assert (env.skills / "graphify" / "SKILL.md").read_text(encoding="utf-8") == "자작"

    def test_dry_run은_아무것도_지우지_않는다(self, env):
        env.set_sources("alpha-skills")
        env.write_skill("alpha-skills", "skills/one", "a")
        vendor.full_vendor()
        before = env.leaves()
        import shutil as _sh
        _sh.rmtree(env.upstream / "alpha-skills" / "skills" / "one")
        env.bump("alpha-skills")
        _, manifest, _ = vendor.full_vendor(dry=True)
        assert env.leaves() == before == ["one"]
        assert manifest == {}
        assert sorted(env.manifest()) == ["one"]


class TestUpdateDuplicateBasename:
    def test_I2_같은_repo_안의_중복_basename이_rmtree되지_않는다(self, env):
        env.set_sources("alpha-skills")
        env.write_skill("alpha-skills", "a/dup", "A판")
        env.write_skill("alpha-skills", "b/dup", "B판")
        vendor.full_vendor()
        assert env.leaves() == ["alpha-dup", "dup"]

        env.write_skill("alpha-skills", "a/dup", "A판-수정")   # sha가 올라 update가 돈다
        changes = vendor.update()
        assert changes["deleted"] == []
        assert env.leaves() == ["alpha-dup", "dup"]
        assert (env.skills / "dup" / "SKILL.md").read_text(encoding="utf-8").find("A판-수정") > 0
        assert (env.skills / "alpha-dup" / "SKILL.md").read_text(encoding="utf-8").find("B판") > 0

    def test_update가_자작_스킬을_침범하지_않는다(self, env):
        env.set_sources("alpha-skills")
        env.write_skill("alpha-skills", "skills/one", "a")
        vendor.full_vendor()
        (env.skills / "graphify").mkdir()
        (env.skills / "graphify" / "SKILL.md").write_text("자작", encoding="utf-8")

        env.write_skill("alpha-skills", "skills/graphify", "새 벤더 스킬")
        changes = vendor.update()
        assert "alpha-graphify" in changes["added"]
        assert changes["renamed"] == [("graphify", "alpha-graphify", "alpha-skills")]
        assert (env.skills / "graphify" / "SKILL.md").read_text(encoding="utf-8") == "자작"


class TestUpdateOnFreshClone:
    """벤더한 적 없는 새 클론에서 --update가 죽지 않는다.

    공개 템플릿의 기본 상태가 이것이다 — sources.json만 있고 baseline·manifest는
    아직 생성되지 않았다. 직접 read_text()로 읽으면 FileNotFoundError 트레이스백이
    난다. 스킬 문서가 "소스 repo 추가는 sources.json에 넣고 --update"라고 안내하므로
    첫 사용자가 정확히 이 경로를 밟는다.
    """

    def test_baseline과_manifest가_없어도_돈다(self, env):
        env.set_sources("alpha-skills")
        env.write_skill("alpha-skills", "skills/one", "a")
        assert not (env.vendor_dir / "baseline.json").exists()
        assert not (env.vendor_dir / "manifest.json").exists()

        changes = vendor.update()

        assert changes["added"] == ["one"]      # 빈 baseline이면 전량 add가 맞는 판정이다
        assert env.leaves() == ["one"]

    def test_소스가_비어_있어도_돈다(self, env):
        env.set_sources()
        changes = vendor.update()
        assert changes == {"added": [], "modified": [], "deleted": [], "renamed": []}
