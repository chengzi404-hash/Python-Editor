# `ui.call`

**Source**: [`ui/call/`](../../ui/call/)

Shell command wrappers used by the editor when it needs to interact with
external tools (git, pip, npm). All classes share the same `Command`
base and exception hierarchy so plugin code can call them uniformly.

```python
from ui.call import (
    Command,
    CallError, CommandExecutionError, CommandNotFoundError,
    MissingArgumentError, SubcommandNotFoundError,
    Git, Pip, Npm,
)
```

## `Command` base class `[_command.py]`

Generic subprocess wrapper with structured argument parsing. Used as
the foundation for `Git`, `Pip`, and `Npm`. Each subclass defines:

| Attribute | Purpose |
| --- | --- |
| `binary` | Executable name (e.g. `"git"`). |
| `subcommands` | Dict of `name -> SubcommandSpec`. Each spec defines args, flags, and an optional callback that turns parsed args into argv. |
| `arg_syntax` | Optional argument grammar (positional / flag / variadic). |

```python
result = Command.invoke("git", ["status"])   # low-level escape hatch
```

Most callers should use the typed subclasses below — they get
auto-completion and validation for free.

## Exceptions

All exceptions inherit from `CallError` (which extends `Exception`).
Consumers can catch the base class to handle every variant.

| Exception | When it is raised |
| --- | --- |
| `CallError` | Base class. |
| `CommandNotFoundError` | The binary is not on `PATH`. |
| `SubcommandNotFoundError` | The subcommand name is not declared in `subcommands`. |
| `MissingArgumentError` | A required argument was not supplied. |
| `CommandExecutionError` | The process exited with a non-zero status. |

## `Git` `[git.py]`

Wraps the `git` CLI. Subcommands cover status / log / diff / add /
commit / push / pull / branch / checkout / merge / rebase / stash / tag.

```python
git = Git()
status = git.status()                       # short status string
branches = git.branch_list()                # list[str]
git.add("file.py")
git.commit(message="fix: typo")
```

Each subcommand returns either a structured object (lists / dicts for
parseable output) or a plain string for read-only calls.

## `Pip` `[pip.py]`

Wraps `python -m pip` (so the editor always uses the same interpreter
that runs the editor itself, not whatever `pip` happens to be first on
`PATH`).

```python
pip = Pip()
outdated = pip.list_outdated()
pip.install("requests", upgrade=True, mirror="https://pypi.tuna.tsinghua.edu.cn/simple")
pip.uninstall("requests")
```

> The editor uses `sys.executable` directly to run scripts and checks
> through `Pip` and the runner (`core.runner`). Calling code does not need
> to manage interpreters separately.

## `Npm` `[npm.py]`

Wraps the `npm` CLI. Subcommands cover install / uninstall / run /
publish / outdated.

```python
npm = Npm()
npm.install("lodash")
npm.run("build")
```

## Public surface

`__all__ = ["CallError", "Command", "CommandExecutionError",
"CommandNotFoundError", "Git", "MissingArgumentError", "Npm", "Pip",
"SubcommandNotFoundError"]`.