from ._command import Command


class Npm(Command):
    def __init__(self, cwd=None):
        super().__init__('npm', cwd=cwd)
