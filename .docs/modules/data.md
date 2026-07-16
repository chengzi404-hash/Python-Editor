# `modules.data`

**Source**: [`modules/data.py`](../../modules/data.py) — 55 lines.

Unified accessor for read-only data files shipped with the editor and for
the on-disk `cache/` directory. Every helper resolves to an absolute path.

```python
from modules.data import (
    data_dir, data_path, i18n_path, suggestions_path,
    cache_dir, cache_path,
)
```

## Layout

```
<project-root>/
├── data/                  # shipped with the editor
│   ├── i18n/locales/
│   └── suggestions/
│       ├── python/
│       ├── c/
│       └── cpp/
└── cache/                 # created on demand
    └── python_libs/       # library DOM cache
```

The two roots are computed from `__file__` at import time:

| Symbol | Value |
| --- | --- |
| `_ROOT` `[16]` | `<project-root>/data` |
| `_CACHE_ROOT` `[17]` | `<project-root>/cache` |

Both are considered **internal** — never use them directly, call the helpers.

## Functions

### `i18n_path(*parts: str) -> str` `[20]`

Absolute path to a file inside `data/i18n/`. Used by the translator to locate
locale JSON files:

```python
modules.i18n.translator.i18n_path("locales", "zh_CN.json")
# -> '.../data/i18n/locales/zh_CN.json'
```

### `data_path(*parts: str) -> str` `[25]`

Absolute path to a file inside `data/`. Generic accessor.

### `data_dir() -> str` `[30]`

Absolute path of the `data/` root.

### `suggestions_path(*parts: str) -> str` `[35]`

Absolute path inside `data/suggestions/`. Used by `modules.suggestion.*`
to load the keyword / builtin / header lists that ship with the editor.

### `cache_dir() -> str` `[40]`

Creates `cache/` if needed and returns its absolute path. Called internally
by `cache_path()`.

### `cache_path(*parts: str) -> str` `[46]`

Like `cache_dir()` but for a sub-path. The parent of the joined path is
created automatically.

```python
from modules.data import cache_path
p = cache_path("dom", "requests.json")   # ensures cache/dom/ exists
```

## Public surface

`__all__ = ["i18n_path", "data_path", "data_dir", "suggestions_path", "cache_dir", "cache_path"]`