# `modules.highlighter`

**Source**:
- [`__init__.py`](../../modules/highlighter/__init__.py) — 42 lines
- [`base.py`](../../modules/highlighter/base.py) — 28 lines
- [`python.py`](../../modules/highlighter/python.py) — 245 lines
- [`ccpp.py`](../../modules/highlighter/ccpp.py) — 152 lines
- [`json_expert.py`](../../modules/highlighter/json_expert.py) — 57 lines
- [`xml_expert.py`](../../modules/highlighter/xml_expert.py) — 47 lines
- [`yaml_expert.py`](../../modules/highlighter/yaml_expert.py) — 53 lines
- [`log_expert.py`](../../modules/highlighter/log_expert.py) — 68 lines
- [`themes.py`](../../modules/highlighter/themes.py) — 198 lines
- [`marketplace.py`](../../modules/highlighter/marketplace.py) — 130 lines
- [`dom_cache.py`](../../modules/highlighter/dom_cache.py) — 276 lines

Syntax-highlighting subsystem: experts, themes, marketplace and a Python
library DOM cache used for fast attribute completion.

```python
from modules.highlighter import (
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

## Data model

### `HighlightToken` `[base.py:6]`

```python
@dataclass
class HighlightToken:
    start: int      # char offset in HighlightBlock.code (inclusive)
    end: int        # char offset (exclusive)
    type: str       # token type, e.g. 'keyword', 'string'
```

### `HighlightBlock` `[base.py:12]`

```python
@dataclass
class HighlightBlock:
    code: str
    tokens: list[HighlightToken] | None = None
```

### `HighlighterExpert` `[base.py:18]`

```python
class HighlighterExpert(ABC):
    @abstractmethod
    def highlight(self, block: HighlightBlock) -> HighlightBlock: ...
    @abstractmethod
    def get_languange_exts(self) -> list: ...
```

`highlight()` is pure: it takes a `HighlightBlock`, returns the same block
populated with `tokens`. The editor calls it on debounced background
schedules.

## Built-in highlighters

| Class | File | Extensions |
| --- | --- | --- |
| `PythonHighlighterExpert` | `python.py:145` | `.py` |
| `CcppHighlighterExpert` | `ccpp.py:86` | `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.hh` |
| `JsonHighlighterExpert` | `json_expert.py:19` | `.json` |
| `XmlHighlighterExpert` | `xml_expert.py:17` | `.xml`, `.html`, `.xhtml`, `.xsd`, `.xsl`, `.svg` |
| `YamlHighlighterExpert` | `yaml_expert.py:17` | `.yaml`, `.yml` |
| `LogHighlighterExpert` | `log_expert.py:36` | `.log`, `.txt`, `.logs` |

The `PythonHighlighterExpert` (the most featureful) tracks `def`/`class`
boundaries, parses `from X import …` statements, and resolves dotted paths
to attributes via the DOM cache.

## Theme registry (`modules.highlighter.themes`)

Re-exported as `modules.highlighter.highlight_themes`. The module-level
functions manage a single current theme and a list of listeners.

```python
from modules.highlighter import highlight_themes

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

| Function | Signature | Description |
| --- | --- | --- |
| `register` | `(theme: HighlightTheme) -> None` | Add or replace a theme by `theme.name`. |
| `unregister` | `(name: str) -> None` | Remove a theme (no error if missing). |
| `get` | `(name: str) -> Optional[HighlightTheme]` | Lookup by name. |
| `available` | `() -> list[HighlightTheme]` | All registered themes. |
| `available_names` | `() -> list[str]` | Names of all themes. |
| `current_name` | `() -> str` | Active theme name. |
| `current` | `() -> HighlightTheme` | Active theme object (falls back to first available). |
| `tokens` | `(name: str \| None = None) -> dict` | Token colour map for the given or current theme. |
| `set_theme` | `(name: str) -> None` | Switch the active theme; fires listeners. |
| `on_change` | `(callback: Callable[[str], None]) -> None` | Subscribe to theme switches. |
| `off_change` | `(callback) -> None` | Unsubscribe. |

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
    tokens: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    description: str = ''
```

## Marketplace (`modules.highlighter.marketplace`)

Re-exported as `modules.highlighter.highlight_marketplace`. Mirror of the
plugin and language marketplaces — provides `MarketplaceProvider` as an
abstract base and a single in-process `HighlightThemeMarketplace`
implementation.

```python
from modules.highlighter import highlight_marketplace
m = highlight_marketplace.get_marketplace()
items = m.search("dark")                # list[MarketplaceSearchResult]
pkg   = m.get_item("default-dark")      # HighlightThemePackage | None
m.download(pkg, target_dir)             # installs to disk
```

## DOM cache (`modules.highlighter.dom_cache`)

```python
from modules.highlighter import (
    LibraryDOM, ensure_lib_cache, get_lib_dom,
    get_or_load_lib_dom, build_full_cache,
    cache_exists, invalidate_lib_cache,
)
```

Per-package caches of the public surface (classes, functions, submodules,
nested submodule contents). Stored as JSON files under
`cache/python_libs/<name>.json` (see [modules/data.md](data.md)).

### `LibraryDOM` `[dom_cache.py:31]`

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

### Functions

| Function | Signature | Description |
| --- | --- | --- |
| `get_lib_dom` | `(lib_name: str) -> Optional[LibraryDOM]` | Read the cached entry or `None`. No scan. |
| `ensure_lib_cache` | `(lib_name: str) -> Optional[LibraryDOM]` | Scan (via `__import__` + `pkgutil`) and write the cache. Returns `None` if the package can't be resolved. |
| `get_or_load_lib_dom` | `(lib_name: str) -> Optional[LibraryDOM]` | Cached-or-load: read first, scan on miss. |
| `build_full_cache` | `(progress_callback=None) -> int` | Scan every top-level package (excluding stdlib, tests, venvs). Calls `progress_callback(current, total)` after each. Returns the count of successfully cached packages. |
| `cache_exists` | `(lib_name: str) -> bool` | |
| `invalidate_lib_cache` | `(lib_name: str) -> None` | Delete the JSON entry. Silent on missing. |