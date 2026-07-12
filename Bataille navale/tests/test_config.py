import battleship.config as config

# NICKNAMES is loaded from a private, gitignored file (see private/nicknames.example.json),
# so tests monkeypatch it with synthetic data instead of asserting on real personal content.


def test_resolve_nickname_matches_a_known_name(monkeypatch):
    monkeypatch.setattr(config, "NICKNAMES", {"alice": "Queen Alice"})
    assert config.resolve_nickname("Alice") == "Queen Alice"


def test_resolve_nickname_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(config, "NICKNAMES", {"bob": "Sir Bob"})
    assert config.resolve_nickname("bOB") == "Sir Bob"


def test_resolve_nickname_does_not_match_substrings(monkeypatch):
    monkeypatch.setattr(config, "NICKNAMES", {"al": "Short Al"})
    assert config.resolve_nickname("Alice") == "Alice"


def test_resolve_nickname_passes_through_unknown_names_unchanged(monkeypatch):
    monkeypatch.setattr(config, "NICKNAMES", {})
    assert config.resolve_nickname("Arnaud") == "Arnaud"


def test_resolve_nickname_strips_whitespace(monkeypatch):
    monkeypatch.setattr(config, "NICKNAMES", {"alice": "Queen Alice"})
    assert config.resolve_nickname("  Alice  ") == "Queen Alice"


def test_load_nicknames_returns_empty_dict_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "_NICKNAMES_PATH", tmp_path / "missing.json")
    assert config._load_nicknames() == {}


def test_load_nicknames_reads_json_file(monkeypatch, tmp_path):
    path = tmp_path / "nicknames.json"
    path.write_text('{"zoe": "Cosmic Zoe"}', encoding="utf-8")
    monkeypatch.setattr(config, "_NICKNAMES_PATH", path)
    assert config._load_nicknames() == {"zoe": "Cosmic Zoe"}
