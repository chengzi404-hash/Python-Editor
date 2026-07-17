# `main.py` — Application entry point

`main.py` is a 26-line bootstrap that configures logging and starts the
`CodeEditor` from `core.editor.app`. All non-trivial logic lives in
`core.editor.app.CodeEditor` and the subsystems it wires together.

```text
$ python main.py [--custom-titlebar]
```

| Argument | Effect |
| --- | --- |
| `--custom-titlebar` | Use a frameless window with a custom title bar (otherwise OS-native title bar). |

## Source

[`main.py`](../../main.py)

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.editor.app import CodeEditor
from core.settings.logging import configure_logging

_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
configure_logging(
    level="INFO",
    file_enabled=True,
    console_enabled=True,
    log_dir=_log_dir,
    max_bytes=5 * 1024 * 1024,
    backup_count=5,
)


def main():
    app = CodeEditor()
    app.window.mainloop()


if __name__ == "__main__":
    main()
```

## What `main.py` does

1. **Inserts the project root into `sys.path`** so `core.*` and `ui.*`
   packages resolve without installing the wheel.
2. **Imports `CodeEditor`** from `core.editor.app` and
   `configure_logging` from `core.settings.logging`.
3. **Configures logging** before anything else runs. Defaults:
   - `level="INFO"`, `file_enabled=True`, `console_enabled=True`
   - `log_dir = <project-root>/logs/`
   - `max_bytes = 5 MiB`, `backup_count = 5`
4. **Defines `main()`** that constructs `CodeEditor()` and runs the Tk
   mainloop on `app.window`.

There are no module-level constants or globals besides the log directory
and the four import-time side effects above.

## `CodeEditor`

The full reference for `CodeEditor` — its constructor, internal state,
and grouped methods — lives in [core/editor.md](core/editor.md). The
short version:

```python
from core.editor.app import CodeEditor

editor = CodeEditor()    # builds window, settings, plugins, env manager, menubar, toolbar, …
editor.window.mainloop() # blocks; returns when the user closes the window
```

Constructor responsibilities (see [`core/editor/app.py`](../../core/editor/app.py)):

1. Build the `Window` (custom or native titlebar based on
   `--custom-titlebar`).
2. Instantiate `SettingsManager`, `Translator`, themes, plugin manager,
   environment manager.
3. Construct the menubar, toolbar, tab bar, editor, output panel, status
   bar.
4. Load global plugins and refresh plugin menus.
5. Schedule an initial `EnvironmentManager.scan()` after 100 ms.

The `Window` is held at `editor.window`. The internal state is
intentionally private (underscore prefix). Plugins interact with the
editor exclusively through the `PluginContext` passed to their entry
point — see [core/plugins.md](core/plugins.md).