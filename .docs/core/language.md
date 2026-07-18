# `core.language`

**Source layout**:

```
core/language/
├── __init__.py
├── checker/             — static analysis backends
│   ├── __init__.py
│   ├── base.py
│   └── python.py
├── highlighter/         — syntax highlighters + themes + DOM cache + marketplace
│   ├── __init__.py
│   ├── base.py
│   ├── python.py
│   ├── ccpp.py
│   ├── json_expert.py
│   ├── xml_expert.py
│   ├── yaml_expert.py
│   ├── log_expert.py
│   ├── themes.py
│   ├── marketplace.py
│   └── dom_cache.py
└── suggestion/          — code completion experts
    ├── __init__.py
    ├── base.py
    ├── python.py
    ├── c.py
    └── cpp.py
```

All three sub-packages follow the same shape: an abstract base class,
concrete experts per language, plus a `__init__.py` that re-exports
them. The editor picks the right `(highlighter, suggestion, checker)`
triple by file extension through `core.editor.lang_config.LANG_CONFIG`.

---

## `core.language.checker`

**Source**:
- [`base.py`](../../core/language/checker/base.py) — 22 lines
- [`python.py`](../../core/language/checker/python.py) — 207 lines

Static-analysis backends for Python files. Three implementations of the
same abstract `Checker` interface; the editor picks whichever tools are
installed.

```python
from core.language.checker import (
    OutputRow, Output, Checker,
    Flake8Checker, PyrightChecker, CPythonChecker,
)
```

### Data model `[base.py]`

```python
@dataclass
class OutputRow:
    message: str
    level: str        # 'error' | 'warning' | 'convention' | 'notice' | 'info'

@dataclass
class Output:
    file: str
    row: list[OutputRow]

class Checker(ABC):
    @abstractmethod
    def check(self, file: str) -> Output: ...
```

A `Checker` consumes a file path and returns all diagnostics for it;
there is no streaming, the entire result fits in one `Output`.

### Implementations

#### `Flake8Checker` `[python.py:10]`

Runs `python -m flake8` against the file and parses its line-oriented
output.

| Behaviour | Detail |
| --- | --- |
| Success | Each `path:line:col: CODE message` row is mapped: `E`/`F` → `error`, `W` → `warning`, `C` → `convention`, `N` → `notice`. |
| Module missing | Emits `FLAKE8_NOT_FOUND` at level `info` and falls back to `ast.parse` syntax check. |
| Subprocess timeout | 30 s; same fallback as above. |

#### `PyrightChecker` `[python.py:93]`

Runs `pyright --outputjson` against the file.

| Behaviour | Detail |
| --- | --- |
| JSON output | Parses `generalDiagnostics` and `summary`. Levels: `error`/`warning`/`information` → `error`/`warning`/`info`. |
| Plain-text fallback | Splits on `:` and detects `warning` / `information` / `error` prefixes. |
| Tool missing | Emits `PYRIGHT_NOT_FOUND` at level `info` and returns. |
| Subprocess timeout | 60 s. |

#### `CPythonChecker` `[python.py:170]`

Executes the file with the interpreter running `main.py`:

```
python -c <source>
```

| Behaviour | Detail |
| --- | --- |
| Non-zero exit | Each line of stderr (after stripping `Traceback` markers and file frames) becomes an `OutputRow` at level `error`. |
| Timeout | 30 s; emits `execution timed out`. |
| Read failure | Emits `file not found: …` or `cannot read file: …` at level `error`. |

This checker is **destructive** — it actually runs the code. Use only
for short, safe scripts, or replace with a sandboxed runner.

### Module-level constants `[python.py]`

| Name | Line | Value |
| --- | --- | --- |
| `FLAKE8_NOT_FOUND` | 7 | `'flake8 is not installed, using basic syntax check only'` |
| `PYRIGHT_NOT_FOUND` | 90 | `'pyright is not installed, type checking skipped'` |
| `CPYTHON_CHECK_FAILED` | 167 | `'python execution check failed'` |

---

## `core.language.highlighter`

**Source**:
- [`base.py`](../../core/language/highlighter/base.py) — 26 lines
- [`python.py`](../../core/language/highlighter/python.py) — ~340 lines
- [`ccpp.py`](../../core/language/highlighter/ccpp.py)
- [`json_expert.py`](../../core/language/highlighter/json_expert.py)
- [`xml_expert.py`](../../core/language/highlighter/xml_expert.py)
- [`yaml_expert.py`](../../core/language/highlighter/yaml_expert.py)
- [`log_expert.py`](../../core/language/highlighter/log_expert.py)
- [`themes.py`](../../core/language/highlighter/themes.py) — 209 lines
- [`marketplace.py`](../../core/language/highlighter/marketplace.py) — 125 lines
- [`dom_cache.py`](../../core/language/highlighter/dom_cache.py) — 280 lines

Syntax-highlighting subsystem: experts, themes, marketplace, and a
Python library DOM cache used for fast attribute completion.

```python
from core.language.highlighter import (
    HighlightToken, HighlightBlock, HighlighterExpert,
    PythonHighlighterExpert, CcppHighlighterExpert,
    JsonHighlighterExpert, XmlHighlighterExpert,
    YamlHighlighterExpert, LogHighlighterExpert,
    highlight_themes, highlight_marketplace,
    LibraryDOM, ensure_lib_cache, get_lib_dom,
    get_or_load_lib_dom, build_full_cache,
    cache_exists, invalidate_lib_cache,
)
```

### Data model `[base.py]`

```python
@dataclass
class HighlightToken:
    start: int      # char offset in HighlightBlock.code (inclusive)
    end: int        # char offset (exclusive)
    type: str       # token type, e.g. 'keyword', 'string'

@dataclass
class HighlightBlock:
    code: str
    tokens: list[HighlightToken] | None = None

class HighlighterExpert(ABC):
    @abstractmethod
    def highlight(self, block: HighlightBlock) -> HighlightBlock: ...
    @abstractmethod
    def get_languange_exts(self) -> list: ...
```

`highlight()` is pure: it takes a `HighlightBlock`, returns the same
block populated with `tokens`. The editor calls it on debounced
background schedules.

### Built-in highlighters

| Class | File | Extensions |
| --- | --- | --- |
| `PythonHighlighterExpert` | `python.py` | `.py` |
| `CcppHighlighterExpert` | `ccpp.py` | `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.hh` |
| `JsonHighlighterExpert` | `json_expert.py` | `.json` |
| `XmlHighlighterExpert` | `xml_expert.py` | `.xml`, `.html`, `.xhtml`, `.xsd`, `.xsl`, `.svg` |
| `YamlHighlighterExpert` | `yaml_expert.py` | `.yaml`, `.yml` |
| `LogHighlighterExpert` | `log_expert.py` | `.log`, `.txt`, `.logs` |

The `PythonHighlighterExpert` is the most featureful: it tracks
`def`/`class` boundaries, parses `from X import …` statements, and
resolves dotted paths to attributes via the DOM cache.

### Theme registry (`core.language.highlighter.themes`)

Re-exported as `core.language.highlighter.highlight_themes`. The
module-level functions manage a single current theme and a list of
listeners.

```python
from core.language.highlighter import highlight_themes

# Inspection
highlight_themes.available_names()      # ['Default Dark', 'Default Light', 'Solarized Dark']
highlight_themes.current()              # HighlightTheme
highlight_themes.current_name()         # 'Default Dark'
highlight_themes.tokens()               # {'keyword': {'foreground': '#569cd6'}, ...}
highlight_themes.tokens('Solarized Dark')

# Mutation
highlight_themes.set_theme('Default Light')

# Events
highlight_themes.on_change(callback)    # callback(name: str)
highlight_themes.off_change(callback)
```

Built-in themes registered at import time:

| Name | Inspired by |
| --- | --- |
| `Default Dark` | VS Code Dark+ |
| `Default Light` | VS Code Light+ |
| `Solarized Dark` | Solarized |

`HighlightTheme` is a frozen-by-convention dataclass:

```python
@dataclass
class HighlightTheme:
    name: str
    label: str = ''
    tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    description: str = ''
```

### Marketplace (`core.language.highlighter.marketplace`)

Re-exported as `core.language.highlighter.highlight_marketplace`. Mirror
of the plugin and language marketplaces — provides `MarketplaceProvider`
as an abstract base and a single in-process `HighlightThemeMarketplace`
implementation.

```python
from core.language.highlighter import highlight_marketplace
m = highlight_marketplace.get_marketplace()
items = m.search("dark")                # list[MarketplaceSearchResult]
pkg   = m.get_item("default-dark")      # HighlightThemePackage | None
m.download(pkg, target_dir)             # installs to disk
```

### DOM cache (`core.language.highlighter.dom_cache`)

```python
from core.language.highlighter import (
    LibraryDOM, ensure_lib_cache, get_lib_dom,
    get_or_load_lib_dom, build_full_cache,
    cache_exists, invalidate_lib_cache,
)
```

Per-package caches of the public surface (classes, functions,
submodules, nested submodule contents). Stored as JSON files under
`cache/python_libs/<name>.json` (see [core/data.md](data.md)).

```python
@dataclass
class LibraryDOM:
    name: str
    version: str = ''
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    submodules: list[str] = field(default_factory=list)
    submodule_contents: dict[str, dict] = field(default_factory=dict)
                                 # submodule_name -> {'classes': [...], 'functions': [...]}
```

| Function | Signature | Description |
| --- | --- | --- |
| `get_lib_dom` | `(lib_name: str) -> Optional[LibraryDOM]` | Read the cached entry or `None`. No scan. |
| `ensure_lib_cache` | `(lib_name: str) -> Optional[LibraryDOM]` | Scan (via `__import__` + `pkgutil`) and write the cache. Returns `None` if the package can't be resolved. |
| `get_or_load_lib_dom` | `(lib_name: str) -> Optional[LibraryDOM]` | Cached-or-load: read first, scan on miss. |
| `build_full_cache` | `(progress_callback=None) -> int` | Scan every top-level package (excluding stdlib, tests, venvs). Calls `progress_callback(current, total)` after each. Returns the count of successfully cached packages. |
| `cache_exists` | `(lib_name: str) -> bool` | |
| `invalidate_lib_cache` | `(lib_name: str) -> None` | Delete the JSON entry. Silent on missing. |

---

## `core.language.suggestion`

**Source**:
- [`base.py`](../../core/language/suggestion/base.py) — 44 lines
- [`python.py`](../../core/language/suggestion/python.py)
- [`c.py`](../../core/language/suggestion/c.py)
- [`cpp.py`](../../core/language/suggestion/cpp.py)

Code completion experts for Python, C, and C++. They share the same
abstract `SuggestionExpert` API as the highlighter.

```python
from core.language.suggestion import (
    SuggestionBlock, SuggestionItem, SuggestionExpert, DOMScope,
    PythonSuggestionExpert, CSuggestionExpert, CppSuggestionExpert,
    KEYWORDS, BUILTIN_FUNCTIONS, BUILTIN_CLASSES, BUILTIN_PROPERTIES, BUILTIN_ATTRS,
)
```

### Data model `[base.py]`

```python
@dataclass
class SuggestionBlock:
    code: str
    position: int

@dataclass
class DOMScope:
    begin: int
    end: int
    varibles: list
    functions: list
    classes: list
    sub_dom: "list[DOMScope]"

@dataclass
class SuggestionItem:
    label: str
    priority: int = 0       # Lower value = higher priority (appears first)
    kind: str = ''          # 'keyword' | 'builtin' | 'function' | 'class' | 'variable'

class SuggestionExpert(ABC):
    @abstractmethod
    def suggest(self, block: SuggestionBlock) -> list[SuggestionItem]: ...
    @abstractmethod
    def get_languange_exts(self) -> list: ...
```

### Implementations

| Class | File | Extensions |
| --- | --- | --- |
| `PythonSuggestionExpert` | `python.py` | `.py` |
| `CSuggestionExpert` | `c.py` | `.c`, `.h` |
| `CppSuggestionExpert` | `cpp.py` | `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh` |

### Built-in sets (`core.language.suggestion.python`)

The Python expert ships with built-in keyword / function / class /
property / attribute tables used when the live DOM is not yet known:

| Name | Source |
| --- | --- |
| `KEYWORDS` | `data/suggestions/keywords_*.json` |
| `BUILTIN_FUNCTIONS` | `data/suggestions/builtins_*.json` |
| `BUILTIN_CLASSES` | same file as builtins |
| `BUILTIN_PROPERTIES` | same file as builtins |
| `BUILTIN_ATTRS` | same file as builtins |

Each table has an `en_US` and `zh_CN` variant; the active one is picked
based on the current translator language.

---

## Public surface

```python
# core.language.checker
__all__ = ["CPythonChecker", "Checker", "Flake8Checker", "Output",
           "OutputRow", "PyrightChecker"]

# core.language.highlighter
__all__ = ["CcppHighlighterExpert", "HighlightBlock", "HighlightToken",
           "HighlighterExpert", "JsonHighlighterExpert",
           "LibraryDOM", "LogHighlighterExpert",
           "PythonHighlighterExpert", "XmlHighlighterExpert",
           "YamlHighlighterExpert", "build_full_cache", "cache_exists",
           "ensure_lib_cache", "get_lib_dom", "get_or_load_lib_dom",
           "highlight_marketplace", "highlight_themes",
           "invalidate_lib_cache"]

# core.language.suggestion
__all__ = ["BUILTIN_ATTRS", "BUILTIN_CLASSES", "BUILTIN_FUNCTIONS",
           "BUILTIN_PROPERTIES", "KEYWORDS", "CSuggestionExpert",
           "CppSuggestionExpert", "DOMScope", "PythonSuggestionExpert",
           "SuggestionBlock", "SuggestionExpert", "SuggestionItem"]
```