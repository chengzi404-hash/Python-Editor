# Python Editor

<div align="center">
<i>A Tkinter-based code editor with syntax highlighting, auto-completion, and plugin support.</i>
</div>

[![code-quality](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/quality.yml/badge.svg)](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/quality.yml)
[![pytest](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/pytest.yml/badge.svg)](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/pytest.yml)

## Features

- **Multi-Document Editing** - Tab-based interface with multiple open files
- **Syntax Highlighting** - Python, JSON, XML, YAML, C/C++, and log files
- **Auto-Completion** - Context-aware suggestions for Python, C, and C++
- **Code Checking** - Flake8, Pyright, and py_compile integration
- **Code Execution** - Run code with streaming output in selected Python environment
- **Python Environment Management** - Detect and manage venv, conda, and system Python
- **Plugin System** - Extensible architecture with hook-based events
- **Internationalization** - Chinese (zh_CN) and English (en_US) locales
- **Theme System** - Dark, Light, and Solarized Dark themes
- **Settings** - Global and project-scoped configuration

## Quick Start

```bash
python main.py
```

## Project Structure

```
python-editor/
├── main.py                    # Entry point - CodeEditor class
├── modules/                   # Core packages
│   ├── Uui/                   # UI framework (widgets, web, CLI)
│   ├── highlighter/           # Syntax highlighting engine
│   ├── checker/               # Code checking (flake8, pyright)
│   ├── runner/                # Code execution
│   ├── plugins/               # Plugin system
│   ├── settings/              # Configuration management
│   ├── i18n/                  # Internationalization
│   ├── env_manager/           # Python environment management
│   ├── suggestion/            # Auto-completion
│   └── logging/               # Logging system
├── data/                     # Static data
│   ├── i18n/locales/         # Translation files (zh_CN.json, en_US.json)
│   └── suggestions/          # Language suggestions data
├── tests/                    # Pytest test suite
└── .github/workflows/        # CI/CD workflows
```

## Architecture

### Uui - UI Framework

Tkinter widget wrappers providing consistent theming and behavior:

| Widget | Description |
|--------|-------------|
| `Window` | Custom titlebar with minimize/maximize/close |
| `UText` | Code editor with line numbers and scrollbar |
| `TabBar` | Multi-document tab management |
| `SideBar` | Explorer, Debug, and Git cards |
| `UButton` | Styled buttons (primary, default, ghost, danger) |
| `theme` | Dark, Light, Solarized Dark themes |

### Highlighter

Regex-based tokenization with language-specific experts:

```python
class HighlighterExpert(ABC):
    def highlight(self, block: HighlightBlock) -> HighlightBlock: ...
```

- **PythonHighlighterExpert** - Uses DOM cache for library symbol resolution
- **JsonHighlighterExpert**, **XmlHighlighterExpert**, **YamlHighlighterExpert**
- **LogHighlighterExpert** - Timestamp and log level highlighting
- **CcppHighlighterExpert** - C/C++ syntax

### Checker

Chain-based code validation:

```python
class Checker(ABC):
    def check(self, path: str) -> Output: ...

# Available checkers
Flake8Checker      # Linting
PyrightChecker     # Type checking
CPythonChecker      # Syntax validation
```

### Runner

Asynchronous code execution with streaming output:

```python
def stream_command(cmd, *, timeout_s=30.0, line_callback=None, done_callback=None)
```

Temporary files are created for code execution using the selected Python environment.

### Plugin System

Hook-based extensibility:

```python
@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str = "0.0.0"

# Plugin entry point
def register(ctx: PluginContext) -> None:
    ctx.add_command(menu="Plugins", label="My Command", callback=my_callback)
    ctx.on(HookEvents.EDITOR_FILE_OPENED, on_file_opened)
```

**Hook Events:**
- `EDITOR_FILE_OPENED`, `EDITOR_FILE_SAVED`, `EDITOR_FILE_CREATED`
- `EDITOR_CONTENT_CHANGED`, `EDITOR_LANGUAGE_CHANGED`
- `EDITOR_RUN_STARTED`, `EDITOR_RUN_FINISHED`
- `EDITOR_CLOSING`

**Plugin Locations:**
- Global: `~/.python-editor/plugins/`
- Project: `<project>/plugins/`

### Settings

Two-tier configuration system:

```python
class SettingsScope(Enum):
    GLOBAL = "global"    # User-wide, stored in ~/.python-editor/
    PROJECT = "project"  # Per-project, stored in <root>/.editorconfig
```

Key settings categories:
- `ui.*` - theme, highlight_theme, font_family, font_size
- `editor.*` - tab_size, auto_save, highlight_delay_ms
- `completion.*` - enabled, min_chars_before_trigger, max_suggestions
- `runner.*` - clear_output_before_run, stream_output, timeout_ms

### i18n

Key-based translation with runtime switching:

```python
def t(key: str, default: str | None = None, **kwargs) -> str
# Example: t("menu.file.new") -> "New"
```

Supported locales: `zh_CN` (default), `en_US` (fallback)

### Env Manager

Python environment detection and management:

```python
@dataclass
class PythonEnvironment:
    name: str
    python_path: str
    version: str
    env_type: str  # venv, conda, system, custom

env_manager.get_python_path()       # Get current interpreter path
env_manager.install_package("pkg")  # Install via pip
env_manager.create_venv(path)       # Create new venv
```

Scanned locations: sys.executable, system Pythons, .venv, venv, .env, conda

## Configuration

Global settings: `~/.python-editor/settings.json`
Project settings: `<project>/.editorconfig`

## Testing

```bash
pytest tests/
```

## CI/CD

**Quality Workflow:** `ruff check` → `ruff format --check` → `mypy`

**Test Workflow:** Runs on Python 3.10–3.12, Ubuntu and Windows

## Entry Point

```python
if __name__ == "__main__":
    editor = CodeEditor()
    editor.run()
```

Main initialization sequence:
1. Configure logging
2. Create window (custom or native titlebar)
3. Initialize settings (global + project)
4. Setup i18n translator
5. Build UI (menubar, toolbar, editor, output panel, status bar)
6. Load plugins
7. Scan Python environments
