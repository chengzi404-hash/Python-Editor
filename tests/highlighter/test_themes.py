"""Tests for the highlight theme registry."""

from core.language.highlighter import highlight_themes


class TestBuiltinThemes:
    def test_default_dark_has_italic_comment(self):
        tokens = highlight_themes.tokens("Default Dark")
        assert tokens["comment"].get("italic") is True

    def test_default_dark_has_bold_log_levels(self):
        tokens = highlight_themes.tokens("Default Dark")
        for name in ("level_warn", "level_error", "level_critical"):
            assert tokens[name].get("bold") is True, f"{name} should be bold"

    def test_default_light_has_italic_comment(self):
        tokens = highlight_themes.tokens("Default Light")
        assert tokens["comment"].get("italic") is True

    def test_solarized_dark_has_italic_comment(self):
        tokens = highlight_themes.tokens("Solarized Dark")
        assert tokens["comment"].get("italic") is True

    def test_all_themes_expose_expected_keys(self):
        names = highlight_themes.available_names()
        assert {"Default Dark", "Default Light", "Solarized Dark"}.issubset(set(names))

    def test_bold_and_italic_are_optional(self):
        tokens = highlight_themes.tokens("Default Dark")
        assert tokens["keyword"].get("bold", False) is False
        assert tokens["keyword"].get("italic", False) is False
        assert tokens["string"].get("bold", False) is False
