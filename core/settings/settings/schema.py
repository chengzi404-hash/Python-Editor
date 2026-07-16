"""``modules.settings.schema`` — Default global / project schemas.

Centrally maintains all **built-in** setting metadata for this editor:

* :data:`GLOBAL_SCHEMA` —— Global settings shared across projects (theme, font, auto-save, etc.).
* :data:`PROJECT_SCHEMA` —— Settings that only apply to the currently opened project (interpreter, entry file, checkers).
* :data:`SCHEMA_BY_SCOPE` —— Aggregated by scope for easy direct indexing.

Third-party or user-defined settings can use :class:`SettingsSchema` to assemble custom schemas,
then pass them to :class:`Settings` when creating it.
"""

from __future__ import annotations

from core.settings.i18n import AVAILABLE_LANGUAGES

from .base import (
    SettingSpec,
    SettingsSchema,
    SettingsScope,
    SettingValueType,
)

GLOBAL_SPECS: tuple = (
    SettingSpec(
        key="ui.theme",
        type=SettingValueType.CHOICE,
        default="Dark",
        label="Interface Theme",
        description="Interface theme.",
        choices=("Dark", "Light", "Solarized Dark"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.highlight_theme",
        type=SettingValueType.CHOICE,
        default="Default Dark",
        label="Code Highlight Theme",
        description="Syntax highlighting color scheme.",
        choices=("Default Dark", "Default Light", "Solarized Dark"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.highlight_theme_marketplace",
        type=SettingValueType.BUTTON,
        default=None,
        label="Browse Highlight Themes...",
        description="",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.font_family",
        type=SettingValueType.STRING,
        default="Consolas",
        label="Editor Font",
        description="Monospace font name.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.font_size",
        type=SettingValueType.INTEGER,
        default=10,
        label="Editor Font Size",
        description="Code area font size (pt).",
        min=6,
        max=72,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.show_line_numbers",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Show Line Numbers",
        description="Show line numbers on the left.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.tab_size",
        type=SettingValueType.INTEGER,
        default=4,
        label="Tab Width",
        description="Number of spaces inserted for Tab.",
        min=1,
        max=16,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.use_spaces",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Tab to Spaces",
        description="Insert spaces for Tab (default).",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="Auto Save",
        description="Automatically write to disk after editing stops.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save_delay_ms",
        type=SettingValueType.INTEGER,
        default=800,
        label="Auto Save Delay",
        description="Idle wait time in milliseconds.",
        min=100,
        max=60000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save_format",
        type=SettingValueType.STRING,
        default="{unix.seconds}",
        label="Auto Save File Name Format",
        description="File name format for auto-save of unnamed files. Available fields: {year} {month} {day} {hour} {minute} {second} {unix.seconds} {unix.float}",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.word_wrap",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="Auto Wrap",
        description="Automatically wrap when exceeding boundary.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.highlight_delay_ms",
        type=SettingValueType.INTEGER,
        default=300,
        label="Highlight Delay",
        description="Highlight recalculation delay in milliseconds, 0=no delay.",
        min=0,
        max=5000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.suggestion_delay_ms",
        type=SettingValueType.INTEGER,
        default=200,
        label="Suggestion Delay",
        description=(
            "Delay in milliseconds before triggering suggestions after typing or cursor movement;"
            "only the last one is kept when keys are pressed repeatedly or cursor moves quickly. 0=no delay."
        ),
        min=0,
        max=5000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.large_file_threshold_bytes",
        type=SettingValueType.INTEGER,
        default=5 * 1024 * 1024,
        label="Large File Threshold (bytes)",
        description=(
            "Files exceeding this byte count are treated as large files:"
            "chunked streaming loading is used to avoid UI freezing,"
            "and highlighting and suggestions are automatically disabled to ensure responsiveness."
            "Set to 0 to disable this feature (all files go through the original path)."
        ),
        min=0,
        max=1024 * 1024 * 1024,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Enable Code Completion",
        description="Show suggestions when typing.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.max_suggestions",
        type=SettingValueType.INTEGER,
        default=20,
        label="Max Suggestions",
        description="Maximum number of suggestions.",
        min=1,
        max=200,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.max_visible",
        type=SettingValueType.INTEGER,
        default=8,
        label="Visible Candidates",
        description="Number of visible candidates in dropdown list.",
        min=3,
        max=20,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.auto_trigger",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Auto Trigger Completion",
        description="Trigger automatically when typing.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.min_chars_before_trigger",
        type=SettingValueType.INTEGER,
        default=1,
        label="Min Chars Before Trigger",
        description=(
            "After continuously typing at least this many characters, wait for the suggestion delay before showing the suggestion popup;"
            "the count resets when pausing, moving cursor, or pressing non-character keys."
            "Default 1: triggers on every character input after delay; set higher to delay the popup."
            "Set to 0 to disable auto popup (only manual trigger with Ctrl+Space)."
        ),
        min=0,
        max=20,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.run_on_open",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="Check on Open",
        description="Run check when file is opened.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.run_on_save",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Check on Save",
        description="Run check when file is saved.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.timeout_ms",
        type=SettingValueType.INTEGER,
        default=30000,
        label="Check Timeout",
        description="Check timeout in milliseconds.",
        min=500,
        max=600000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="runner.timeout_ms",
        type=SettingValueType.INTEGER,
        default=30000,
        label="Run Timeout",
        description="Run timeout in milliseconds.",
        min=500,
        max=600000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="runner.clear_output_before_run",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Clear Output Before Run",
        description="Clear output before running.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="runner.stream_output",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Streaming Output",
        description=(
            "Output subprocess stdout/stderr in real-time line by line during execution."
            "When off, output all at once after subprocess completes."
        ),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="startup.restore_files",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Restore Last Opened Files",
        description="Restore files opened in the last session.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="i18n.language",
        type=SettingValueType.CHOICE,
        default="zh_CN",
        label="Interface Language",
        description="Interface language switch. Menu/status bar/dialog text will re-render immediately after change.",
        choices=tuple(AVAILABLE_LANGUAGES),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="i18n.language_marketplace",
        type=SettingValueType.BUTTON,
        default=None,
        label="Browse Languages...",
        description="",
        scope=SettingsScope.GLOBAL,
    ),
    # ── Logging ────────────────────────────────────────────────────────────
    SettingSpec(
        key="logging.enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Enable Logging",
        description="When enabled, records runtime logs to the logs/ directory.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.level",
        type=SettingValueType.CHOICE,
        default="INFO",
        label="Log Level",
        description="Log at this level and above.",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.file_enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Write File Logs",
        description="Write logs to logs/<name>.log file.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.console_enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Output to Console",
        description="Also print logs to stdout.",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.max_bytes",
        type=SettingValueType.INTEGER,
        default=5 * 1024 * 1024,
        label="Log File Max Size",
        description="Maximum bytes per log file, rotates automatically when exceeded.",
        min=1024,
        max=100 * 1024 * 1024,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.backup_count",
        type=SettingValueType.INTEGER,
        default=5,
        label="Log Backup Count",
        description="Number of old log files to keep during rotation.",
        min=1,
        max=100,
        scope=SettingsScope.GLOBAL,
    ),
    # ── Plugins ────────────────────────────────────────────────────────────
    SettingSpec(
        key="plugins.marketplace",
        type=SettingValueType.BUTTON,
        default=None,
        label="Browse Plugin Marketplace...",
        description="",
        scope=SettingsScope.GLOBAL,
    ),
)


GLOBAL_SCHEMA = SettingsSchema(GLOBAL_SPECS)


PROJECT_SPECS: tuple = (
    SettingSpec(
        key="project.python_interpreter",
        type=SettingValueType.PATH,
        default="",
        label="Python Interpreter",
        description="Interpreter path; empty uses system default.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.entry_point",
        type=SettingValueType.PATH,
        default="",
        label="Entry File",
        description="F5 entry file; empty uses current file.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.c_compiler",
        type=SettingValueType.PATH,
        default="gcc",
        label="C Compiler",
        description="C compiler name or absolute path.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.cpp_compiler",
        type=SettingValueType.PATH,
        default="g++",
        label="C++ Compiler",
        description="C++ compiler name or absolute path.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="checker.enabled",
        type=SettingValueType.LIST,
        default=["flake8", "pyright"],
        label="Enabled Checkers",
        description="List of enabled checker IDs.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="checker.ignore",
        type=SettingValueType.LIST,
        default=[],
        label="Ignored Checks",
        description="Ignored checker item IDs (e.g., E501).",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.exclude_paths",
        type=SettingValueType.LIST,
        default=["__pycache__", ".git", ".venv", "venv", "build", "dist"],
        label="Exclude Paths",
        description="Ignored glob paths.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.tab_size",
        type=SettingValueType.INTEGER,
        default=4,
        label="Project Tab Width",
        description="Tab width override; 0=fallback to global.",
        min=0,
        max=16,
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.use_spaces",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Project Tab to Spaces",
        description="Tab to spaces behavior override.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.name",
        type=SettingValueType.STRING,
        default="",
        label="Project Name",
        description="Display name; empty uses directory name.",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.description",
        type=SettingValueType.STRING,
        default="",
        label="Project Description",
        description="For display only, does not affect execution.",
        scope=SettingsScope.PROJECT,
    ),
)


PROJECT_SCHEMA = SettingsSchema(PROJECT_SPECS)


SCHEMA_BY_SCOPE = {
    SettingsScope.GLOBAL: GLOBAL_SCHEMA,
    SettingsScope.PROJECT: PROJECT_SCHEMA,
}


def get_schema(scope: SettingsScope) -> SettingsSchema:
    """Return the built-in :class:`SettingsSchema` for the given scope."""

    return SCHEMA_BY_SCOPE[scope]


__all__ = [
    "GLOBAL_SCHEMA",
    "GLOBAL_SPECS",
    "PROJECT_SCHEMA",
    "PROJECT_SPECS",
    "SCHEMA_BY_SCOPE",
    "get_schema",
]
