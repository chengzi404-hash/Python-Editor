from .base import SuggestionExpert, SuggestionBlock, DOMScope

import re

CLASS_PATTERN = re.compile(
    r'^[ \t]*'
    r'class\s+'
    r'(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'\s*'
    r'(?:\([^()]*\))?'
    r'\s*'
    r':',
    re.MULTILINE
)

FUNC_PATTERN = re.compile(
    r'^[ \t]*'
    r'(?:async\s+)?'
    r'def\s+'
    r'(?P<name>[A-Za-z_][A-Za-z0-9_]*)'
    r'\s*'
    r'\([^()]*\)'
    r'\s*'
    r'(?:->\s*[^:]*)?'
    r':',
    re.MULTILINE
)

BUILTIN_FUNCTIONS = [
    'abs', 'all', 'any', 'ascii', 'bin', 'breakpoint', 'callable',
    'chr', 'compile', 'delattr', 'dir', 'divmod', 'eval', 'exec',
    'format', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex',
    'id', 'input', 'isinstance', 'issubclass', 'len', 'locals',
    'max', 'min', 'next', 'oct', 'open', 'ord', 'pow', 'print',
    'repr', 'round', 'setattr', 'sorted', 'sum', 'vars', '__import__',
]

BUILTIN_CLASSES = [
    'bool', 'bytearray', 'bytes', 'classmethod', 'complex', 'dict',
    'enumerate', 'filter', 'float', 'frozenset', 'int', 'list',
    'map', 'memoryview', 'object', 'property', 'range', 'reversed',
    'set', 'slice', 'staticmethod', 'str', 'super', 'tuple', 'type',
    'zip',
]

BUILTIN_PROPERTIES = [
    'True', 'False', 'None', 'Ellipsis', 'NotImplemented',
    '__name__', '__file__', '__doc__', '__package__', '__loader__',
    '__spec__', '__path__', '__all__',
]

KEYWORDS = [
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
    'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
    'while', 'with', 'yield',
]

BUILTIN_ATTRS: dict[str, list[str]] = {
    'str': [
        '__add__', '__class__', '__contains__', '__delattr__', '__dir__',
        '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
        '__getitem__', '__getnewargs__', '__gt__', '__hash__', '__init__',
        '__iter__', '__le__', '__len__', '__lt__', '__mod__', '__mul__',
        '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__',
        '__rmod__', '__rmul__', '__setattr__', '__sizeof__', '__str__',
        '__subclasshook__', 'capitalize', 'casefold', 'center', 'count',
        'encode', 'endswith', 'expandtabs', 'find', 'format', 'format_map',
        'index', 'isalnum', 'isalpha', 'isascii', 'isdecimal', 'isdigit',
        'isidentifier', 'islower', 'isnumeric', 'isprintable', 'isspace',
        'istitle', 'isupper', 'join', 'ljust', 'lower', 'lstrip',
        'maketrans', 'partition', 'removeprefix', 'removesuffix', 'replace',
        'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit', 'rstrip',
        'split', 'splitlines', 'startswith', 'strip', 'swapcase', 'title',
        'translate', 'upper', 'zfill',
    ],
    'list': [
        '__add__', '__class__', '__contains__', '__delattr__', '__delitem__',
        '__dir__', '__doc__', '__eq__', '__format__', '__ge__',
        '__getattribute__', '__getitem__', '__gt__', '__hash__', '__iadd__',
        '__imul__', '__init__', '__iter__', '__le__', '__len__', '__lt__',
        '__mul__', '__ne__', '__new__', '__reduce__', '__reduce_ex__',
        '__repr__', '__reversed__', '__rmul__', '__setattr__', '__setitem__',
        '__sizeof__', '__str__', '__subclasshook__', 'append', 'clear',
        'copy', 'count', 'extend', 'index', 'insert', 'pop', 'remove',
        'reverse', 'sort',
    ],
    'dict': [
        '__class__', '__contains__', '__delattr__', '__delitem__', '__dir__',
        '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
        '__getitem__', '__gt__', '__hash__', '__init__', '__iter__', '__le__',
        '__len__', '__lt__', '__ne__', '__new__', '__reduce__',
        '__reduce_ex__', '__repr__', '__setattr__', '__setitem__',
        '__sizeof__', '__str__', '__subclasshook__', 'clear', 'copy',
        'fromkeys', 'get', 'items', 'keys', 'pop', 'popitem',
        'setdefault', 'update', 'values',
    ],
    'int': [
        '__abs__', '__add__', '__and__', '__bool__', '__ceil__', '__class__',
        '__delattr__', '__dir__', '__divmod__', '__doc__', '__eq__',
        '__float__', '__floor__', '__floordiv__', '__format__', '__ge__',
        '__getattribute__', '__getnewargs__', '__gt__', '__hash__',
        '__index__', '__init__', '__int__', '__invert__', '__le__', '__lshift__',
        '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__new__',
        '__or__', '__pos__', '__pow__', '__radd__', '__rand__', '__rdivmod__',
        '__reduce__', '__reduce_ex__', '__repr__', '__rfloordiv__', '__rlshift__',
        '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__',
        '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__', '__rxor__',
        '__setattr__', '__sizeof__', '__str__', '__sub__', '__subclasshook__',
        '__truediv__', '__trunc__', '__xor__', 'as_integer_ratio', 'bit_count',
        'bit_length', 'conjugate', 'denominator', 'from_bytes', 'imag',
        'numerator', 'real', 'to_bytes',
    ],
    'float': [
        '__abs__', '__add__', '__bool__', '__ceil__', '__class__',
        '__delattr__', '__dir__', '__divmod__', '__doc__', '__eq__',
        '__float__', '__floor__', '__floordiv__', '__format__', '__ge__',
        '__getattribute__', '__getnewargs__', '__gt__', '__hash__',
        '__init__', '__int__', '__le__', '__lt__', '__mod__', '__mul__',
        '__ne__', '__neg__', '__new__', '__pos__', '__pow__', '__radd__',
        '__rdivmod__', '__reduce__', '__reduce_ex__', '__repr__',
        '__rfloordiv__', '__rmod__', '__rmul__', '__round__', '__rpow__',
        '__rsub__', '__rtruediv__', '__setattr__', '__sizeof__', '__str__',
        '__sub__', '__subclasshook__', '__truediv__', '__trunc__',
        'as_integer_ratio', 'conjugate', 'fromhex', 'hex', 'imag', 'is_integer',
        'real',
    ],
    'set': [
        '__and__', '__class__', '__contains__', '__delattr__', '__dir__',
        '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
        '__gt__', '__hash__', '__iand__', '__init__', '__ior__', '__isub__',
        '__iter__', '__ixor__', '__le__', '__len__', '__lt__', '__ne__',
        '__new__', '__or__', '__rand__', '__reduce__', '__reduce_ex__',
        '__repr__', '__ror__', '__rsub__', '__rxor__', '__setattr__',
        '__sizeof__', '__str__', '__sub__', '__subclasshook__', '__xor__',
        'add', 'clear', 'copy', 'difference', 'difference_update',
        'discard', 'intersection', 'intersection_update', 'isdisjoint',
        'issubset', 'issuperset', 'pop', 'remove',
        'symmetric_difference', 'symmetric_difference_update', 'union',
        'update',
    ],
    'tuple': [
        '__add__', '__class__', '__contains__', '__delattr__', '__dir__',
        '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
        '__getitem__', '__getnewargs__', '__gt__', '__hash__', '__init__',
        '__iter__', '__le__', '__len__', '__lt__', '__mul__', '__ne__',
        '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__rmul__',
        '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
        'count', 'index',
    ],
    'bytes': [
        '__add__', '__class__', '__contains__', '__delattr__', '__dir__',
        '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__',
        '__getitem__', '__getnewargs__', '__gt__', '__hash__', '__init__',
        '__iter__', '__le__', '__len__', '__lt__', '__mod__', '__mul__',
        '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__',
        '__rmod__', '__rmul__', '__setattr__', '__sizeof__', '__str__',
        '__subclasshook__', 'capitalize', 'center', 'count', 'decode',
        'endswith', 'expandtabs', 'find', 'fromhex', 'hex', 'index',
        'isalnum', 'isalpha', 'isascii', 'isdigit', 'islower', 'isspace',
        'istitle', 'isupper', 'join', 'ljust', 'lower', 'lstrip',
        'maketrans', 'partition', 'removeprefix', 'removesuffix', 'replace',
        'rfind', 'rindex', 'rjust', 'rpartition', 'rsplit', 'rstrip',
        'split', 'splitlines', 'startswith', 'strip', 'swapcase', 'title',
        'translate', 'upper', 'zfill',
    ],
    'bool': [
        '__abs__', '__add__', '__and__', '__bool__', '__ceil__', '__class__',
        '__delattr__', '__dir__', '__divmod__', '__doc__', '__eq__',
        '__float__', '__floor__', '__floordiv__', '__format__', '__ge__',
        '__getattribute__', '__getnewargs__', '__gt__', '__hash__',
        '__index__', '__init__', '__int__', '__invert__', '__le__', '__lshift__',
        '__lt__', '__mod__', '__mul__', '__ne__', '__neg__', '__new__',
        '__or__', '__pos__', '__pow__', '__radd__', '__rand__', '__rdivmod__',
        '__reduce__', '__reduce_ex__', '__repr__', '__rfloordiv__', '__rlshift__',
        '__rmod__', '__rmul__', '__ror__', '__round__', '__rpow__',
        '__rrshift__', '__rshift__', '__rsub__', '__rtruediv__', '__rxor__',
        '__setattr__', '__sizeof__', '__str__', '__sub__', '__subclasshook__',
        '__truediv__', '__trunc__', '__xor__',
    ],
}

class PythonSuggestionExpert(SuggestionExpert):
    def __init__(self) -> None:
        super().__init__()

    def get_languange_exts(self) -> list:
        return ['py']

    def suggest(self, block: SuggestionBlock) -> list:
        code = block.code
        pos = block.position

        text_before = code[:pos]
        line_no = text_before.count('\n')
        line_start = text_before.rfind('\n') + 1 if '\n' in text_before else 0
        col = pos - line_start

        lines = code.split('\n')
        current_line = lines[line_no] if line_no < len(lines) else ''
        before_cursor = current_line[:col]

        word_start = col
        while word_start > 0 and (current_line[word_start - 1].isalnum() or current_line[word_start - 1] == '_'):
            word_start -= 1
        prefix = current_line[word_start:col]

        if word_start > 0 and current_line[word_start - 1] == '.':
            obj_end = word_start - 1
            obj_start = obj_end - 1
            while obj_start >= 0 and (current_line[obj_start].isalnum() or current_line[obj_start] == '_'):
                obj_start -= 1
            obj_name = current_line[obj_start + 1:obj_end]
            suggestions = self._suggest_attributes(block, line_no, obj_name)
        else:
            suggestions = self._suggest_names(block, line_no)

        if prefix:
            suggestions = [s for s in suggestions if s.startswith(prefix)]

        return sorted(set(suggestions))
    
    def _suggest_names(self, block: SuggestionBlock, line_no: int) -> list[str]:
        suggestions = set()

        suggestions.update(BUILTIN_FUNCTIONS)
        suggestions.update(BUILTIN_CLASSES)
        suggestions.update(BUILTIN_PROPERTIES)
        suggestions.update(KEYWORDS)

        root = self._build_scope_tree(block.code)

        def _walk(scope: DOMScope, pos: int) -> None:
            suggestions.update(scope.functions)
            suggestions.update(scope.classes)
            suggestions.update(scope.varibles)

            vars_in_scope = self._extract_variables(block.code, scope.begin, scope.end)
            suggestions.update(vars_in_scope)

            for sub in scope.subDOM:
                if sub.begin <= pos < sub.end:
                    _walk(sub, pos)
                    break

        _walk(root, line_no)
        return list(suggestions)

    def _suggest_attributes(self, block: SuggestionBlock, line_no: int, obj_name: str) -> list[str]:
        if obj_name == 'self':
            cls_methods = self._enclosing_class_methods(block, line_no)
            if cls_methods:
                return cls_methods

        if obj_name in BUILTIN_ATTRS:
            return BUILTIN_ATTRS[obj_name]

        if obj_name in BUILTIN_CLASSES:
            return BUILTIN_ATTRS.get(obj_name, list(BUILTIN_ATTRS.get('object', [])))

        return [
            '__class__', '__delattr__', '__dir__', '__doc__', '__eq__',
            '__format__', '__ge__', '__getattribute__', '__gt__',
            '__hash__', '__init__', '__le__', '__lt__', '__ne__',
            '__new__', '__reduce__', '__reduce_ex__', '__repr__',
            '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
        ]

    def _enclosing_class_methods(self, block: SuggestionBlock, line_no: int) -> list[str]:
        lines = block.code.split('\n')

        start_line = line_no
        while start_line >= 0:
            line = lines[start_line]
            m = re.match(r'^[ \t]*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^()]*\))?\s*:', line)
            if m:
                class_indent = len(line) - len(line.lstrip())
                break
            start_line -= 1
        else:
            return []

        methods = []
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            line_stripped = line.lstrip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            indent = len(line) - len(line_stripped)
            if indent <= class_indent and line_stripped.startswith('class'):
                break
            if indent > class_indent:
                m = re.match(r'^[ \t]*def\s+([A-Za-z_][A-Za-z0-9_]*)', line)
                if m:
                    methods.append(m.group(1))

        if not methods:
            return []

        return methods + [
            '__class__', '__delattr__', '__dir__', '__doc__', '__eq__',
            '__format__', '__ge__', '__getattribute__', '__gt__',
            '__hash__', '__init__', '__le__', '__lt__', '__ne__',
            '__new__', '__reduce__', '__reduce_ex__', '__repr__',
            '__setattr__', '__sizeof__', '__str__', '__subclasshook__',
        ]

    @staticmethod
    def _extract_variables(code: str, begin: int, end: int) -> list[str]:
        lines = code.split('\n')
        segment = '\n'.join(lines[begin:end]) if begin < len(lines) else ''
        vars_found = set()

        for m in re.finditer(r'(?:^|[;\n])\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[^=]+)?\s*=\s*', segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r'\bfor\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b', segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r'\bwith\s+[^:]*\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r'\bexcept\s+[^:]*\s+as\s+([A-Za-z_][A-Za-z0-9_]*)', segment):
            vars_found.add(m.group(1))

        for m in re.finditer(r'\bdef\s+\w+\s*\(([^)]*)\)', segment):
            args = m.group(1)
            for arg in args.split(','):
                arg = arg.strip().split(':')[0].split('=')[0].strip()
                if arg:
                    vars_found.add(arg)
                    vars_found.add('self')
                    vars_found.add('cls')

        return list(vars_found)

    @staticmethod
    def _collect_entries(code: str) -> list[tuple[int, int, str, str, int]]:
        total_lines = code.count('\n') + 1

        entries = []
        for pattern, kind in ((CLASS_PATTERN, 'class'), (FUNC_PATTERN, 'function')):
            for m in pattern.finditer(code):
                line_no = code[:m.start()].count('\n')
                indent = len(m.group()) - len(m.group().lstrip())
                name = m.group('name')
                entries.append((line_no, indent, kind, name, 0))
        entries.sort(key=lambda x: x[0])

        for i in range(len(entries)):
            end = total_lines
            for j in range(i + 1, len(entries)):
                if entries[j][1] <= entries[i][1]:
                    end = entries[j][0]
                    break
            entries[i] = (entries[i][0], entries[i][1], entries[i][2], entries[i][3], end)

        return entries

    @staticmethod
    def iter_classes(block: SuggestionBlock) -> list[str]:
        return [name for _, _, kind, name, _ in PythonSuggestionExpert._collect_entries(block.code) if kind == 'class']

    @staticmethod
    def iter_function(block: SuggestionBlock) -> list[str]:
        return [name for _, _, kind, name, _ in PythonSuggestionExpert._collect_entries(block.code) if kind == 'function']

    @staticmethod
    def _build_scope_tree(code: str) -> DOMScope:
        entries = PythonSuggestionExpert._collect_entries(code)
        if not entries:
            return DOMScope(begin=0, end=code.count('\n') + 1, varibles=[], functions=[], classes=[], subDOM=[])

        total_lines = entries[-1][4]

        root = DOMScope(begin=0, end=total_lines, varibles=[], functions=[], classes=[], subDOM=[])
        stack = [(root, -1)]

        for line_no, indent, kind, name, end in entries:
            while stack and stack[-1][1] >= indent:
                stack.pop()

            parent = stack[-1][0]
            scope = DOMScope(begin=line_no, end=end, varibles=[], functions=[], classes=[], subDOM=[])

            if kind == 'class':
                parent.classes.append(name)
            else:
                parent.functions.append(name)

            parent.subDOM.append(scope)
            stack.append((scope, indent))

        return root

    @staticmethod
    def find_domin(block: SuggestionBlock, position: int) -> DOMScope:
        root = PythonSuggestionExpert._build_scope_tree(block.code)

        def _deepest(scope: DOMScope, pos: int) -> DOMScope:
            for sub in scope.subDOM:
                if sub.begin <= pos < sub.end:
                    return _deepest(sub, pos)
            return scope

        return _deepest(root, position)