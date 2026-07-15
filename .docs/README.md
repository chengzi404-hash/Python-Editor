# Python Editor — API Documentation

Reference documentation for every public module in this project. Generated from
the source code; line numbers in `[brackets]` refer to the implementation files.

## Layout

```
.docs/
├── README.md                  — this file
├── architecture.md            — high-level architecture overview
├── entry-point.md             — main.py and CodeEditor
├── modules/                   — module-level overviews (this directory)
│   ├── data.md                — modules/data.py
│   ├── checker.md             — modules/checker/*
│   ├── env_manager.md         — modules/env_manager/*
│   ├── highlighter.md         — modules/highlighter/*
│   ├── i18n.md                — modules/i18n/*
│   ├── logging.md             — modules/logging/*
│   ├── plugins.md             — modules/plugins/*
│   ├── runner.md              — modules/runner/*
│   ├── settings.md            — modules/settings/*
│   └── suggestion.md          — modules/suggestion/*
├── uui/                       — vendored library overviews
│   ├── widgets.md             — modules/Uui/widgets/*  (Tk toolkit)
│   ├── call.md                — modules/Uui/call/*     (shell helpers)
│   ├── tool.md                — modules/Uui/tool/*     (visual designer)
│   └── web.md                 — modules/Uui/web/*      (WSGI framework)
└── api/                       — per-file API reference (Chinese, auto-generated)
    └── *.zh.md                — one file per source module
```

## Two complementary views

- `modules/` and `uui/` — **module-level** documentation (English): the
  entry points, the public classes, the most important methods, and how
  the parts fit together. Read these first.
- `api/*.zh.md` — **per-file** API reference (Chinese): every public
  symbol in every source file, with signatures and brief descriptions.
  Use as a lookup table when you need a specific function.

## Naming convention

Per [`AGENTS.md`](../AGENTS.md):

- English documentation → `*.md`
- Chinese documentation → `*.zh.md`

## Project at a glance

| Item | Value |
| --- | --- |
| Entry point | `main.py` (`python main.py` or `python -m`) |
| UI toolkit | Tkinter + `modules.Uui.widgets.*` |
| i18n default | `zh_CN` (fallback `en_US`) |
| Settings location (Win) | `%APPDATA%\PythonEditor\settings.json` |
| Settings location (project) | `<root>/.pyeditor/settings.json` |
| Plugins (global) | `~/.python_editor_plugins/` (or platform equivalent) |
| Python | `>= 3.10` |

## Module map

| Module | Purpose | Doc |
| --- | --- | --- |
| `modules.data` | Locate data/cache files in `data/` and `cache/` | [modules/data.md](modules/data.md) |
| `modules.charts` | Reserved (empty package) | — |
| `modules.checker` | Static analysis backends (flake8 / pyright / ast) | [modules/checker.md](modules/checker.md) |
| `modules.env_manager` | Detect / manage Python interpreters and packages | [modules/env_manager.md](modules/env_manager.md) |
| `modules.highlighter` | Syntax highlighters + theme registry + DOM cache | [modules/highlighter.md](modules/highlighter.md) |
| `modules.i18n` | Translation lookup and runtime language switching | [modules/i18n.md](modules/i18n.md) |
| `modules.logging` | Unified rotating-file logger | [modules/logging.md](modules/logging.md) |
| `modules.plugins` | Plugin loading, hooks, manifest, manager UI | [modules/plugins.md](modules/plugins.md) |
| `modules.runner` | Subprocess streaming and blocking runners | [modules/runner.md](modules/runner.md) |
| `modules.settings` | Global + per-project settings, schemas, UI | [modules/settings.md](modules/settings.md) |
| `modules.suggestion` | Code completion experts (Python / C / C++) | [modules/suggestion.md](modules/suggestion.md) |
| `modules.Uui.widgets` | Themed Tk widget toolkit | [uui/widgets.md](uui/widgets.md) |
| `modules.Uui.call` | Shell command wrappers (Git, Pip, Npm) | [uui/call.md](uui/call.md) |
| `modules.Uui.tool` | Visual widget designer | [uui/tool.md](uui/tool.md) |
| `modules.Uui.web` | Django-inspired WSGI framework + ORM + admin | [uui/web.md](uui/web.md) |

## Public surface guarantees

- Every subpackage has an explicit `__all__`; **only** symbols listed there are
  considered public API. Anything else is internal and may change without notice.
- Settings keys are documented in [modules/settings.md](modules/settings.md).
  All keys are dotted (`ui.theme`, `editor.tab_size`, …) and grouped by prefix.
- Plugin authors should only import from `modules.plugins.*`; in particular,
  `modules.plugins.api.PluginContext` is the contract every plugin receives.