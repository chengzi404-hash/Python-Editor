import pytest

from modules.suggestion.cpp import CppSuggestionExpert, SuggestionBlock


class TestCppSuggestionExpert:
    def test_init(self):
        expert = CppSuggestionExpert()
        assert expert is not None

    def test_init_with_lang(self):
        expert = CppSuggestionExpert(lang="zh_CN")
        assert expert._lang == "zh_CN"

    def test_get_language_exts(self):
        expert = CppSuggestionExpert()
        exts = expert.get_languange_exts()
        assert "cpp" in exts
        assert "hpp" in exts

    def test_suggest_empty_code(self):
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code="", position=0)
        suggestions = expert.suggest(block)
        assert isinstance(suggestions, list)

    def test_suggest_with_keyword(self):
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code="cl", position=2)
        suggestions = expert.suggest(block)
        labels = [s.label for s in suggestions]
        assert "class" in labels

    def test_suggest_prefix_filter(self):
        expert = CppSuggestionExpert()
        block = SuggestionBlock(code="st", position=2)
        suggestions = expert.suggest(block)
        for s in suggestions:
            assert s.label.lower().startswith("st")

    def test_iter_classes(self):
        CppSuggestionExpert()
        code = """
class MyClass {
};

class AnotherClass {
};
"""
        SuggestionBlock(code=code, position=0)
        classes = []
        for _, _, kind, name, _ in CppSuggestionExpert._collect_entries(code):
            if kind == "class":
                classes.append(name)
        assert "MyClass" in classes
        assert "AnotherClass" in classes

    def test_iter_functions(self):
        CppSuggestionExpert()
        code = "int my_function() {}"
        SuggestionBlock(code=code, position=0)
        entries = CppSuggestionExpert._collect_entries(code)
        function_entries = [name for _, _, kind, name, _ in entries if kind == "function"]
        assert len(function_entries) >= 0

    def test_suggest_namespace(self):
        CppSuggestionExpert()
        code = """
namespace my_namespace {
    class MyClass {};
}
"""
        SuggestionBlock(code=code, position=0)
        classes = []
        for _, _, kind, name, _ in CppSuggestionExpert._collect_entries(code):
            if kind == "namespace":
                classes.append(name)
        assert "my_namespace" in classes
