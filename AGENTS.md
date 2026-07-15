# AGENTS.md

## Project Overview

Python Editor is a Tkinter-based code editor. Entry point: `python main.py`.

## CI Workflow

`quality.yml` runs in order: `ruff check` → `ruff format --check` → `mypy`

`pytest.yml` runs on Python 3.10–3.12, Ubuntu and Windows.

## Package Structure

- `modules/` — core packages (Uui, highlighter, checker, runner, plugins, settings, i18n, env_manager)
- `utils/` — utility modules
- `tests/` — pytest test suite with fixtures in `conftest.py`

## Key Conventions

- Packages are discovered with `setuptools.packages.find` using `modules*` and `utils*` patterns
- Line length: 100 (ruff + black)
- Ruff ignores: `B008` (function call in default arg, common in Tk callbacks), `B904`, `SIM108`, `SIM117`
- Tests directory ignores `F401`, `F811`, `N802`, `N803`
- i18n uses `t(key, **kwargs)` — all UI text must go through `t()`, hardcoded strings are a bug
- Two locales: `zh_CN` (default), `en_US` (fallback)
- Use english comments
- When editing docs, create '.zh.md' for chinese files and '.md' for english files
