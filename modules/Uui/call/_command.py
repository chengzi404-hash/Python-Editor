import shutil
import subprocess

from .exceptions import (
    CommandExecutionError,
    CommandNotFoundError,
    MissingArgumentError,
    SubcommandNotFoundError,
)


class Command:
    _option_aliases = {}
    _required_args = {}

    def __init__(self, program, cwd=None):
        if shutil.which(program) is None:
            raise CommandNotFoundError(f"Command not found: {program}")
        self.program = program
        self.cwd = cwd

    def _build_option(self, key):
        flag = self._option_aliases.get(key, key).replace('_', '-')
        if len(flag) == 1:
            return f'-{flag}'
        return f'--{flag}'

    def _append_options(self, cmd, kwargs):
        for key, value in kwargs.items():
            option = self._build_option(key)
            if isinstance(value, bool):
                if value:
                    cmd.append(option)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    cmd.append(option)
                    cmd.append(str(item))
            else:
                cmd.append(option)
                cmd.append(str(value))

    def _check_required_args(self, subcommand, kwargs):
        required = self._required_args.get(subcommand, ())
        for arg in required:
            if arg not in kwargs:
                raise MissingArgumentError(
                    f"Missing required argument '{arg}' for '{self.program} {subcommand}'"
                )

    def _run(self, cmd):
        try:
            return subprocess.run(
                cmd,
                cwd=self.cwd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise CommandExecutionError(
                f"Command failed: {' '.join(str(c) for c in exc.cmd)}",
                returncode=exc.returncode,
                stdout=exc.stdout,
                stderr=exc.stderr,
                cmd=exc.cmd,
            ) from exc
        except FileNotFoundError as exc:
            raise CommandNotFoundError(
                f"Command not found: {self.program}"
            ) from exc

    def _validate_subcommand(self, subcommand):
        if not subcommand:
            raise SubcommandNotFoundError(
                f"Subcommand not found for '{self.program}'"
            )

    def __getattr__(self, name):
        subcommand = name.replace('_', '-')
        self._validate_subcommand(subcommand)

        def method(*args, **kwargs):
            self._check_required_args(subcommand, kwargs)
            cmd = [self.program, subcommand]
            self._append_options(cmd, kwargs)
            cmd.extend(str(arg) for arg in args)
            return self._run(cmd)

        return method

    def __call__(self, *args, **kwargs):
        cmd = [self.program]
        self._append_options(cmd, kwargs)
        cmd.extend(str(arg) for arg in args)
        return self._run(cmd)
