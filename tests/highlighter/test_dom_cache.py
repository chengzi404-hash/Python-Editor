import pytest

from modules.highlighter.dom_cache import LibraryDOM, cache_exists, get_lib_dom


class TestLibraryDOM:
    def test_creation(self):
        dom = LibraryDOM(name="os", version="1.0")
        assert dom.name == "os"
        assert dom.version == "1.0"
        assert dom.classes == []
        assert dom.functions == []
        assert dom.submodules == []

    def test_with_data(self):
        dom = LibraryDOM(
            name="test",
            version="1.0",
            classes=["ClassA", "ClassB"],
            functions=["func1", "func2"],
            submodules=["sub1", "sub2"]
        )
        assert len(dom.classes) == 2
        assert len(dom.functions) == 2
        assert len(dom.submodules) == 2


class TestDomCache:
    def test_cache_exists_false_for_unknown(self):
        assert not cache_exists("nonexistent_library_xyz123")

    def test_get_lib_dom_none_for_unknown(self):
        result = get_lib_dom("nonexistent_library_xyz123")
        assert result is None
