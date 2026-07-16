"""Uui command-line scaffolding tool.

Usage:
    python -m Uui.cli new [<project>]        Scaffold a new project (interactive if no name)
    python -m Uui.cli theme <Name>           Generate a custom theme file
    python -m Uui.cli info                   Show package info (themes, components)
    python -m Uui.cli demo                   Launch the built-in gallery
    python -m Uui.cli designer [file.xml]    Launch the visual widget designer
    python -m Uui.cli config [SUBCMD]        Manage global ~/.uui/config.py
"""

import argparse
import importlib.util
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

CONFIG_DIR = Path.home() / ".uui"
CONFIG_FILE = CONFIG_DIR / "config.py"


DEFAULT_CONFIG = '''\
"""Uui global configuration.

This file is auto-loaded by `uui new` and `uui info`. Edits take effect on
the next CLI invocation.
"""
from Uui.widgets import theme


# OS theme mapping: which Uui theme to switch to when the OS appearance
# changes (and `theme.follow_system(...)` is called).
FOLLOW_SYSTEM_THEME = {
    'dark': 'Dark',
    'light': 'Light',
    'default': 'Dark',
}


# Default Uui theme baked into newly scaffolded projects (`uui new`).
DEFAULT_THEME = 'Dark'


# Default window geometry for new projects ("WxH+X+Y" or just "WxH").
DEFAULT_GEOMETRY = '640x420+100+100'


# Prepended verbatim to the generated `main.py` in new projects.
# Define app-level constants (APP_NAME, APP_VERSION, ...) here.
PRELOAD = """
APP_NAME = "MyApp"
APP_VERSION = "0.1.0"
"""


# If True, new projects auto-call theme.follow_system() at startup.
FOLLOW_OS_THEME = False
'''


PROJECT_TEMPLATE = '''\
"""Entry point for {project}."""
{preload}

import tkinter as tk

from Uui import Window
from Uui.widgets import theme
from Uui.widgets import (
    UFrame, ULabel, UButton, UMenuBar,
    UEntry, UText, UCheckButton, URadioButton,
    UComboBox, UProgressBar, USlider,
)


DEFAULT_THEME = '{default_theme}'
DEFAULT_GEOMETRY = '{default_geometry}'

# OS theme mapping baked in from ~/.uui/config.py at scaffold time.
_OS_THEME_MAP = {os_theme_map_repr}

FOLLOW_OS_THEME = {follow_os_bool}


def _apply_startup_theme(window: Window) -> None:
    target = theme.by_name(DEFAULT_THEME)
    if target is not None:
        theme.set_theme(target)
    if FOLLOW_OS_THEME:
        theme.follow_system(window, mapping=_OS_THEME_MAP, poll_interval_ms=2000)


def build(window: Window) -> None:
    menu_bar = UMenuBar(window)
    menu_bar.pack(fill=tk.X)

    file_menu = menu_bar.add_cascade('File')
    file_menu.add_command('Quit', window.destroy, 'Alt+F4')

    body = UFrame(window, variant='base')
    body.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

    ULabel(
        body,
        text=globals().get('APP_NAME', '{project}'),
        font=('Arial', 14, 'bold'), variant='primary',
    ).pack(anchor=tk.W, pady=(0, 4))

    ULabel(
        body,
        text='Edit build() in main.py to design your UI.',
        variant='secondary',
    ).pack(anchor=tk.W, pady=(0, 16))

    UButton(
        body, text='Click me', variant='primary',
        command=lambda: print('clicked'),
    ).pack(anchor=tk.W, pady=4)


def main() -> None:
    window = Window(title=globals().get('APP_NAME', '{project}'))
    window.geometry(DEFAULT_GEOMETRY)
    window.configure(bg=theme.BG_BASE)

    build(window)

    _apply_startup_theme(window)

    window.mainloop()


if __name__ == '__main__':
    main()
'''


THEME_TEMPLATE = '''\
"""Custom theme: {name}.

Edit the colour values below to taste. Anything you leave unset inherits from
the base Theme (Dark).
"""
from Uui.widgets.theme import Theme


class {class_name}(Theme):
    name = '{name}'

    BG_TITLE = '#000000'
    BG_BASE = '#1e1e1e'
    BG_PANEL = '#2a2a2a'
    BG_RAISED = '#3a3a3a'
    BG_HOVER = '#4a4a4a'
    BG_ACTIVE = '#5a5a5a'
    BG_INPUT = '#161616'
    BG_DROPDOWN = '#2a2a2a'

    FG_PRIMARY = '#ffffff'
    FG_SECONDARY = '#a0a0a0'
    FG_TERTIARY = '#707070'
    FG_DISABLED = '#505050'

    BORDER = '#3a3a3a'
    BORDER_STRONG = '#5a5a5a'
    BORDER_FOCUS = '#0a84ff'

    RED = '#ff5f57'
    RED_HOVER = '#ff7f77'
    RED_DARK = '#d94540'

    YELLOW = '#febc2e'
    YELLOW_HOVER = '#ffcc4e'
    YELLOW_DARK = '#cf9a10'

    GREEN = '#28c840'
    GREEN_HOVER = '#4ae060'
    GREEN_DARK = '#1caa30'

    BLUE = '#0a84ff'
    BLUE_HOVER = '#3a9eff'
    BLUE_DARK = '#0066cc'

    PURPLE = '#bf5af2'
'''


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def _write_file(path: str, content: str, *, force: bool = False) -> None:
    if os.path.exists(path) and not force:
        print(f"  ! exists, skipping: {path}  (use --force to overwrite)")
        return
    _ensure_parent(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  + wrote {path}")


def _ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG, encoding="utf-8")


def _load_config(quiet: bool = True):
    _ensure_config()
    spec = importlib.util.spec_from_file_location("uui_user_config", CONFIG_FILE)
    if spec is None or spec.loader is None:
        if not quiet:
            print(f"  ! could not load config spec from {CONFIG_FILE}")
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        if not quiet:
            print(f"  ! failed to load config {CONFIG_FILE}: {e}")
        return None
    return module


def _py_repr(value) -> str:
    return repr(value)


class _C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RED = "\033[31m"
    GRAY = "\033[90m"


def _ansi_supported() -> bool:
    if not (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
        return False
    if sys.platform.startswith("win"):
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
        except Exception:
            return False
    return True


_ANSI = _ansi_supported()


def _c(code: str, text: str) -> str:
    if _ANSI:
        return f"{code}{text}{_C.RESET}"
    return text


def _hr(width: int = 60, char: str = "─") -> str:
    return char * width


def _banner(title: str, subtitle: str = "") -> None:
    inner_w = max(len(title), len(subtitle), 30)
    pad = inner_w + 4
    print()
    print(_c(_C.CYAN, "  ╭" + "─" * pad + "╮"))
    print(_c(_C.CYAN, "  │ ") + _c(_C.BOLD, title.ljust(inner_w)) + _c(_C.CYAN, " │"))
    if subtitle:
        print(_c(_C.CYAN, "  │ ") + _c(_C.DIM, subtitle.ljust(inner_w)) + _c(_C.CYAN, " │"))
    print(_c(_C.CYAN, "  ╰" + "─" * pad + "╯"))


def _step(num: int, total: int, label: str) -> None:
    bar_w = 24
    filled = int(bar_w * num / max(total, 1))
    bar = _c(_C.CYAN, "━" * filled) + _c(_C.GRAY, "━" * (bar_w - filled))
    print()
    print(f"  {bar}  {_c(_C.BOLD, f'Step {num} of {total}')}  {_c(_C.DIM, label)}")


def _summary(rows) -> None:
    label_w = max(len(k) for k, _ in rows)
    value_w = max(len(v) for _, v in rows)
    inner = label_w + value_w + 6
    print()
    print(_c(_C.GRAY, "  ┌" + "─" * (inner + 2) + "┐"))
    print(_c(_C.GRAY, "  │ ") + _c(_C.BOLD, "Summary".ljust(inner)) + _c(_C.GRAY, " │"))
    print(_c(_C.GRAY, "  ├" + "─" * (inner + 2) + "┤"))
    for k, v in rows:
        line = (
            _c(_C.GRAY, "  │ ")
            + _c(_C.GRAY, k.ljust(label_w))
            + "  "
            + _c(_C.CYAN, v.ljust(value_w))
            + "  "
            + _c(_C.GRAY, "│")
        )
        print(line)
    print(_c(_C.GRAY, "  └" + "─" * (inner + 2) + "┘"))


def _success(msg: str) -> None:
    print("  " + _c(_C.GREEN, "✓ ") + msg)


def _info(msg: str) -> None:
    print("  " + _c(_C.DIM, msg))


def _warn(msg: str) -> None:
    print("  " + _c(_C.YELLOW, "! ") + msg)


def _error(msg: str) -> None:
    print("  " + _c(_C.RED, "✗ ") + msg)


def _is_interactive() -> bool:
    return sys.stdin is not None and sys.stdin.isatty() and _ANSI


def _prompt(question: str, default: str = "", *, required: bool = False, validator=None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        try:
            raw = input(
                "  " + _c(_C.YELLOW, "? ") + question + _c(_C.DIM, suffix) + _c(_C.YELLOW, " › ")
            )
        except EOFError:
            return default
        ans = raw.strip()
        if not ans:
            ans = default
        if required and not ans:
            _error("required")
            continue
        if validator and ans:
            try:
                ans = validator(ans)
            except ValueError as e:
                _error(str(e))
                continue
        return ans


def _prompt_choice(question: str, choices: list, default=None, *, index_from: int = 1) -> str:
    if default is None:
        default = choices[0]
    if default not in choices:
        default = choices[0]
    print("  " + _c(_C.YELLOW, "? ") + question)
    for i, choice in enumerate(choices, index_from):
        marker = "›" if choice == default else " "
        line = "     " + _c(_C.CYAN if choice == default else _C.GRAY, marker) + f" {i}) {choice}"
        print(line)
    while True:
        try:
            raw = input(
                "  "
                + _c(_C.YELLOW, "  choice")
                + _c(_C.DIM, f" [{default}]")
                + _c(_C.YELLOW, " › ")
            )
        except EOFError:
            return default
        ans = raw.strip()
        if not ans:
            return default
        if ans in choices:
            return ans
        try:
            idx = int(ans)
            if index_from <= idx < index_from + len(choices):
                return choices[idx - index_from]
        except ValueError:
            pass
        _error(f"enter a number 1-{len(choices)} or one of: {', '.join(choices)}")


def _prompt_yes_no(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            raw = input(
                "  "
                + _c(_C.YELLOW, "? ")
                + question
                + _c(_C.DIM, f" {suffix}")
                + _c(_C.YELLOW, " › ")
            )
        except EOFError:
            return default
        ans = raw.strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        _error("answer 'y' or 'n'")


def _validate_identifier(value: str) -> str:
    if not value.isidentifier():
        raise ValueError(f"{value!r} is not a valid Python identifier")
    return value


def _validate_geometry(value: str) -> str:
    if not re.match(r"^\d{2,5}x\d{2,5}([+-]\d+[+-]\d+)?$", value):
        raise ValueError("use WxH or WxH+X+Y (e.g. 800x600 or 800x600+100+100)")
    return value


def _detect_vcs_tools() -> list:
    import shutil

    found = []
    for tool in ("git", "svn"):
        if shutil.which(tool):
            found.append(tool)
    return found


def _probe_python(path: str) -> str:
    """Return a 'X.Y.Z' version string for a python executable, or ''."""
    try:
        r = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return ""
    out = (r.stdout or r.stderr or "").strip()
    if out.lower().startswith("python "):
        out = out[7:]
    m = re.search(r"\d+\.\d+(?:\.\d+)?", out)
    return m.group(0) if m else ""


def _conda_flavor(conda_path: str) -> tuple:
    """Return ('anaconda' | 'miniconda' | 'conda', default_python_version)."""
    kind = "conda"
    py_ver = ""
    try:
        r = subprocess.run(
            [conda_path, "info", "--root"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        root = (r.stdout or "").strip().lower()
        if "miniconda" in root:
            kind = "miniconda"
        elif "anaconda" in root:
            kind = "anaconda"
    except Exception:
        pass
    try:
        r = subprocess.run(
            [conda_path, "run", "-n", "base", "python", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        out = (r.stdout or r.stderr or "").strip()
        if out.lower().startswith("python "):
            py_ver = out[7:].split()[0]
    except Exception:
        pass
    return kind, py_ver


def _detect_python_envs() -> list:
    """Find python interpreters and conda. Returns list of choice dicts."""
    import shutil

    found = []
    seen = set()

    try:
        canonical = os.path.realpath(sys.executable)
    except Exception:
        canonical = sys.executable
    seen.add(canonical)
    ver = _probe_python(sys.executable)
    if ver:
        found.append(
            {
                "kind": "venv",
                "path": canonical,
                "label": f"venv  (python {ver})",
                "short": f"python {ver}",
                "source": sys.executable,
            }
        )

    for name in ("python", "python3", "py"):
        path = shutil.which(name)
        if not path:
            continue
        try:
            resolved = os.path.realpath(path)
        except Exception:
            resolved = path
        if resolved in seen:
            continue
        ver = _probe_python(path)
        if not ver:
            continue
        seen.add(resolved)
        label = f"venv  (python {ver})" if name == "python" else f"venv via {name}  (python {ver})"
        found.append(
            {
                "kind": "venv",
                "path": resolved,
                "label": label,
                "short": f"python {ver}",
                "source": name,
            }
        )

    conda_path = shutil.which("conda")
    if conda_path:
        kind, py_ver = _conda_flavor(conda_path)
        label = f"{kind}  (conda)"
        if py_ver:
            label += f"  python {py_ver}"
        found.append(
            {
                "kind": "conda",
                "path": conda_path,
                "label": label,
                "short": kind,
                "flavor": kind,
            }
        )
    return found


def _create_python_env(project_dir: str, choice: dict) -> None:
    if choice is None:
        return
    if choice["kind"] == "venv":
        _create_venv(project_dir, choice["path"])
    elif choice["kind"] == "conda":
        _create_conda(project_dir, choice["path"])


def _create_venv(project_dir: str, python_path: str) -> None:
    venv_path = os.path.join(project_dir, ".venv")
    if os.path.isdir(venv_path):
        _warn(".venv already exists, skipping venv creation")
        return
    _info(f"creating venv via {python_path} ...")
    try:
        subprocess.run(
            [python_path, "-m", "venv", venv_path],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        _warn(f"python not found at {python_path}")
        return
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        _warn(f"venv creation failed: {stderr.strip() or e}")
        return
    ver = _probe_python(python_path)
    _success(f"created venv at .venv/  (python {ver})")
    _activate_hint(venv_path)


def _create_conda(project_dir: str, conda_path: str) -> None:
    env_path = os.path.abspath(os.path.join(project_dir, ".venv"))
    if os.path.isdir(env_path):
        _warn(".venv already exists, skipping conda env creation")
        return
    _info(f"creating conda env at {env_path} ...")
    try:
        subprocess.run(
            [conda_path, "create", "--prefix", env_path, "python", "-y"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        _warn(f"conda not found at {conda_path}")
        return
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        _warn(f"conda create failed: {stderr.strip() or e}")
        return
    _success("created conda env at .venv/")
    _activate_hint(env_path, conda=True)


def _activate_hint(env_path: str, *, conda: bool = False) -> None:
    print()
    print("  " + _c(_C.BOLD, "Next:"))
    if conda:
        print("    " + _c(_C.CYAN, f"conda activate {env_path}"))
    elif sys.platform.startswith("win"):
        print("    " + _c(_C.CYAN, r".venv\Scripts\activate"))
    else:
        print("    " + _c(_C.CYAN, "source .venv/bin/activate"))
    print("    " + _c(_C.CYAN, "pip install -e <Uui source dir>"))


GITIGNORE_TEMPLATE = """\
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.eggs/
build/
dist/

# Virtual environments
.venv/
venv/
env/

# Environment / secrets
.env
.env.local

# IDE / editors
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
desktop.ini
"""


def _init_git(project_dir: str) -> None:
    gitignore_path = os.path.join(project_dir, ".gitignore")
    with open(gitignore_path, "w", encoding="utf-8") as f:
        f.write(GITIGNORE_TEMPLATE)
    _success("wrote .gitignore")
    try:
        subprocess.run(["git", "init", "-q"], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=project_dir, check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=uui@local",
                "-c",
                "user.name=Uui Scaffold",
                "commit",
                "-q",
                "-m",
                "Initial scaffold from Uui",
            ],
            cwd=project_dir,
            check=True,
            capture_output=True,
        )
        _success("git repo initialised with first commit")
    except FileNotFoundError:
        _warn("git is not on PATH — .gitignore was written but no commit was made")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace").strip() if e.stderr else ""
        _warn(f"git step failed: {stderr or e}")


def _init_svn(project_dir: str) -> None:
    repo_path = os.path.abspath(os.path.join(project_dir, ".svnrepo"))
    if os.path.isdir(repo_path):
        _warn(f"{repo_path} already exists, skipping svn setup")
        return
    try:
        subprocess.run(["svnadmin", "create", repo_path], check=True, capture_output=True)
    except FileNotFoundError:
        _warn("svn (svnadmin) is not on PATH — no repo created")
        return
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace").strip() if e.stderr else ""
        _warn(f"svnadmin create failed: {stderr or e}")
        return

    repo_url = "file:///" + repo_path.replace("\\", "/").lstrip("/")

    _success("created local SVN repo at .svnrepo/")
    print()
    print("  " + _c(_C.BOLD, "To start working with it:"))
    print(
        "    "
        + _c(
            _C.CYAN,
            f'svn mkdir {repo_url}/trunk {repo_url}/branches {repo_url}/tags -m "create layout"',
        )
    )
    print("    " + _c(_C.CYAN, f"svn checkout {repo_url}/trunk {project_dir}-wc"))
    print("    " + _c(_C.CYAN, f"cp {project_dir}/* {project_dir}-wc/"))
    print("    " + _c(_C.CYAN, f'svn add {project_dir}-wc && svn commit -m "initial scaffold"'))


def cmd_new(args: argparse.Namespace) -> int:
    if args.name:
        return _new_noninteractive(args)
    if not _is_interactive():
        _error("no project name given and stdin is not a TTY")
        _info("usage: python -m Uui.cli new <project_name>")
        return 1
    return _new_interactive(args)


def _new_interactive(args: argparse.Namespace) -> int:
    from .widgets import theme as _theme

    cfg = _load_config() or type("_Defaults", (), {})()
    available_themes = [t.name for t in _theme.available()]

    cfg_default_theme = getattr(cfg, "DEFAULT_THEME", "Dark")
    if cfg_default_theme not in available_themes:
        cfg_default_theme = available_themes[0]

    cfg_geometry = getattr(cfg, "DEFAULT_GEOMETRY", "640x420+100+100")
    cfg_follow_os = bool(getattr(cfg, "FOLLOW_OS_THEME", False))

    _banner("Uui  ✿  Project Setup", "Let's scaffold your first app.")

    vcs_tools = _detect_vcs_tools()
    python_envs = _detect_python_envs()
    total_steps = 5 + (1 if python_envs else 0) + (1 if vcs_tools else 0)

    _step(1, total_steps, "Project name")
    project = _prompt(
        "Project name (a Python identifier)",
        default="myapp",
        required=True,
        validator=_validate_identifier,
    )

    _step(2, total_steps, "Window title")
    title = _prompt("Window title", default=project.capitalize())

    _step(3, total_steps, "Default theme")
    default_theme = _prompt_choice("Default Uui theme", available_themes, default=cfg_default_theme)

    _step(4, total_steps, "Window geometry")
    geometry = _prompt("Window geometry", default=cfg_geometry, validator=_validate_geometry)

    _step(5, total_steps, "OS theme follow")
    follow_os = _prompt_yes_no("Follow OS theme at runtime?", default=cfg_follow_os)

    env_choice = None
    if python_envs:
        env_step = 5 + 1
        _step(env_step, total_steps, "Python environment")
        env_labels = ["none"] + [c["label"] for c in python_envs]
        env_default_label = python_envs[0]["label"]
        picked = _prompt_choice(
            "Set up a Python virtual environment?",
            env_labels,
            default=env_default_label,
        )
        if picked != "none":
            env_choice = next((c for c in python_envs if c["label"] == picked), None)
    else:
        _info("No Python interpreter detected on PATH — skipping venv setup.")

    if vcs_tools:
        vcs_step = total_steps
        _step(vcs_step, total_steps, "Version control")
        vcs_choices = [*vcs_tools, "none"]
        vcs_default = vcs_tools[0]
        vcs = _prompt_choice("Initialise a version-control repo?", vcs_choices, default=vcs_default)
    else:
        vcs = "none"
        _info("No git or svn detected on PATH — skipping VCS setup.")

    env_display = env_choice["short"] if env_choice else "none"

    _summary(
        [
            ("Project", project),
            ("Title", title),
            ("Theme", default_theme),
            ("Geometry", geometry),
            ("Follow OS", "yes" if follow_os else "no"),
            ("Python env", env_display),
            ("VCS", vcs if vcs != "none" else "none"),
            ("Config", str(CONFIG_FILE)),
        ]
    )

    print()
    if not _prompt_yes_no("Create this project?", default=True):
        _warn("Aborted.")
        return 0

    return _new_apply(
        name=project,
        title=title,
        theme=default_theme,
        geometry=geometry,
        follow_os=follow_os,
        env_choice=env_choice,
        vcs=vcs,
        force=args.force,
        silent=False,
    )


def _new_noninteractive(args: argparse.Namespace) -> int:
    project = args.name
    if not project.isidentifier():
        _error(f"{project!r} is not a valid Python identifier")
        return 1

    cfg = _load_config() or type("_Defaults", (), {})()
    title = project.capitalize()
    vcs_tools = _detect_vcs_tools()
    vcs = vcs_tools[0] if vcs_tools else "none"
    python_envs = _detect_python_envs()
    env_choice = python_envs[0] if python_envs else None
    return _new_apply(
        name=project,
        title=title,
        theme=getattr(cfg, "DEFAULT_THEME", "Dark"),
        geometry=getattr(cfg, "DEFAULT_GEOMETRY", "640x420+100+100"),
        follow_os=bool(getattr(cfg, "FOLLOW_OS_THEME", False)),
        env_choice=env_choice,
        vcs=vcs,
        force=args.force,
        silent=True,
    )


def _new_apply(
    *,
    name: str,
    title: str,
    theme: str,
    geometry: str,
    follow_os: bool,
    env_choice,
    vcs: str,
    force: bool,
    silent: bool,
) -> int:
    cfg = _load_config() or type("_Defaults", (), {})()
    preload = getattr(cfg, "PRELOAD", "\n") or "\n"
    os_map = getattr(
        cfg, "FOLLOW_SYSTEM_THEME", {"dark": "Dark", "light": "Light", "default": "Dark"}
    )

    if os.path.exists(name) and not force:
        _error(f"directory already exists: {name}  (use --force to merge)")
        return 1

    os.makedirs(name, exist_ok=True)

    if not silent:
        print()
        _info(f"Creating {name}/")

    main_content = PROJECT_TEMPLATE.format(
        project=name,
        preload=preload.rstrip() + "\n",
        default_theme=theme,
        default_geometry=geometry,
        os_theme_map_repr=_py_repr(dict(os_map)),
        follow_os_bool=_py_repr(bool(follow_os)),
    )

    main_path = os.path.join(name, "main.py")
    readme_path = os.path.join(name, "README.md")

    _write_file(main_path, main_content, force=force)
    _write_file(readme_path, _project_readme(name, theme), force=force)

    if silent:
        print()
        print("Baked-in settings (from ~/.uui/config.py):")
        print(f"  DEFAULT_THEME    = {theme!r}")
        print(f"  DEFAULT_GEOMETRY = {geometry!r}")
        print(f"  FOLLOW_OS_THEME  = {follow_os!r}")
        print(f"  _OS_THEME_MAP    = {dict(os_map)!r}")
        env_disp = env_choice["short"] if env_choice else "none"
        print(f"  PYTHON_ENV       = {env_disp!r}")
        print(f"  VCS              = {vcs!r}")
        print()
        print("Next steps:")
        print(f"  cd {name}")
        print("  python main.py")
    else:
        print()
        _success(f"Project ready at {_c(_C.BOLD, name + '/')}")

        if env_choice is not None:
            _create_python_env(name, env_choice)

        if vcs == "git":
            _init_git(name)
        elif vcs == "svn":
            _init_svn(name)

        print()
        print("  " + _c(_C.BOLD, "Next:"))
        print("    " + _c(_C.CYAN, f"cd {name}"))
        if env_choice is not None and env_choice["kind"] == "venv":
            if sys.platform.startswith("win"):
                print("    " + _c(_C.CYAN, r".venv\Scripts\activate"))
            else:
                print("    " + _c(_C.CYAN, "source .venv/bin/activate"))
        elif env_choice is not None and env_choice["kind"] == "conda":
            print(
                "    "
                + _c(_C.CYAN, f"conda activate {os.path.abspath(os.path.join(name, '.venv'))}")
            )
        print("    " + _c(_C.CYAN, "python main.py"))
        print()
        _info("edit main.py's build() function to design your UI")
    return 0


def _project_readme(project: str, default_theme: str) -> str:
    return textwrap.dedent(f"""\
        # {project}

        A Uui-based Tkinter application.

        ## Run

        ```
        python main.py
        ```

        ## Settings

        The starter was generated with these values baked in (from your
        `~/.uui/config.py` at scaffold time):

        - `DEFAULT_THEME = {default_theme!r}` — theme applied on startup.
        - `FOLLOW_OS_THEME` — set to `True` in `main.py` to follow the OS
          appearance automatically.

        Edit those constants in `main.py` to change behaviour without
        re-scaffolding.

        ## Generating more themes

        ```
        python -m Uui.cli theme MyTheme
        ```
    """)


def cmd_theme(args: argparse.Namespace) -> int:
    name = args.name
    if not name.isidentifier():
        print(f"  ! theme name must be a valid Python identifier: {name!r}")
        return 1
    out_path = f"{name.lower()}_theme.py"
    class_name = name if name[:1].isupper() else name.capitalize()
    if not class_name.endswith("Theme"):
        class_name = class_name + "Theme"

    content = THEME_TEMPLATE.format(name=name, class_name=class_name)
    _write_file(out_path, content, force=args.force)
    print()
    print("Usage:")
    print(f"  from {os.path.splitext(out_path)[0]} import {class_name}")
    print("  from Uui.widgets import theme")
    print(f"  theme.set_theme({class_name}(), refresh_root=root)")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    from . import widgets
    from .widgets import theme

    print("Uui  —  Component Gallery")
    print()

    cfg = _load_config()
    user_os_map = getattr(cfg, "FOLLOW_SYSTEM_THEME", None) if cfg else None
    default_os_map = dict(theme.FOLLOW_SYSTEM_THEME)

    print("Built-in themes:")
    for t in theme.available():
        marker = "*" if t is theme.current() else " "
        print(f"  {marker} {t.name}")

    print()
    print("Components:")
    names = sorted(n for n in dir(widgets) if n[:1].isupper() and not n.startswith("_"))
    for n in names:
        print(f"  - {n}")

    print()
    print("OS theme follow mapping:")
    src = "user" if user_os_map else "default"
    mapping = user_os_map if user_os_map else default_os_map
    print(f"  source: {src}  ({CONFIG_FILE})")
    for k, v in mapping.items():
        resolved = theme.by_name(v)
        flag = "ok" if resolved else "!! missing theme"
        print(f"    {k!r:>10} -> {v!r:<20} [{flag}]")

    print()
    print("Current theme:", theme.current().name)
    print("OS theme    :", theme._read_os_theme() or "(unknown)")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    from . import demo

    demo.main()
    return 0


def cmd_designer(args: argparse.Namespace) -> int:
    from .tool.designer import main as _designer_main

    _designer_main(args.file)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if getattr(args, "init", False):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(DEFAULT_CONFIG, encoding="utf-8")
        print(f"  + wrote {CONFIG_FILE}")
        return 0

    if getattr(args, "reset", False):
        if CONFIG_FILE.exists() and not args.force:
            print(f"  ! config exists: {CONFIG_FILE}  (use --force to overwrite)")
            return 1
        CONFIG_FILE.write_text(DEFAULT_CONFIG, encoding="utf-8")
        print(f"  + reset {CONFIG_FILE}")
        return 0

    if getattr(args, "path", False):
        print(CONFIG_FILE)
        return 0

    if getattr(args, "edit", False):
        _ensure_config()
        editor = os.environ.get("EDITOR") or (
            "notepad" if sys.platform.startswith("win") else "nano"
        )
        try:
            subprocess.Popen([editor, str(CONFIG_FILE)])
        except FileNotFoundError:
            print(f"  ! editor not found: {editor}")
            print(f"  open manually: {CONFIG_FILE}")
            return 1
        print(f"  opened {CONFIG_FILE} in {editor}")
        return 0

    print(f"Uui global config: {CONFIG_FILE}")
    print()
    module = _load_config(quiet=False)
    if module is None:
        return 1

    sections = [
        ("FOLLOW_SYSTEM_THEME", "OS theme mapping"),
        ("DEFAULT_THEME", "Default Uui theme for new projects"),
        ("DEFAULT_GEOMETRY", "Default window geometry for new projects"),
        ("FOLLOW_OS_THEME", "New projects auto-follow OS theme"),
        ("PRELOAD", "Constants prepended to new project main.py"),
    ]
    for attr, desc in sections:
        if hasattr(module, attr):
            value = getattr(module, attr)
            print(f"{attr}  —  {desc}")
            print(f"  = {value!r}")
            print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="uui",
        description="Uui widget kit — scaffolding and tooling.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_new = sub.add_parser("new", help="create a new project skeleton")
    p_new.add_argument(
        "name",
        nargs="?",
        help="project name (Python identifier); omit to launch the interactive onboarding",
    )
    p_new.add_argument("--force", action="store_true", help="overwrite files when they exist")
    p_new.set_defaults(func=cmd_new)

    p_theme = sub.add_parser("theme", help="generate a custom theme file")
    p_theme.add_argument("name", help="theme name (Python identifier)")
    p_theme.add_argument("--force", action="store_true", help="overwrite existing file")
    p_theme.set_defaults(func=cmd_theme)

    p_info = sub.add_parser("info", help="list themes and components")
    p_info.set_defaults(func=cmd_info)

    p_demo = sub.add_parser("demo", help="launch the component gallery")
    p_demo.set_defaults(func=cmd_demo)

    p_designer = sub.add_parser("designer", help="launch the visual widget designer")
    p_designer.add_argument("file", nargs="?", help=".xml project file")
    p_designer.set_defaults(func=cmd_designer)

    p_cfg = sub.add_parser("config", help="manage ~/.uui/config.py")
    p_cfg.add_argument("--show", action="store_true", help="show current config (default)")
    p_cfg.add_argument("--init", action="store_true", help="create config if missing")
    p_cfg.add_argument("--reset", action="store_true", help="overwrite config with defaults")
    p_cfg.add_argument("--path", action="store_true", help="print config file path")
    p_cfg.add_argument("--edit", action="store_true", help="open config in $EDITOR")
    p_cfg.add_argument("--force", action="store_true", help="force overwrite on --reset")
    p_cfg.set_defaults(func=cmd_config)

    p_web = sub.add_parser("web", help="Uui.web commands (new / runserver / ...)")
    p_web.set_defaults(func=_dispatch_web)
    p_web.add_argument(
        "web_args", nargs=argparse.REMAINDER, help="arguments forwarded to `Uui.web.cli`"
    )

    return p


def _dispatch_web(args: argparse.Namespace) -> int:
    from .web.cli import main as _web_main

    return _web_main(args.web_args or ["--help"])


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
