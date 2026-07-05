from ._command import Command


class Pip(Command):
    def __init__(self, cwd=None):
        super().__init__('pip', cwd=cwd)
