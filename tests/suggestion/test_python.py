"""针对 ``modules.suggestion.python.PythonSuggestionExpert`` 的测试。

按 ``API_DOCS.md`` 描述覆盖:

* 基础接口(扩展名、迭代 class/function 名、``find_domin``)
* 标识符补全:关键字、内建名、作用域内变量/函数/类、前缀过滤
* 属性补全:``self.``、内建类型属性、其他对象通用 dunder
* 内置常量集合(BUILTIN_FUNCTIONS / BUILTIN_CLASSES / BUILTIN_PROPERTIES /
  KEYWORDS / BUILTIN_ATTRS)
* ``_extract_variables`` 的正则提取
"""

from __future__ import annotations

import pytest

from modules.suggestion.base import SuggestionBlock
from modules.suggestion.python import (
    BUILTIN_ATTRS,
    BUILTIN_CLASSES,
    BUILTIN_FUNCTIONS,
    BUILTIN_PROPERTIES,
    KEYWORDS,
    PythonSuggestionExpert,
)




class TestBasicInterface:
    def test_get_languange_exts(self) -> None:
        expert = PythonSuggestionExpert()
        assert expert.get_languange_exts() == ["py"]

    def test_suggest_returns_list(self) -> None:
        expert = PythonSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="x", position=1))
        assert isinstance(result, list)

    def test_suggest_is_sorted_and_unique(self) -> None:
        """返回结果应去重并按字母序排序。"""
        expert = PythonSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        assert result == sorted(set(result))




class TestIterClassesAndFunctions:
    def test_iter_classes_finds_all_classes(self) -> None:
        code = (
            "class A:\n"
            "    pass\n"
            "class B:\n"
            "    pass\n"
        )
        result = PythonSuggestionExpert.iter_classes(SuggestionBlock(code=code, position=0))
        assert result == ["A", "B"]

    def test_iter_classes_with_inheritance(self) -> None:
        code = "class Foo(Bar, Baz):\n    pass\n"
        result = PythonSuggestionExpert.iter_classes(SuggestionBlock(code=code, position=0))
        assert result == ["Foo"]

    def test_iter_function_finds_all_functions(self) -> None:
        code = (
            "def foo():\n"
            "    pass\n"
            "async def bar():\n"
            "    pass\n"
            "def baz():\n"
            "    pass\n"
        )
        result = PythonSuggestionExpert.iter_function(SuggestionBlock(code=code, position=0))
        assert result == ["foo", "bar", "baz"]

    def test_iter_classes_empty(self) -> None:
        result = PythonSuggestionExpert.iter_classes(SuggestionBlock(code="x = 1\n", position=0))
        assert result == []

    def test_iter_function_empty(self) -> None:
        result = PythonSuggestionExpert.iter_function(SuggestionBlock(code="x = 1\n", position=0))
        assert result == []




class TestFindDomin:
    def test_root_scope_when_no_definitions(self) -> None:
        """没有任何 class/def 时,返回的根作用域 ``begin=0``,``end`` 为行数。"""
        code = "x = 1\n"
        result = PythonSuggestionExpert.find_domin(
            SuggestionBlock(code=code, position=0), position=0
        )
        assert result.begin == 0
        assert result.end == code.count("\n") + 1
        assert result.subDOM == []

    def test_finds_top_level_class(self) -> None:
        code = "class A:\n    pass\nclass B:\n    pass\n"
        root = PythonSuggestionExpert.find_domin(
            SuggestionBlock(code=code, position=0), position=0
        )
        assert root.begin == 0

    def test_finds_inner_class_when_inside_it(self) -> None:
        code = (
            "class A:\n"          # line 0
            "    class B:\n"      # line 1
            "        pass\n"      # line 2
        )
        scope = PythonSuggestionExpert.find_domin(
            SuggestionBlock(code=code, position=0), position=1
        )
        assert scope.begin == 1




class TestIdentifierSuggestion:
    def test_includes_keywords(self) -> None:
        expert = PythonSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for kw in ("if", "else", "def", "class", "return"):
            assert kw in result, f"missing keyword: {kw}"

    def test_includes_builtin_functions(self) -> None:
        expert = PythonSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for name in ("print", "len", "isinstance", "open", "input"):
            assert name in result

    def test_includes_builtin_classes(self) -> None:
        expert = PythonSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for name in ("list", "dict", "str", "int", "bool"):
            assert name in result

    def test_includes_builtin_properties(self) -> None:
        expert = PythonSuggestionExpert()
        result = expert.suggest(SuggestionBlock(code="\n", position=0))
        for name in ("True", "False", "None", "__name__"):
            assert name in result

    def test_prefix_filter(self) -> None:
        """输入 ``pr`` 时,结果应以 ``pr`` 开头。"""
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="pr", position=2)
        result = expert.suggest(block)
        assert result, "expected non-empty suggestions"
        for s in result:
            assert s.startswith("pr"), f"unexpected suggestion: {s!r}"

    def test_prefix_filter_for_print(self) -> None:
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="pri", position=3)
        result = expert.suggest(block)
        assert "print" in result

    def test_no_match_returns_empty(self) -> None:
        """没有任何标识符以某个奇怪前缀开头时,应返回空列表。"""
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(code="zzq", position=3)
        result = expert.suggest(block)
        assert result == []

    def test_local_variables_are_suggested_with_prefix(self) -> None:
        """模块级赋值得到的变量,在以 ``my`` 为前缀时应在补全候选里。"""
        expert = PythonSuggestionExpert()
        block = SuggestionBlock(
            code="my_local_var = 1\nmy", position=len("my_local_var = 1\nmy")
        )
        result = expert.suggest(block)
        assert "my_local_var" in result

    def test_function_in_scope_is_suggested(self) -> None:
        expert = PythonSuggestionExpert()
        code = (
            "def helper():\n"
            "    return 1\n"
            "hel\n"
        )
        block = SuggestionBlock(code=code, position=len(code))
        result = expert.suggest(block)
        assert "helper" in result

    def test_class_in_scope_is_suggested(self) -> None:
        expert = PythonSuggestionExpert()
        code = (
            "class Greeter:\n"
            "    pass\n"
            "Gre\n"
        )
        block = SuggestionBlock(code=code, position=len(code))
        result = expert.suggest(block)
        assert "Greeter" in result

    def test_root_functions_visible_in_nested_scope(self) -> None:
        """root 作用域里定义的函数在嵌套作用域中仍是可见的。"""
        expert = PythonSuggestionExpert()
        code = (
            "def helper():\n"
            "    pass\n"
            "def runner():\n"
            "    \n"
        )
        block = SuggestionBlock(code=code, position=len(code))
        result = expert.suggest(block)
        assert "helper" in result
        assert "runner" in result




class TestAttributeSuggestion:
    def test_self_dot_suggests_class_methods(self) -> None:
        """光标在 ``self.`` 之后时,应列出所在类中定义的方法。"""
        expert = PythonSuggestionExpert()
        code = (
            "class Greeter:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n"
            "    def greet(self):\n"
            "        return self.\n"
        )
        pos = code.index("self.\n") + len("self.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert "greet" in result
        assert "__init__" in result

    def test_self_dot_outside_class_returns_generic_dunders(self) -> None:
        """光标 ``self.|`` 不在任何 class 内时,应回退到通用 dunder 列表。"""
        expert = PythonSuggestionExpert()
        code = "x = self.\n"
        pos = code.index("self.\n") + len("self.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert "__init__" in result
        assert "__class__" in result
        assert "greet" not in result

    def test_str_dot_returns_str_attributes(self) -> None:
        """``str.|`` 应给出 ``BUILTIN_ATTRS['str']`` 中的方法。"""
        expert = PythonSuggestionExpert()
        code = "x = str."
        pos = code.index("str.") + len("str.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for attr in ("upper", "lower", "split", "strip"):
            assert attr in result, f"missing attribute: {attr}"

    def test_unknown_typed_name_does_not_get_type_specific_attrs(self) -> None:
        """``lis.|`` (lis 不是已知内建类型)不应列出 list 专有属性。"""
        expert = PythonSuggestionExpert()
        code = "x = lis."
        pos = code.index("lis.") + len("lis.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert "append" not in result

    def test_int_dot_with_b_prefix(self) -> None:
        """``int.b|`` 应只返回以 ``b`` 开头的 int 属性。"""
        expert = PythonSuggestionExpert()
        code = "x = int.b"
        pos = code.index("int.b") + len("int.b")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        for s in result:
            assert s.startswith("b"), f"unexpected suggestion: {s!r}"
        assert "bit_length" in result
        assert "bit_count" in result

    def test_unknown_object_returns_generic_dunders(self) -> None:
        expert = PythonSuggestionExpert()
        code = "obj."
        pos = code.index("obj.") + len("obj.")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert "__init__" in result
        assert "__class__" in result

    def test_attribute_prefix_filter(self) -> None:
        """``str.up|`` 应只返回以 ``up`` 开头的 str 属性。"""
        expert = PythonSuggestionExpert()
        code = "x = str.up"
        pos = code.index("str.up") + len("str.up")
        block = SuggestionBlock(code=code, position=pos)
        result = expert.suggest(block)
        assert result == ["upper"]




class TestExtractVariables:
    """直接调用 ``_extract_variables`` 以验证其正则覆盖各种变量声明。"""

    def test_simple_assignment(self) -> None:
        vars_ = PythonSuggestionExpert._extract_variables("a = 1", 0, 1)
        assert "a" in vars_

    def test_tuple_assignment_not_supported(self) -> None:
        """当前 ``_extract_variables`` 的正则只覆盖 ``var = ...`` 形式,
        不支持 ``a, b = 1, 2`` 这样的元组解包。"""
        vars_ = PythonSuggestionExpert._extract_variables("a, b = 1, 2", 0, 1)
        assert vars_ == []

    def test_for_loop_variable(self) -> None:
        code = "for i in range(10):\n    pass"
        vars_ = PythonSuggestionExpert._extract_variables(code, 0, 2)
        assert "i" in vars_

    def test_with_as_variable(self) -> None:
        code = "with open('f') as f:\n    pass"
        vars_ = PythonSuggestionExpert._extract_variables(code, 0, 2)
        assert "f" in vars_

    def test_except_as_variable(self) -> None:
        code = "try:\n    pass\nexcept Exception as e:\n    pass"
        vars_ = PythonSuggestionExpert._extract_variables(code, 0, 4)
        assert "e" in vars_

    def test_function_parameters(self) -> None:
        code = "def f(a, b, c):\n    pass"
        vars_ = PythonSuggestionExpert._extract_variables(code, 0, 2)
        for arg in ("a", "b", "c", "self"):
            assert arg in vars_




class TestBuiltinConstants:
    """检验 API_DOCS.md 中描述的常量集合。"""

    def test_builtin_functions_contains_common(self) -> None:
        for name in ("print", "len", "isinstance", "open", "input"):
            assert name in BUILTIN_FUNCTIONS

    def test_builtin_functions_does_not_contain_classes(self) -> None:
        """``range`` / ``int`` / ``str`` 应当属于 BUILTIN_CLASSES 而非 FUNCTIONS。"""
        for name in ("range", "int", "str", "list", "dict"):
            assert name not in BUILTIN_FUNCTIONS
            assert name in BUILTIN_CLASSES

    def test_builtin_classes_contains_common(self) -> None:
        for name in ("list", "dict", "str", "int", "float", "bool", "range"):
            assert name in BUILTIN_CLASSES

    def test_builtin_properties_contains_constants_and_dunders(self) -> None:
        for name in ("True", "False", "None", "__name__", "__file__", "__doc__"):
            assert name in BUILTIN_PROPERTIES

    def test_keywords_contains_python_keywords(self) -> None:
        for name in (
            "False", "None", "True", "and", "as", "assert", "async", "await",
            "break", "class", "continue", "def", "del", "elif", "else", "except",
            "finally", "for", "from", "global", "if", "import", "in", "is",
            "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield",
        ):
            assert name in KEYWORDS

    def test_builtin_attrs_has_expected_keys(self) -> None:
        for type_name in ("str", "list", "dict", "int", "float", "set", "tuple", "bytes", "bool"):
            assert type_name in BUILTIN_ATTRS
            assert isinstance(BUILTIN_ATTRS[type_name], list)
            assert len(BUILTIN_ATTRS[type_name]) > 0




class TestEndToEnd:
    def test_api_docs_example(self) -> None:
        source = (
            "import os\n"
            "\n"
            "class Greeter:\n"
            "    def __init__(self, name):\n"
            "        self.name = name\n"
            "\n"
            "    def greet(self):\n"
            '        return f"hi {self."\n'
            "\n"
            'g = Greeter("world")\n'
            "print(g.greet)\n"
        )

        expert = PythonSuggestionExpert()

        pos = source.index("self.") + len("self.")
        block = SuggestionBlock(code=source, position=pos)
        attr_result = expert.suggest(block)
        assert "greet" in attr_result
        assert "__init__" in attr_result

        pos2 = source.index("print(") + len("print(")
        block2 = SuggestionBlock(code=source, position=pos2)
        ident_result = expert.suggest(block2)
        assert "Greeter" in ident_result
        assert "print" in ident_result