from ._command import Command


class Git(Command):
    _option_aliases = {
        "empty": "allow-empty",
    }
    _required_args = {
        "commit": ("message",),
    }

    def __init__(self, cwd=None):
        super().__init__("git", cwd=cwd)
