"""Tests for the ghost-text / inline-completion helpers in app.py.

We don't instantiate the full :class:`CodeEditor` (it builds a Tk window and
runs the full plugin/skill subsystem). Instead we exercise the pure helpers
directly — they are the load-bearing logic for the feature.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.editor.app import (
    _NAVIGATION_KEYS,
    _pick_local_completion,
    _strip_common_prefix,
)


@dataclass
class _Item:
    label: str
    insert: str = ""
    priority: int = 100


class _FakeExpert:
    def __init__(self, items: list[_Item]) -> None:
        self._items = items

    def suggest(self, _block):
        return self._items


class TestStripCommonPrefix:
    def test_strips_matching_prefix(self):
        assert _strip_common_prefix("hello", "hel") == "lo"

    def test_returns_unchanged_when_no_match(self):
        assert _strip_common_prefix("hello", "foo") == "hello"

    def test_empty_partial_returns_full(self):
        assert _strip_common_prefix("hello", "") == "hello"

    def test_full_match_returns_empty(self):
        assert _strip_common_prefix("hello", "hello") == ""


class TestPickLocalCompletion:
    def test_no_expert(self):
        assert _pick_local_completion(None, code="x", position=0, partial="") is None

    def test_no_partial_returns_none_to_avoid_noise(self):
        # We deliberately do NOT show ghost text when the user has not typed a
        # token prefix — otherwise the overlay would appear immediately on
        # every cursor move.
        expert = _FakeExpert([_Item("hello")])
        assert _pick_local_completion(expert, code="", position=0, partial="") is None

    def test_partial_matches_label(self):
        expert = _FakeExpert([_Item("hello"), _Item("help")])
        # Best match is whichever comes first in the list — both start with 'hel'.
        # Either 'lo' (from hello) or 'p' (from help) is acceptable.
        result = _pick_local_completion(expert, code="hel", position=3, partial="hel")
        assert result in ("lo", "p")

    def test_partial_does_not_match_returns_none(self):
        expert = _FakeExpert([_Item("apple"), _Item("banana")])
        assert _pick_local_completion(expert, code="xyz", position=3, partial="xyz") is None

    def test_partial_skips_empty_label_items(self):
        expert = _FakeExpert([_Item(""), _Item("hello")])
        result = _pick_local_completion(expert, code="hel", position=3, partial="hel")
        assert result == "lo"


class TestNavigationKeys:
    def test_navigation_keys_contains_expected(self):
        assert "Up" in _NAVIGATION_KEYS
        assert "Down" in _NAVIGATION_KEYS
        assert "Left" in _NAVIGATION_KEYS
        assert "Right" in _NAVIGATION_KEYS
        assert "Tab" in _NAVIGATION_KEYS
        assert "Escape" in _NAVIGATION_KEYS

    def test_printable_keys_not_in_navigation(self):
        assert "a" not in _NAVIGATION_KEYS
        assert "space" not in _NAVIGATION_KEYS
        assert "Return" not in _NAVIGATION_KEYS
