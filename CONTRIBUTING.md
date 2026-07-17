# Contributing to Python Editor

Thank you for your interest in contributing to Python Editor!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/Python-Editor.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
5. Install dependencies: `pip install -e .`

## Development Workflow

### Code Quality

This project uses:
- **Ruff** for linting and formatting
- **Mypy** for type checking
- **Pytest** for testing

Run quality checks:
```bash
ruff check .
ruff format --check .
mypy .
pytest tests/
```

### Writing Code

- Follow existing code style (English comments, 100 char line length)
- Use `t(key, **kwargs)` for all UI text (internationalization)
- All new features should include tests
- Update documentation as needed

### Commit Messages

- Use clear, descriptive commit messages
- Reference issue numbers when applicable

## Pull Request Process

1. Create a new branch for your feature/fix: `git checkout -b feature/my-feature`
2. Make your changes
3. Run quality checks locally
4. Submit a pull request with a clear description

## Project Structure

```
modules/
├── Uui/           # UI framework
├── highlighter/   # Syntax highlighting
├── checker/       # Code checking
├── runner/        # Code execution
├── plugins/       # Plugin system
├── settings/      # Configuration
└── i18n/          # Internationalization
```

## Questions?

Feel free to open an issue for any questions about contributing.
