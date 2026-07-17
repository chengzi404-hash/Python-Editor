# Python Editor — API Documentation

Reference documentation for every public module in this project. Line numbers
in `[brackets]` refer to the implementation files.

## Layout

```
.docs/
├── README.md                  — this file
├── architecture.md            — high-level architecture overview
├── entry-point.md             — main.py and CodeEditor
├── core/                      — core package overviews (English)
│   ├── editor.md              — core/editor/*             (CodeEditor, Document, lang registry)
│   ├── env_manager.md         — core/env_manager/*        (Python interpreter detection)
│   ├── language.md            — core/language/*           (highlighter, suggestion, checker)
│   ├── plugins.md             — core/plugins/*            (plugin manager, hooks, marketplace)
│   ├── runner.md              — core/runner/*             (subprocess streaming runner)
│   ├── settings.md            — core/settings/*           (global/project settings, i18n, logging)
│   └── data.md                — core/data.py              (data/cache path helpers)
└── ui/                        — UI framework overviews
    ├── widgets.md             — ui/widgets/*              (Tk toolkit)
    ├── call.md                — ui/call/*                 (Git / Pip / Npm wrappers)
    ├── web.md                 — ui/web/*                  (WSGI framework + ORM + admin)
    ├── tool.md                — ui/tool/*                 (visual designer)
    ├── cli.md                 — ui/cli.py                 (scaffolding CLI)
    └── demo.md                — ui/demo.py                (component gallery)
```

## Two complementary views

- `core/` and `ui/` — **module-level** documentation (English): the entry
  points, the public classes, the most important methods, and how the parts
  fit together. Read these first.
- `ui/web/README.md` — a long-form Chinese reference for the embedded WSGI
  framework. Treat it as an authoritative lookup for that subsystem.

## Naming convention

Per [`AGENTS.md`](../AGENTS.md):

- English documentation → `*.md`
- Chinese documentation → `*.zh.md`

## Project at a glance

| Item | Value |
| --- | --- |
| Entry point | `main.py` (`python main.py`) |
| Core packages | `core.editor`, `core.env_manager`, `core.language.*`, `core.plugins`, `core.runner`, `core.settings.*` |
| UI framework | Tkinter + `ui.widgets.*` |
| i18n default | `zh_CN` (fallback `en_US`) |
| Settings location (Win) | `%APPDATA%\PythonEditor\settings.json` |
| Settings location (project) | `<root>/.pyeditor/settings.json` |
| Plugins (global) | `<config_root>/plugins/` (e.g. `%APPDATA%\PythonEditor\plugins/`) |
| Python | `>= 3.10` |

## Module map

| Module | Purpose | Doc |
| --- | --- | --- |
| `core.editor` | `CodeEditor` controller, document model, language registry | [core/editor.md](core/editor.md) |
| `core.env_manager` | Detect / manage Python interpreters and packages | [core/env_manager.md](core/env_manager.md) |
| `core.language.checker` | Static analysis backends (flake8 / pyright / ast) | [core/language.md](core/language.md) |
| `core.language.highlighter` | Syntax highlighters + theme registry + DOM cache | [core/language.md](core/language.md) |
| `core.language.suggestion` | Code completion experts (Python / C / C++) | [core/language.md](core/language.md) |
| `core.plugins` | Plugin loading, hooks, manifest, manager UI | [core/plugins.md](core/plugins.md) |
| `core.runner` | Subprocess streaming and blocking runners | [core/runner.md](core/runner.md) |
| `core.settings` | Global + per-project settings, schemas | [core/settings.md](core/settings.md) |
| `core.settings.i18n` | Translation lookup and runtime language switching | [core/settings.md](core/settings.md) |
| `core.settings.logging` | Unified rotating-file logger | [core/settings.md](core/settings.md) |
| `core.data` | Locate data/cache files in `data/` and `cache/` | [core/data.md](core/data.md) |
| `ui.widgets` | Themed Tk widget toolkit | [ui/widgets.md](ui/widgets.md) |
| `ui.call` | Shell command wrappers (Git, Pip, Npm) | [ui/call.md](ui/call.md) |
| `ui.web` | Django-inspired WSGI framework + ORM + admin | [ui/web.md](ui/web.md) |
| `ui.tool` | Visual widget designer | [ui/tool.md](ui/tool.md) |
| `ui.cli` | Scaffolding CLI (`python -m ui.cli`) | [ui/cli.md](ui/cli.md) |
| `ui.demo` | Component gallery | [ui/demo.md](ui/demo.md) |

## Public surface guarantees

- Every subpackage has an explicit `__all__`; **only** symbols listed there are
  considered public API. Anything else is internal and may change without notice.
- Settings keys are documented in [core/settings.md](core/settings.md).
  All keys are dotted (`ui.theme`, `editor.tab_size`, …) and grouped by prefix.
- Plugin authors should only import from `core.plugins.*`; in particular,
  `core.plugins.api.PluginContext` is the contract every plugin receives.