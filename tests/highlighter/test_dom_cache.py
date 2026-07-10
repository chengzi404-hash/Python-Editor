"""Tests for ``modules.highlighter.dom_cache``."""

from __future__ import annotations

import os
import pytest

from modules.highlighter.dom_cache import (
    LibraryDOM,
    ensure_lib_cache,
    get_lib_dom,
    get_or_load_lib_dom,
    cache_exists,
    invalidate_lib_cache,
    _cache_file,
    build_full_cache,
)


class TestLibraryDOM:
    def test_library_dom_creation(self) -> None:
        dom = LibraryDOM(
            name="test_lib",
            version="1.0.0",
            classes=["MyClass"],
            functions=["my_func"],
            submodules=["submod"],
            submodule_contents={"submod": {"classes": [], "functions": []}},
        )
        assert dom.name == "test_lib"
        assert dom.version == "1.0.0"
        assert dom.classes == ["MyClass"]
        assert dom.functions == ["my_func"]
        assert dom.submodules == ["submod"]


class TestCacheOperations:
    def test_cache_file_path(self) -> None:
        path = _cache_file("os")
        assert "os.json" in path

    def test_cache_file_path_dotted_name(self) -> None:
        """Dotted names are flattened in cache filenames."""
        path = _cache_file("my_package.sub")
        assert "my_package_sub.json" in path

    def test_cache_exists_nonexistent(self) -> None:
        """Returns False for a package never cached."""
        assert cache_exists("this_package_does_not_exist_12345") is False

    def test_get_lib_dom_nonexistent(self) -> None:
        """Returns None when no cache exists."""
        result = get_lib_dom("nonexistent_package_xyz_123")
        assert result is None

    def test_ensure_then_get(self) -> None:
        """ensure_lib_cache + get_lib_dom roundtrip."""
        lib_name = "os"
        invalidate_lib_cache(lib_name)  # clean slate

        dom = ensure_lib_cache(lib_name)
        assert dom is not None
        assert dom.name == lib_name
        assert isinstance(dom.classes, list)
        assert isinstance(dom.functions, list)
        assert isinstance(dom.submodules, list)

        # get_lib_dom should retrieve the same data
        cached = get_lib_dom(lib_name)
        assert cached is not None
        assert cached.name == dom.name

    def test_get_or_load_lib_dom_caches(self) -> None:
        """get_or_load_lib_dom should create cache if missing."""
        lib_name = "collections"
        invalidate_lib_cache(lib_name)

        # Should not exist yet
        assert cache_exists(lib_name) is False

        dom = get_or_load_lib_dom(lib_name)
        assert dom is not None
        assert dom.name == lib_name
        assert cache_exists(lib_name) is True

    def test_invalidate(self) -> None:
        """invalidate_lib_cache removes the cache file."""
        lib_name = "os"
        ensure_lib_cache(lib_name)
        assert cache_exists(lib_name) is True

        invalidate_lib_cache(lib_name)
        assert cache_exists(lib_name) is False

        # get_lib_dom should return None after invalidation
        assert get_lib_dom(lib_name) is None


class TestDOMContent:
    def test_os_dom_has_expected_structure(self) -> None:
        """The 'os' module should have some known classes/functions."""
        dom = ensure_lib_cache("os")
        assert dom is not None

        # os should expose some functions and classes
        assert len(dom.functions) > 0
        assert len(dom.classes) > 0

    def test_collections_dom(self) -> None:
        """collections module should expose Counter, OrderedDict, etc."""
        dom = ensure_lib_cache("collections")
        assert dom is not None

        # OrderedDict and Counter are commonly-used classes
        assert "Counter" in dom.classes or "OrderedDict" in dom.classes


class TestBuildFullCache:
    def test_build_full_cache_returns_count(self) -> None:
        """build_full_cache should return a non-negative integer."""
        count = build_full_cache()
        assert isinstance(count, int)
        assert count >= 0

    def test_build_full_cache_progress_callback(self) -> None:
        """Progress callback is called with (current, total)."""
        progress_calls: list[tuple[int, int]] = []

        def callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        build_full_cache(progress_callback=callback)
        if progress_calls:
            # Each call should have current <= total
            for curr, tot in progress_calls:
                assert 1 <= curr <= tot
