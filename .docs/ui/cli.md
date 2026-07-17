# `ui.cli`

**Source**: [`ui/cli.py`](../../ui/cli.py) — 1 169 lines.

Command-line scaffolding tool for `ui`-based projects.

## Usage

```bash
python -m ui.cli new [<project>]        # Scaffold a new project (interactive if no name)
python -m ui.cli theme <Name>           # Generate a custom theme file
python -m ui.cli info                   # Show package info (themes, components)
python -m ui.cli demo                   # Launch the built-in gallery
python -m ui.cli designer [file.xml]    # Launch the visual widget designer
python -m ui.cli config [SUBCMD]        # Manage global ~/.uui/config.py
python -m ui.cli web ...                # Forward to `python -m ui.web`
```

## Subcommands

### `new [<project>]`

Scaffold a new project skeleton. If a project name is given, runs
non-interactively. Otherwise drops into an interactive wizard that
walks through:

1. Project name (Python identifier).
2. Window title.
3. Default Uui theme.
4. Window geometry (`WxH` or `WxH+X+Y`).
5. Whether to follow OS theme at runtime.
6. Optional Python virtual environment (`venv` or `conda`).
7. Optional version control (`git` or `svn`).

The generated `main.py` reads these settings from `~/.uui/config.py` at
scaffold time and bakes them in as constants.

| Flag | Effect |
| --- | --- |
| `--force` | Overwrite files that already exist. |

### `theme <Name>`

Generate `<name>_theme.py` containing a `Theme` subclass ready to be
imported. The class is named `<Name>Theme` (capitalised + suffixed).

```bash
python -m ui.cli theme SolarizedLight
# -> Solarizedlight_theme.py with `class SolarizedLightTheme(Theme)`
```

### `info`

Print a report of:

- Built-in themes (with `*` next to the active one).
- All public widget classes exported from `ui.widgets`.
- The OS theme mapping from `~/.uui/config.py` (or the built-in default).
- The currently active theme and the detected OS theme.

### `demo`

Launch the component gallery — equivalent to
`python -m ui.demo` / `python -c "from ui.demo import main; main()"`.

### `designer [file.xml]`

Launch the visual widget designer; optionally pre-load an XML scene.

### `config [SUBCMD]`

Manage `~/.uui/config.py`. Subcommands:

| Subcommand | Description |
| --- | --- |
| `--show` (default) | Print the current config. |
| `--init` | Create `~/.uui/config.py` if missing. |
| `--reset` | Overwrite `~/.uui/config.py` with defaults. |
| `--path` | Print the config file path. |
| `--edit` | Open the config in `$EDITOR` (or `notepad` on Windows). |
| `--force` | Force overwrite on `--reset`. |

### `web ...`

Forwards all remaining arguments to `python -m ui.web`. Useful for
combining scaffold + serve workflows:

```bash
python -m ui.cli new mysite
python -m ui.cli web runserver mysite
```

## Public surface

`ui.cli` exposes `build_parser()` for embedding the CLI inside another
program:

```python
from ui.cli import build_parser, main

parser = build_parser()
args = parser.parse_args(["info"])
exit_code = args.func(args)
```

`main(argv=None)` is the standard `argparse`-style entry point that
returns an exit code (use `sys.exit(main(...))` for command-line use).