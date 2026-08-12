import pytest

import search


def _mk(root, name, desc):
    d = root / name
    d.mkdir()
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\n", encoding="utf-8"
    )


class TestScore:
    def test_이름_가중치가_description을_이긴다(self):
        s_name = {"name": "recomposition-debug", "desc": "misc", "headings": ""}
        s_desc = {"name": "misc", "desc": "recomposition tuning", "headings": ""}
        assert search.score("recomposition", s_name) > search.score("recomposition", s_desc)

    def test_매칭_없으면_0점(self):
        assert search.score("xyz", {"name": "a", "desc": "b", "headings": ""}) == 0.0

    def test_빈_쿼리는_0점(self):
        assert search.score("", {"name": "a", "desc": "b", "headings": ""}) == 0.0


class TestSearch:
    @pytest.fixture
    def skills_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(search, "SKILLS_DIR", tmp_path)
        return tmp_path

    def test_관련_스킬이_1위(self, skills_dir):
        _mk(skills_dir, "stability-diagnostics", "diagnose compose stability")
        _mk(skills_dir, "navigation-3", "set up navigation")
        res = search.search("compose stability", top=5)
        assert res[0][1]["name"] == "stability-diagnostics"

    def test_SKILL_md_없는_디렉토리는_건너뛴다(self, skills_dir):
        _mk(skills_dir, "real-skill", "compose stability")
        (skills_dir / "empty-dir").mkdir()
        res = search.search("compose", top=5)
        assert [s["name"] for _, s in res] == ["real-skill"]

    def test_0점은_결과에서_빠진다(self, skills_dir):
        _mk(skills_dir, "stability-diagnostics", "diagnose compose stability")
        _mk(skills_dir, "navigation-3", "set up navigation")
        res = search.search("stability", top=5)
        assert len(res) == 1


class TestTokenizeHangul:
    """I1: ASCII만 뽑던 tokenize가 한글 쿼리를 통째로 버렸다."""

    def test_한글_어절이_토큰으로_남는다(self):
        assert search.tokenize("위키 이슈 동기화") == ["위키", "이슈", "동기화"]

    def test_영문과_한글이_섞이면_둘_다_토큰(self):
        assert search.tokenize("벤더 스킬 갱신 update") == ["벤더", "스킬", "갱신", "update"]

    def test_영문_토큰화는_그대로다(self):
        assert search.tokenize("Compose-Stability 3") == ["compose", "stability", "3"]


class TestHangulSearch:
    @pytest.fixture
    def skills_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(search, "SKILLS_DIR", tmp_path)
        return tmp_path

    def test_순한글_쿼리도_결과를_돌려준다(self, skills_dir):
        _mk(skills_dir, "wiki-issue-sync", "위키 이슈 동기화를 수행한다")
        _mk(skills_dir, "navigation-3", "set up navigation")
        res = search.search("위키 이슈 동기화", top=5)
        assert [s["name"] for _, s in res] == ["wiki-issue-sync"]

    def test_혼합_쿼리는_한글_토큰도_센다(self, skills_dir):
        _mk(skills_dir, "update-injected-skills", "벤더 스킬 갱신. update로 delta만 재벤더한다")
        _mk(skills_dir, "graphify", "update update update graph")
        res = search.search("벤더 스킬 갱신 update", top=5)
        assert res[0][1]["name"] == "update-injected-skills"

    def test_한글_description만_있어도_0점이_아니다(self, skills_dir):
        _mk(skills_dir, "korean-only", "한국어 설명만 있는 스킬")
        assert search.score("한국어", search.parse_skill(skills_dir / "korean-only" / "SKILL.md")) > 0
