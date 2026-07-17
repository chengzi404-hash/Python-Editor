# `core.data`

**Source**: [`core/data.py`](../../core/data.py) — 55 lines.

Unified accessor for read-only data files shipped with the editor and
for the on-disk `cache/` directory. Every helper resolves to an
absolute path.

```python
from core.data import (
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
| `_ROOT` | `<project-root>/data` |
| `_CACHE_ROOT` | `<project-root>/cache` |

Both are considered **internal** — never use them directly, call the
helpers below.

## Functions

### `i18n_path(*parts: str) -> str`

Absolute path to a file inside `data/i18n/`. Used by the translator to
locate locale JSON files:

```python
core.settings.i18n.translator.i18n_path("locales", "zh_CN.json")
# -> '.../data/i18n/locales/zh_CN.json'
```

### `data_path(*parts: str) -> str`

Absolute path to a file inside `data/`. Generic accessor.

### `data_dir() -> str`

Absolute path of the `data/` root.

### `suggestions_path(*parts: str) -> str`

Absolute path inside `data/suggestions/`. Used by
`core.language.suggestion.*` to load the keyword / builtin / header
lists that ship with the editor.

### `cache_dir() -> str`

Creates `cache/` if needed and returns its absolute path. Called
internally by `cache_path()`.

### `cache_path(*parts: str) -> str`

Like `cache_dir()` but for a sub-path. The parent of the joined path is
created automatically.

```python
from core.data import cache_path
p = cache_path("dom", "requests.json")   # ensures cache/dom/ exists
```

## Public surface

`__all__ = ["cache_dir", "cache_path", "data_dir", "data_path",
"i18n_path", "suggestions_path"]`.