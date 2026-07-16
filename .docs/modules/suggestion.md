# `modules.suggestion`

**Source**:
- [`__init__.py`](../../modules/suggestion/__init__.py) — 28 lines
- [`base.py`](../../modules/suggestion/base.py) — 46 lines
- [`python.py`](../../modules/suggestion/python.py) — 659 lines
- [`c.py`](../../modules/suggestion/c.py) — 307 lines
- [`cpp.py`](../../modules/suggestion/cpp.py) — 359 lines

Code-completion experts, parallel to `modules.highlighter`. Each expert
is paired with a highlighter for a given language. The editor invokes
`suggest(block)` on debounced schedules while the user types.

```python
from modules.suggestion import (
    SuggestionBlock, DOMScope, SuggestionItem, SuggestionExpert,
    PythonSuggestionExpert, CSuggestionExpert, CppSuggestionExpert,
    KEYWORDS, BUILTIN_FUNCTIONS, BUILTIN_CLASSES,
    BUILTIN_PROPERTIES, BUILTIN_ATTRS,
)
```

## Data model

### `SuggestionBlock` `[base.py:7]`

```python
@dataclass
class SuggestionBlock:
    code: str         # entire buffer
    position: int     # cursor offset (chars)
```

### `DOMScope` `[base.py:13]`

```python
@dataclass
class DOMScope:
    begin: int
    end: int
    varibles: list    # NOTE: typo preserved from upstream
    functions: list
    classes: list
    subDOM: "list[DOMScope]"
```

Represents a Python scope (module, function, class). Used internally by
the Python expert to build a tree of nested scopes from `code`.

### `SuggestionItem` `[base.py:23]`

```python
@dataclass
class SuggestionItem:
    label: str              # displayed text
    priority: int = 0       # lower value = higher priority (sorted first)
    kind: str = ''          # 'keyword' | 'builtin' | 'function' | 'class' | 'variable'
```

### `SuggestionExpert` (abstract) `[base.py:36]`

```python
class SuggestionExpert(ABC):
    @abstractmethod
    def suggest(self, block: SuggestionBlock) -> List[SuggestionItem]: ...
    @abstractmethod
    def get_languange_exts(self) -> list: ...
```

`suggest()` is called from the Tk main thread after a `_Debouncer`
fires.

## Built-in experts

| Class | File | Extensions | Features |
| --- | --- | --- | --- |
| `PythonSuggestionExpert` | `python.py:861` | `.py` | Keywords, builtins, enclosing-scope methods (`self.*`), `from X import …`, dotted-path attribute completion via the DOM cache. |
| `CSuggestionExpert` | `c.py:239` | `.c`, `.h` | `.` and `->` attribute access; struct / union / enum / function / typedef discovery. |
| `CppSuggestionExpert` | `cpp.py:282` | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh` | All of C plus `::` scope resolution. |

## Public sets (from `PythonSuggestionExpert`)

| Symbol | Description |
| --- | --- |
| `KEYWORDS` | `set[str]` — Python language keywords. |
| `BUILTIN_FUNCTIONS` | `set[str]` — top-level functions from `builtins`. |
| `BUILTIN_CLASSES` | `set[str]` — top-level types. |
| `BUILTIN_PROPERTIES` | `set[str]` — `True`, `False`, `None`, dunders, etc. |
| `BUILTIN_ATTRS` | `dict[str, list[str]]` — per-type attribute list (e.g. `BUILTIN_ATTRS['list']` → `['append', 'clear', …]`). |

These are stable identifiers usable by external tools (e.g. tests).
They are populated from the bundled JSON files in `data/suggestions/python/`
or, failing that, from `_FALLBACK_*` constants in `python.py`.

## Usage

```python
from modules.suggestion import PythonSuggestionExpert, SuggestionBlock

expert = PythonSuggestionExpert()
items = expert.suggest(SuggestionBlock(code=src, position=cursor))
for item in items[:10]:                       # show top 10
    print(item.kind, item.label, item.priority)
```

## Internal helpers (Python expert)

The Python expert exposes a few static helpers used internally and by
tests:

| Method | Description |
| --- | --- |
| `PythonSuggestionExpert.iter_classes(...)` | Iterate classes found in the buffer. |
| `PythonSuggestionExpert.iter_function(...)` | Iterate top-level functions. |
| `PythonSuggestionExpert._build_scope_tree(...)` | Build a `DOMScope` tree from source. |
| `PythonSuggestionExpert.find_domin(...)` | Locate the innermost `DOMScope` for a position. |

These are not part of the public surface but are stable and widely used
in tests.