# Python Editor — AGENTS.md

Tkinter-based code editor with syntax highlighting, code completion, static checking, and multi-language run support.

## Project

- **Stack:** Python 3.10+, Tkinter, self-built Uui widget library
- **Entry point:** `python main.py` (creates `CodeEditor` from `core/editor/app.py`)
- **Tests:** `python -m pytest tests/` (280+ tests)
- **Lint:** `ruff check .` | **Format:** `ruff format --check .` | **Type:** `mypy --explicit-package-bases .`
- **Config:** `pyproject.toml` (ruff, mypy, setuptools config)

## Package Structure

| Path | Role |
|------|------|
| `core/editor/app.py` | Main `CodeEditor` class — window, menus, file ops, event dispatch (~3000 lines) |
| `core/editor/document.py` | `Document` model — file content, language, dirty tracking |
| `core/settings/settings/` | Settings framework: `SettingsManager`, `GlobalSettings`, `ProjectSettings`, JSON persistence, schema, UI widgets |
| `core/settings/i18n/` | i18n engine: `Translator` singleton, `t()` function, locale JSON files in `data/i18n/locales/` |
| `core/settings/logging/` | Logging configuration |
| `core/plugins/` | Plugin system — `PluginManager`, `PluginContext`, `PluginAPI` |
| `core/language/` | Language definitions and registration |
| `core/runner/` | Code runner (subprocess execution) |
| `ui/` | Uui widget library: `UFrame`, `UButton`, `UText`, `TabBar`, `TreeCanvas`, `USettingsNavBar` etc. |
| `ui/widgets/` | Individual widget modules (button, checkbutton, combobox, entry, frame, label, etc.) |
| `ui/widgets/settings_nav.py` | `USettingsNavBar` — settings navigation tree component |
| `utils/` | Utility modules (currently empty) |
| `data/i18n/locales/` | `en_US.json` + `zh_CN.json` translation files |
| `tests/` | pytest suite: checkers, highlighter, i18n, plugins, runner, settings, suggestion |

## CI Workflow

- `.github/workflows/quality.yml` — `ruff check` → `ruff format --check` → `mypy`
- `.github/workflows/pytest.yml` — runs on Python 3.10–3.12, Ubuntu + Windows
- `ruff` ignores: `B008`, `B904`, `SIM108`, `SIM117` (Tk-compatible)
- `tests/` per-file ignores: `F401`, `F811`, `N802`, `N803`
- `ui/` per-file ignores: `N999` (intentional project name)
- Line length: 100 (ruff + black)

## Key Conventions

- **i18n first:** All UI-facing strings use `t("key", **kwargs)` from `core.settings.i18n`. Hardcoded user-visible strings are bugs
- **Default locale:** `zh_CN`; fallback: `en_US`. Menu & dialog text re-renders immediately on language switch
- **Settings pattern:** `SettingSpec` schema → `JsonFileSettings` (JSON persistence) → `SettingsManager` (unified API). UI uses `USettingPanel` + `UProjectSettingsWindow`
- **Settings translation:** Setting labels/descriptions use `t(f"settings.{key}.label", default=...)` and `t(f"settings.{key}.desc", default=...)`
- **Comments:** Use English for code comments
- **Docs:** English = `.md`, Chinese = `.zh.md`
- **Import style:** First-party = `core`, `ui`, `utils` (configured in ruff isort)
- **mypy:** Loose on Tkinter types; `ignore_missing_imports = true`

## Notes

(Legacy: `modules/` directory is empty. CI mypy config still references `modules/` — target is `main.py core ui utils`.)
