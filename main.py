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
