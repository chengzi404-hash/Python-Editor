class CallError(Exception):
    pass


class CommandNotFoundError(CallError):
    pass


class SubcommandNotFoundError(CallError):
    pass


class MissingArgumentError(CallError):
    pass


class CommandExecutionError(CallError):
    def __init__(self, message, returncode=None, stdout=None, stderr=None, cmd=None):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
