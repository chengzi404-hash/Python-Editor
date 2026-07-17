import pytest

from core.language.suggestion import (
    BUILTIN_CLASSES,
    BUILTIN_FUNCTIONS,
    KEYWORDS,
    PythonSuggestionExpert,
    SuggestionBlock,
    SuggestionItem,
)
from core.language.suggestion.python import _adjust_underscore_priority, _load_suggestion_list


class TestPythonSuggestionExpert:
    def test_init(self):
        expert = PythonSuggestionExpert()
        assert expert is not None

    def test_init_with_lang(self):
        expert = PythonSuggestionExpert(lang="zh_CN")
        assert expert._lang == "zh_CN"

    def test_get_language_exts(self):
        expert = PythonSuggestionExpert()
        exts = expert.get_languange_exts()
        assert "py" in exts

    def test_suggest_empty_code(self):
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="", position=0)
        suggestions = expert.suggest(block)
        assert isinstance(suggestions, list)

    def test_suggest_with_keyword(self):
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="pr", position=2)
        suggestions = expert.suggest(block)
        labels = [s.label for s in suggestions]
        assert "print" in labels

    def test_suggest_with_builtin(self):
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="lis", position=3)
        suggestions = expert.suggest(block)
        labels = [s.label for s in suggestions]
        assert "list" in labels

    def test_suggest_prefix_filter(self):
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="pri", position=3)
        suggestions = expert.suggest(block)
        for s in suggestions:
            assert s.label.lower().startswith("pri")

    def test_iter_classes(self):
        expert = PythonSuggestionExpert()
        code = """
class MyClass:
    pass

class AnotherClass:
    pass
"""
        block = SuggestionBlock(code=code, position=0)
        classes = expert.iter_classes(block)
        assert "MyClass" in classes
        assert "AnotherClass" in classes

    def test_iter_function(self):
        expert = PythonSuggestionExpert()
        code = """
def my_function():
    pass

def another_function():
    pass
"""
        block = SuggestionBlock(code=code, position=0)
        functions = expert.iter_function(block)
        assert "my_function" in functions
        assert "another_function" in functions


class TestAdjustUnderscorePriority:
    def test_double_underscore(self):
        result = _adjust_underscore_priority("__test", 10)
        assert result == 30

    def test_single_underscore(self):
        result = _adjust_underscore_priority("_test", 10)
        assert result == 20

    def test_no_underscore(self):
        result = _adjust_underscore_priority("test", 10)
        assert result == 10


class TestExportedSets:
    def test_keywords_not_empty(self):
        assert len(KEYWORDS) > 0

    def test_builtin_functions_not_empty(self):
        assert len(BUILTIN_FUNCTIONS) > 0

    def test_builtin_classes_not_empty(self):
        assert len(BUILTIN_CLASSES) > 0

    def test_print_in_builtins(self):
        assert "print" in BUILTIN_FUNCTIONS

    def test_len_in_builtins(self):
        assert "len" in BUILTIN_FUNCTIONS
