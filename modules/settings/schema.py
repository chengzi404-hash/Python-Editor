"""``modules.settings.schema`` — 默认的全局 / 项目 Schema。

集中维护本编辑器**内置**的全部设置项元信息：

* :data:`GLOBAL_SCHEMA` —— 跨项目共享的全局设置（主题、字体、自动保存等）。
* :data:`PROJECT_SCHEMA` —— 仅作用于当前打开项目的设置（解释器、入口文件、checkers）。
* :data:`SCHEMA_BY_SCOPE` —— 按作用域聚合，方便直接索引。

第三方或用户自定义的设置项，可使用 :class:`SettingsSchema` 自行组装，
然后在创建 :class:`Settings` 时传入自定义 schema。
"""

from __future__ import annotations

from modules.i18n import AVAILABLE_LANGUAGES

from .base import (
    SettingsSchema,
    SettingsScope,
    SettingSpec,
    SettingValueType,
)




GLOBAL_SPECS: tuple = (
    SettingSpec(
        key="ui.theme",
        type=SettingValueType.CHOICE,
        default="Dark",
        label="界面主题",
        description="界面主题。",
        choices=("Dark", "Light", "Solarized Dark"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.highlight_theme",
        type=SettingValueType.CHOICE,
        default="Default Dark",
        label="代码高亮主题",
        description="语法高亮配色方案。",
        choices=("Default Dark", "Default Light", "Solarized Dark"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.highlight_theme_marketplace",
        type=SettingValueType.BUTTON,
        default=None,
        label="浏览高亮主题市场...",
        description="",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.font_family",
        type=SettingValueType.STRING,
        default="Consolas",
        label="编辑器字体",
        description="等宽字体名。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.font_size",
        type=SettingValueType.INTEGER,
        default=10,
        label="编辑器字号",
        description="代码区字号(pt)。",
        min=6,
        max=72,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.show_line_numbers",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="显示行号",
        description="左侧显示行号。",
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="editor.tab_size",
        type=SettingValueType.INTEGER,
        default=4,
        label="Tab 宽度",
        description="Tab 插入空格数。",
        min=1,
        max=16,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.use_spaces",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Tab 转空格",
        description="Tab 插入空格(默认)。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="自动保存",
        description="编辑停止自动写盘。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save_delay_ms",
        type=SettingValueType.INTEGER,
        default=800,
        label="自动保存延迟",
        description="空闲等待毫秒。",
        min=100,
        max=60000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save_format",
        type=SettingValueType.STRING,
        default="{unix.seconds}",
        label="自动保存文件名格式",
        description="未命名文件自动保存时的文件名格式。可用字段: {year} {month} {day} {hour} {minute} {second} {unix.seconds} {unix.float}",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.word_wrap",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="自动换行",
        description="超界自动换行。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.highlight_delay_ms",
        type=SettingValueType.INTEGER,
        default=300,
        label="高亮延迟",
        description="高亮重算延迟毫秒,0=无延迟。",
        min=0,
        max=5000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.suggestion_delay_ms",
        type=SettingValueType.INTEGER,
        default=200,
        label="建议延迟",
        description=(
            "输入或光标主动移动后,触发建议的延迟毫秒;"
            "快速连续按键/移动时只保留最后一次。0=无延迟。"
        ),
        min=0,
        max=5000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.large_file_threshold_bytes",
        type=SettingValueType.INTEGER,
        default=5 * 1024 * 1024,
        label="大文件阈值(字节)",
        description=(
            "超过该字节数的文件会被视为大文件:"
            "采用分块流式加载避免 UI 冻结,"
            "并自动关闭高亮与建议以保证响应速度。"
            "设为 0 关闭此特性(所有文件走原始路径)。"
        ),
        min=0,
        max=1024 * 1024 * 1024,
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="completion.enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="启用代码补全",
        description="键入弹出建议。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.max_suggestions",
        type=SettingValueType.INTEGER,
        default=20,
        label="最大建议数",
        description="建议上限条数。",
        min=1,
        max=200,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.max_visible",
        type=SettingValueType.INTEGER,
        default=8,
        label="候选条数",
        description="下拉列表可见候选条数。",
        min=3,
        max=20,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.auto_trigger",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="自动触发补全",
        description="键入自动触发。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.min_chars_before_trigger",
        type=SettingValueType.INTEGER,
        default=1,
        label="触发补全的最小连续字符数",
        description=(
            "连续输入不少于该字符数后,等待建议延迟才弹出建议窗口;"
            "在停顿、移动光标或非字符按键时会重置计数。"
            "默认 1:每次输入字符都会按延迟触发;设为更大的值可延迟弹出。"
            "设为 0 禁用自动弹窗(只能通过 Ctrl+Space 手动触发)。"
        ),
        min=0,
        max=20,
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="checker.run_on_open",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="打开时检查",
        description="打开时检查。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.run_on_save",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="保存时检查",
        description="保存时检查。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.timeout_ms",
        type=SettingValueType.INTEGER,
        default=30000,
        label="检查超时",
        description="检查超时毫秒。",
        min=500,
        max=600000,
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="runner.timeout_ms",
        type=SettingValueType.INTEGER,
        default=30000,
        label="运行超时",
        description="运行超时毫秒。",
        min=500,
        max=600000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="runner.clear_output_before_run",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="运行前清空输出",
        description="运行前清空输出。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="runner.stream_output",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="流式输出",
        description=(
            "运行时按行实时输出子进程 stdout/stderr。"
            "关闭后等待子进程结束再一次性输出。"
        ),
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="startup.restore_files",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="恢复上次打开的文件",
        description="恢复上次打开的文件。",
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="i18n.language",
        type=SettingValueType.CHOICE,
        default="zh_CN",
        label="界面语言",
        description="界面语言切换。修改后菜单/状态栏/对话框文案会立即重渲。",
        choices=tuple(AVAILABLE_LANGUAGES),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="i18n.language_marketplace",
        type=SettingValueType.BUTTON,
        default=None,
        label="浏览语言市场...",
        description="",
        scope=SettingsScope.GLOBAL,
    ),

    # ── 日志 ────────────────────────────────────────────────────────────
    SettingSpec(
        key="logging.enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="启用日志",
        description="开启后记录运行日志到 logs/ 目录。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.level",
        type=SettingValueType.CHOICE,
        default="INFO",
        label="日志级别",
        description="记录该级别及以上的日志。",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.file_enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="写文件日志",
        description="将日志写入 logs/<name>.log 文件。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.console_enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="输出到控制台",
        description="同时将日志打印到 stdout。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.max_bytes",
        type=SettingValueType.INTEGER,
        default=5 * 1024 * 1024,
        label="日志文件大小上限",
        description="单个日志文件最大字节数，超出后自动轮转。",
        min=1024,
        max=100 * 1024 * 1024,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="logging.backup_count",
        type=SettingValueType.INTEGER,
        default=5,
        label="日志备份数量",
        description="轮转时保留的旧日志文件数量。",
        min=1,
        max=100,
        scope=SettingsScope.GLOBAL,
    ),

    # ── 插件 ────────────────────────────────────────────────────────────
    SettingSpec(
        key="plugins.marketplace",
        type=SettingValueType.BUTTON,
        default=None,
        label="浏览插件市场...",
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
        label="Python 解释器",
        description="解释器路径;空用系统默认。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.entry_point",
        type=SettingValueType.PATH,
        default="",
        label="入口文件",
        description="F5 入口文件;空用当前文件。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.c_compiler",
        type=SettingValueType.PATH,
        default="gcc",
        label="C 编译器",
        description="C 编译器名或绝对路径。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.cpp_compiler",
        type=SettingValueType.PATH,
        default="g++",
        label="C++ 编译器",
        description="C++ 编译器名或绝对路径。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="checker.enabled",
        type=SettingValueType.LIST,
        default=["flake8", "pyright"],
        label="启用的检查器",
        description="启用的检查器 ID 列表。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="checker.ignore",
        type=SettingValueType.LIST,
        default=[],
        label="忽略的检查项",
        description="忽略的检查项 ID(如 E501)。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="project.exclude_paths",
        type=SettingValueType.LIST,
        default=["__pycache__", ".git", ".venv", "venv", "build", "dist"],
        label="排除路径",
        description="忽略的 glob 路径。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="project.tab_size",
        type=SettingValueType.INTEGER,
        default=4,
        label="项目 Tab 宽度",
        description="Tab 宽度覆盖;0=回退全局。",
        min=0,
        max=16,
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.use_spaces",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="项目 Tab 转空格",
        description="Tab 转空格行为覆盖。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="project.name",
        type=SettingValueType.STRING,
        default="",
        label="项目名称",
        description="显示名;空用目录名。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.description",
        type=SettingValueType.STRING,
        default="",
        label="项目描述",
        description="仅展示,不影响运行。",
        scope=SettingsScope.PROJECT,
    ),
)


PROJECT_SCHEMA = SettingsSchema(PROJECT_SPECS)




SCHEMA_BY_SCOPE = {
    SettingsScope.GLOBAL: GLOBAL_SCHEMA,
    SettingsScope.PROJECT: PROJECT_SCHEMA,
}


def get_schema(scope: SettingsScope) -> SettingsSchema:
    """根据作用域返回内置 :class:`SettingsSchema`。"""

    return SCHEMA_BY_SCOPE[scope]


__all__ = [
    "GLOBAL_SPECS",
    "GLOBAL_SCHEMA",
    "PROJECT_SPECS",
    "PROJECT_SCHEMA",
    "SCHEMA_BY_SCOPE",
    "get_schema",
]