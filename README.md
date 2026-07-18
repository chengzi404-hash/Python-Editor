# Python Editor

[![Quality](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/quality.yml/badge.svg)](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/quality.yml)
[![Test](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/pytest.yml/badge.svg)](https://github.com/chengzi404-hash/Python-Editor/actions/workflows/pytest.yml)
[![License](https://img.shields.io/github/license/chengzi404-hash/Python-Editor)](LICENSE)

<div align="center">
 A concise and efficient Python code editor that supports syntax highlighting, auto-completion, code inspection, and multi-language execution.
</div>

## ✨ Core Highlights
- **Out of the box** — No complex configuration required, simply run `python main.py` to start
- **Multi-language support** — Supports file types such as Python, JSON, XML, YAML, C/C++, Log, etc
- **Intelligent Completion** — Context-aware code suggestions for Python and C/C++
- **Code quality inspection** — Integrates Flake8, Pyright, and py_compile
- **One-click operation** — Supports venv, conda, and system Python environment selection
- **Plugin Extensions** — A rich ecosystem of plugins, enabling easy customization of functions
- **Bilingual Interface** — Real-time switching between Chinese and English interfaces

## 🚀 Quick Start
```bash
python main.py
```

## 📋 Main functions
### Multi-document editing
The Tab bar supports opening and switching multiple files simultaneously

### Syntax highlighting
Provide color syntax highlighting for files such as Python, JSON, XML, YAML, C/C++, Log, etc

### Intelligent completion
Automatically pop up completion suggestions based on code context

### Code inspection
Integrate Flake8, Pyright, and py_compile for static analysis

### One-click operation
Supports quick switching and execution between venv, conda, and system Python environments

### Plugin system
Provide a hook event mechanism to extend the customization capabilities of the editor

### Switch topic
Supports three theme appearances: Dark, Light, and Solarized Dark

### Internationalization
Built-in Chinese and English languages, with real-time switchable interface display

## ⚙️ Configuration and Data
| Type | Path |
|------|------|
| Global Configuration | `~/.python-editor/settings.json` |
| Project Configuration | `<project>/.editorconfig` |
| Global plugins | `~/.python-editor/plugins/` |
| Project plugin | `<project>/plugins/` |

## ✅ Quality Assurance
- **Test Coverage** — 280+ automated test cases
- **Continuous Integration** — Multi-version testing for Python 3.10~3.12
- **Code standards** — Ruff + MyPy strict checking

---

<div align="center">
 Made with ❤️ by <a href="https://github.com/chengzi404-hash">chengzi404-hash</a>
</div>