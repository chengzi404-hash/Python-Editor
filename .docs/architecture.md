# Architecture

This document describes how the major subsystems in Python Editor fit together.

## High-level diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                          main.py — CodeEditor                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Tk window                                                  │  │
│  │  ├── MenuBar (UMenu / UMenuBar)                            │  │
│  │  ├── Toolbar (UButton row)                                 │  │
│  │  ├── ActivityBar + SideBar (Explorer / Debug / Git)        │  │
│  │  ├── TabBar + UText editor (LineNumberCanvas)              │  │
│  │  ├── Output panel (UText, runner stdout/stderr)            │  │
│  │  ├── Status bar (current env, lang, cursor, …)             │  │
│  │  └── UEditorSuggestion (code-completion popup)             │  │
│  └────────────────────────────────────────────────────────────┘  │
│           │           │            │           │                │
│           ▼           ▼            ▼           ▼                │
│   settings   highlighter   plugins      env_manager              │
│  (manager)  + suggestion  (manager)    (EnvironmentManager)      │
│       │        │              │              │                  │
│       ▼        ▼              ▼              ▼                  │
│  JSON files   themes      global+proj   python -m pip,           │
│  schema       dom_cache   plugins dir   venv create, …           │
└──────────────────────────────────────────────────────────────────┘
```

## Subsystems

### 1. Settings (`modules.settings`)
- Two scopes: **global** (`SettingsScope.GLOBAL`) and **project**
  (`SettingsScope.PROJECT`). `SettingsManager` is the unified entry point.
- Each scope has a `SettingsSchema` (a tuple of `SettingSpec`). The schema
  defines keys, types, defaults, min/max, choices, and the label/description
  shown in the UI.
- Persistence is JSON. `JsonFileSettings` writes via temp-file + `os.replace`
  to guarantee atomicity, and uses a per-file lock.
- Changes emit `SettingsChangeEvent` to all listeners (editor, plugins, …).
- UI: `USettingPanel` (one scope) and `UProjectSettingsWindow` (both scopes,
  side navigation).

### 2. Plugins (`modules.plugins`)
- Discovery scans `<config-root>/plugins/**` (global) and
  `<project>/plugins/**` (project).
- Each plugin is a directory containing `plugin.json` (manifest) and a Python
  entry point. The entry point receives a `PluginContext` and may register
  hooks, commands, languages, or read/write settings.
- The host (`PluginManager`) implements `PluginHostAPI` and dispatches
  `HookEvents` constants declared in `modules.plugins.hooks`.
- The plugin manager window (`UPluginManagerWindow`) shows the load state and
  exposes enable / disable / reload / info actions.

### 3. Highlighter + Suggestion (`modules.highlighter`, `modules.suggestion`)
- Both expose an abstract base: `HighlighterExpert` and `SuggestionExpert`.
- Each implementation declares `get_languange_exts()` so the editor can pick
  the right pair by file extension.
- The DOM cache (`modules.highlighter.dom_cache`) scans installed Python
  libraries once and caches their classes / functions / submodules for fast
  attribute completion.

### 4. Environment manager (`modules.env_manager`)
- On `scan()`, walks `PATH`, common install locations, conda envs and
  `<project>/.venv` to find `python` interpreters.
- Tracks the **current** environment. `install_package()` and
  `uninstall_package()` shell out to `python -m pip` on the right interpreter.
- `create_venv(path)` is the only mutation that affects disk structure
  outside `pip`’s control.
- Listeners (`add_listener`) let the UI refresh when the set of environments
  changes.

### 5. Runner (`modules.runner`)
- `stream_command()` runs a subprocess with separate drain threads for
  stdout and stderr, calling back line-by-line. `done_callback` fires when
  the process exits (or times out).
- `run_blocking()` is the simpler `subprocess.run` wrapper used by
  `CPythonChecker` and quick utility tasks.
- The `CodeEditor._run_*` methods in `main.py` orchestrate the runners and
  redirect their output to the output panel.

### 6. UI toolkit (`modules.Uui.widgets`)
- Themed replacement for raw `tk.*` widgets. Every widget listens to the
  current theme and re-applies colors on `set_theme(...)`.
- `Window` is the custom-titlebar root window used by `CodeEditor`.
- `LineNumberCanvas`, `TabBar`, `UEditorSuggestion` and `TreeCanvas` are
  Canvas-drawn — Tk does not provide native equivalents.

### 7. i18n (`modules.i18n`)
- Two locales: `zh_CN` (default) and `en_US` (fallback).
- `Translator` is a process-wide singleton; `t(key, **kwargs)` is the module
  shortcut. Strings use Python `str.format` placeholders.
- All UI text must go through `t()`. Hard-coded English is a bug.

### 8. Logging (`modules.logging`)
- `configure_logging()` is called once from `main.py` before anything else.
- Writes to `logs/<name>.log` (rotating, default 1 MiB × 5 backups) and
  optionally to the console.
- In-memory ring buffer (`get_entries`) is used by the in-app log viewer.

### 9. Checker (`modules.checker`)
- Three backends: `Flake8Checker`, `PyrightChecker`, `CPythonChecker`. They
  share the abstract `Checker` interface returning `Output` rows.
- Selection is made by `modules.checker.python` directly; the editor picks
  based on which tools are installed (`shutil.which`).

## Lifecycle

```
main.py
  ├── configure_logging(...)
  ├── get_logger("app").info("Application starting...")
  ├── CodeEditor()
  │     ├── SettingsManager()         # loads global settings.json
  │     ├── Translator.set_language() # picks ui.language
  │     ├── Theme.set_theme()         # picks ui.theme
  │     ├── PluginManager()           # loads global plugins
  │     ├── EnvironmentManager.scan()
  │     ├── build menu / toolbar / editor / status
  │     └── show welcome tab
  └── editor.run()                    # Tk mainloop
```