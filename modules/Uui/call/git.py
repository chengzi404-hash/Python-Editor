from typing import ClassVar

from ._command import Command


class Git(Command):
    _option_aliases: ClassVar[dict] = {
        "empty": "allow-empty",
    }
    _required_args: ClassVar[dict] = {
        "commit": ("message",),
    }

    def __init__(self, cwd=None):
        super().__init__("git", cwd=cwd)
