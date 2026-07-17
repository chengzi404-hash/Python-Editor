# Architecture

This document describes how the major subsystems in Python Editor fit
together. The source layout is `core/` for the editor and its language /
settings / plugin subsystems, and `ui/` for the Tk toolkit and its
accompanying web framework.

## High-level diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         main.py → core.editor.app.CodeEditor        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Tk window (ui.widgets.window.Window)                          │  │
│  │  ├── MenuBar (UMenu / UMenuBar)                               │  │
│  │  ├── Toolbar (UButton row)                                    │  │
│  │  ├── ActivityBar + SideBar (Explorer / Debug / Git)           │  │
│  │  ├── TabBar + UText editor (LineNumberCanvas)                 │  │
│  │  ├── Output panel (UText, runner stdout/stderr)               │  │
│  │  ├── Status bar (lang, cursor, …)                             │  │
│  │  └── UEditorSuggestion (code-completion popup)                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│           │           │            │                                │
│           ▼           ▼            ▼                                │
│    settings     highlighter     plugins                            │
│   (manager)   + suggestion     (manager)                           │
│       │           │               │                                │
│       ▼           ▼               ▼                                │
│   JSON files    themes      global+proj                            │
│   schema        dom_cache   plugins dir                            │
└─────────────────────────────────────────────────────────────────────┘
```

## Subsystems

### 1. Editor (`core.editor`)
- `CodeEditor` is the single application controller. It is a 2 300-line
  object that builds the Tk window, wires every other subsystem together,
  and forwards plugin events back to the editor internals.
- The `Document` dataclass is the data model for one open tab; `_Debouncer`
  is the GUI-agnostic debounce scheduler used for highlight / suggestion /
  autosave timers.
- `lang_config.LANG_CONFIG` is the language registry consulted by the
  editor when switching languages, picking highlighter/suggestion experts
  by file extension, and rendering the language menu.

### 2. Settings (`core.settings`)
- Two scopes: **global** (`SettingsScope.GLOBAL`) and **project**
  (`SettingsScope.PROJECT`). `SettingsManager` is the unified entry point.
- Each scope has a `SettingsSchema` (a tuple of `SettingSpec`). The schema
  defines keys, types, defaults, min/max, choices, and the label /
  description shown in the UI.
- Persistence is JSON. `JsonFileSettings` writes via temp-file + `os.replace`
  to guarantee atomicity, and uses a per-file lock.
- Plugin-scoped keys (`plugins.<id>.*`) bypass schema validation because
  plugin IDs are dynamic; they live in the `_extras` map.
- Changes emit `SettingsChangeEvent` to all listeners (editor, plugins, …).
- UI: `USettingPanel` (one scope) and `UProjectSettingsWindow` (both
  scopes, side navigation).

### 3. Plugins (`core.plugins`)
- Discovery scans `<config-root>/plugins/**` (global) and
  `<project>/plugins/**` (project).
- Each plugin is a directory containing `__init__.py` (or `plugin.py`)
  that exposes a `MANIFEST` and a `register(ctx)` function. The entry
  point receives a `PluginContext` and may register hooks, commands,
  languages, or read/write settings.
- The host (`PluginManager`) implements `PluginHostAPI` and dispatches
  `HookEvents` constants declared in `core.plugins.hooks`.
- The plugin manager window (`UPluginManagerWindow`) shows the load state
  and exposes enable / disable / reload / info actions.

### 4. Highlighter + Suggestion (`core.language.highlighter`, `core.language.suggestion`)
- Both expose an abstract base: `HighlighterExpert` and `SuggestionExpert`.
- Each implementation declares `get_languange_exts()` (sic — kept for
  compatibility with existing plugins) so the editor can pick the right
  pair by file extension.
- The DOM cache (`core.language.highlighter.dom_cache`) scans installed
  Python libraries once and caches their classes / functions / submodules
  for fast attribute completion.

### 5. Runner (`core.runner`)
- `stream_command()` runs a subprocess with separate drain threads for
  stdout and stderr, calling back line-by-line. `done_callback` fires
  when the process exits (or times out).
- `run_blocking()` is the simpler `subprocess.run` wrapper used by
  `CPythonChecker` and quick utility tasks.
- The `CodeEditor._run_*` methods orchestrate the runners and redirect
  their output to the output panel.

### 6. UI toolkit (`ui.widgets`)
- Themed replacement for raw `tk.*` widgets. Every widget listens to the
  current theme and re-applies colors on `theme.set_theme(...)`.
- `Window` is the custom-titlebar root window used by `CodeEditor`.
- `LineNumberCanvas`, `TabBar`, `UEditorSuggestion` and `TreeCanvas` are
  Canvas-drawn — Tk does not provide native equivalents.

### 7. i18n (`core.settings.i18n`)
- Two locales: `zh_CN` (default) and `en_US` (fallback).
- `Translator` is a process-wide singleton; `t(key, **kwargs)` is the
  module shortcut. Strings use Python `str.format` placeholders.
- All UI text must go through `t()`. Hard-coded English is a bug.

### 8. Logging (`core.settings.logging`)
- `configure_logging()` is called once from `main.py` before anything
  else.
- Writes to `logs/<name>.log` (rotating, default 5 MiB × 5 backups) and
  optionally to the console.
- In-memory ring buffer (`get_entries`) is used by the in-app log viewer.

### 9. Checker (`core.language.checker`)
- Three backends: `Flake8Checker`, `PyrightChecker`, `CPythonChecker`.
  They share the abstract `Checker` interface returning `Output` rows.
- The editor runs them in sequence and surfaces the first non-empty
  result through the output panel.

### 10. Shell wrappers (`ui.call`)
- `Command` is the generic subprocess wrapper used by `Git`, `Pip`,
  `Npm`. Editor code (git card) goes through these classes
  instead of calling `subprocess` directly.
- Exception hierarchy under `CallError` lets callers distinguish
  "command missing" from "command returned non-zero".

### 11. Web framework (`ui.web`)
- A self-contained Django-inspired WSGI framework: `UWSGIApp`,
  `URLRouter`, request / response, an ORM with multiple backends
  (SQLite / MySQL / PostgreSQL / Oracle), auth, sessions, admin, and a
  Jinja2 template backend.
- Lives in the editor so that "ship your editor extension as a web app"
  is possible; it is **not** loaded by the editor startup. See
  [`ui/web/README.md`](../../ui/web/README.md).

### 12. Tooling (`ui.tool`, `ui.cli`, `ui.demo`)
- `ui.tool.designer` — visual widget designer (Canvas-based, edit a
  scene XML file).
- `ui.cli` — project scaffolder, theme generator, info / demo / designer
  launchers.
- `ui.demo` — runs the component gallery `Window` that exercises every
  public widget.

## Lifecycle

```
main.py
  ├── configure_logging(...)
  ├── CodeEditor()                       # from core.editor.app
  │     ├── SettingsManager()            # loads global settings.json
  │     ├── Translator.set_language()    # picks i18n.language
  │     ├── theme.set_theme()            # picks ui.theme
  │     ├── PluginManager()              # loads global plugins
  │     ├── build menu / toolbar / editor / status
  │     └── show welcome tab
  └── editor.window.mainloop()           # Tk mainloop
```