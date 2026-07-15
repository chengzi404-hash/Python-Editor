# `modules.Uui.call`

**Source**:
- [`__init__.py`](../../modules/Uui/call/__init__.py) — 18 lines
- [`_command.py`](../../modules/Uui/call/_command.py) — 95 lines
- [`exceptions.py`](../../modules/Uui/call/exceptions.py) — 23 lines
- [`git.py`](../../modules/Uui/call/git.py) — 13 lines
- [`npm.py`](../../modules/Uui/call/npm.py) — 6 lines
- [`pip.py`](../../modules/Uui/call/pip.py) — 6 lines

Object-oriented wrappers around external CLI tools (`git`, `npm`,
`pip`). Each command object maps Python attribute access to the
subcommand line — `git.commit(message="m")` builds
`git commit --message m` and runs it.

```python
from modules.Uui.call import (
    CallError, CommandExecutionError, CommandNotFoundError,
    MissingArgumentError, SubcommandNotFoundError,
    Command, Git, Npm, Pip,
)
```

## Exceptions `[exceptions.py]`

| Exception | Base | Carries |
| --- | --- | --- |
| `CallError` | `Exception` | — |
| `CommandNotFoundError` | `CallError` | — |
| `SubcommandNotFoundError` | `CallError` | — |
| `MissingArgumentError` | `CallError` | — |
| `CommandExecutionError` | `CallError` | `returncode`, `stdout`, `stderr`, `cmd` |

## `Command` `[_command.py:12]`

Base class. Subclass for each tool.

### Class attributes

| Attribute | Default | Description |
| --- | --- | --- |
| `_option_aliases` | `{}` | Map kwarg name → CLI flag (default: kwarg name with `_` → `-`). |
| `_required_args` | `{}` | Map subcommand → tuple of required kwarg names. |

### Constructor

```python
def __init__(self, program: str, cwd: Optional[str] = None)
```

Resolves `program` via `shutil.which`; raises `CommandNotFoundError` if
missing. `cwd` is the subprocess working directory.

### Magic methods

#### `__getattr__(name) -> Callable`

Returns a method that runs `<program> <subcommand> [<options>] [<args>]`
where `subcommand = name.replace('_', '-')`.

```python
git = Git()
result = git.commit(message="Initial commit")
result = git.push(origin=True)
```

#### `__call__(*args, **kwargs)`

Runs `<program> [<options>] [<args>]` directly (no subcommand).

```python
git("--version")            # equivalent to: git --version
```

### Internal helpers (not part of public API)

- `_build_option(key)` — translate kwarg name to `-x` / `--xx`.
- `_append_options(cmd, kwargs)` — fold kwargs into a CLI list.
  `bool` adds the flag alone, `list`/`tuple` repeats the flag per item,
  anything else emits `--flag value`.
- `_check_required_args(subcommand, kwargs)` — raises
  `MissingArgumentError` if a required arg is absent.
- `_run(cmd)` — `subprocess.run(check=True, capture_output=True, text=True)`;
  raises `CommandExecutionError` or `CommandNotFoundError`.

## `Git` `[git.py:4]`

```python
git = Git(cwd="/path/to/repo")
git.status()
git.add(".")
git.commit(message="...")
git.push()
git.pull()
```

| Setting | Value |
| --- | --- |
| `_option_aliases` | `{'empty': 'allow-empty'}` (so `git.commit(empty=True)` becomes `--allow-empty`). |
| `_required_args` | `{'commit': ('message',)}` |

## `Npm` `[npm.py]`

```python
npm = Npm()
npm.install()
npm.install(["lodash", "express"])
npm.run(dev=True)         # → npm run --dev
```

No custom aliases or required args.

## `Pip` `[pip.py]`

```python
pip = Pip()
pip.install("requests")
pip.list()
pip.uninstall("requests", yes=True)    # pip uninstall --yes
```

No custom aliases or required args.

## Usage pattern

```python
from modules.Uui.call import Git, CommandExecutionError

git = Git()
try:
    result = git.status()
    print(result.stdout)
except CommandExecutionError as exc:
    print(f"git failed (rc={exc.returncode}): {exc.stderr}")
```