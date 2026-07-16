import pytest

from modules.suggestion.c import CSuggestionExpert, SuggestionBlock


class TestCSuggestionExpert:
    def test_init(self):
        expert = CSuggestionExpert()
        assert expert is not None

    def test_init_with_lang(self):
        expert = CSuggestionExpert(lang="zh_CN")
        assert expert._lang == "zh_CN"

    def test_get_language_exts(self):
        expert = CSuggestionExpert()
        exts = expert.get_languange_exts()
        assert "c" in exts
        assert "h" in exts

    def test_suggest_empty_code(self):
        expert = CSuggestionExpert()
        block = SuggestionBlock(code="", position=0)
        suggestions = expert.suggest(block)
        assert isinstance(suggestions, list)

    def test_suggest_with_keyword(self):
        expert = CSuggestionExpert()
        block = SuggestionBlock(code="in", position=2)
        suggestions = expert.suggest(block)
        labels = [s.label for s in suggestions]
        assert "int" in labels

    def test_suggest_with_preprocessor(self):
        expert = CSuggestionExpert()
        block = SuggestionBlock(code="#", position=1)
        suggestions = expert.suggest(block)
        labels = [s.label for s in suggestions]
        assert "#include" in labels

    def test_suggest_prefix_filter(self):
        expert = CSuggestionExpert()
        block = SuggestionBlock(code="pri", position=3)
        suggestions = expert.suggest(block)
        for s in suggestions:
            assert s.label.lower().startswith("pri")

    def test_iter_classes(self):
        CSuggestionExpert()
        code = """
struct MyStruct {
    int x;
};

struct AnotherStruct {
    int y;
};
"""
        SuggestionBlock(code=code, position=0)
        classes = []
        for _, _, kind, name, _ in CSuggestionExpert._collect_entries(code):
            if kind in ("class", "typedef"):
                classes.append(name)
        assert "MyStruct" in classes
        assert "AnotherStruct" in classes

    def test_iter_functions(self):
        CSuggestionExpert()
        code = """
int my_function() {
    return 0;
}

void another_function() {
}
"""
        SuggestionBlock(code=code, position=0)
        functions = []
        for _, _, kind, name, _ in CSuggestionExpert._collect_entries(code):
            if kind == "function":
                functions.append(name)
        assert "my_function" in functions
        assert "another_function" in functions
