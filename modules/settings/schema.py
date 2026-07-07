"""``modules.settings.schema`` — 默认的全局 / 项目 Schema。

集中维护本编辑器**内置**的全部设置项元信息：

* :data:`GLOBAL_SCHEMA` —— 跨项目共享的全局设置（主题、字体、自动保存等）。
* :data:`PROJECT_SCHEMA` —— 仅作用于当前打开项目的设置（解释器、入口文件、checkers）。
* :data:`SCHEMA_BY_SCOPE` —— 按作用域聚合，方便直接索引。

第三方或用户自定义的设置项，可使用 :class:`SettingsSchema` 自行组装，
然后在创建 :class:`Settings` 时传入自定义 schema。
"""

from __future__ import annotations

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
        description="编辑器界面所使用的主题。",
        choices=("Dark", "Light", "Solarized Dark"),
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.font_family",
        type=SettingValueType.STRING,
        default="Consolas",
        label="编辑器字体",
        description="代码区使用的等宽字体名称。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.font_size",
        type=SettingValueType.INTEGER,
        default=10,
        label="编辑器字号",
        description="代码区字号（pt）。",
        min=6,
        max=72,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="ui.show_line_numbers",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="显示行号",
        description="在编辑器左侧显示行号。",
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="editor.tab_size",
        type=SettingValueType.INTEGER,
        default=4,
        label="Tab 宽度",
        description="按一次 Tab 键插入的空格数。",
        min=1,
        max=16,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.use_spaces",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="Tab 转空格",
        description="True 时按 Tab 会插入空格；False 时插入制表符。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="自动保存",
        description="编辑停止后自动将改动写回磁盘。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.auto_save_delay_ms",
        type=SettingValueType.INTEGER,
        default=800,
        label="自动保存延迟",
        description="自动保存的空闲等待时间（毫秒）。",
        min=100,
        max=60000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="editor.word_wrap",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="自动换行",
        description="超出右边界时是否自动换行。",
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="completion.enabled",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="启用代码补全",
        description="输入时是否弹出代码补全建议。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.max_suggestions",
        type=SettingValueType.INTEGER,
        default=20,
        label="最大建议数",
        description="补全弹窗中最多展示的建议条目数量。",
        min=1,
        max=200,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="completion.auto_trigger",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="自动触发补全",
        description="键入时自动触发补全。",
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="checker.run_on_open",
        type=SettingValueType.BOOLEAN,
        default=False,
        label="打开时检查",
        description="打开文件后是否立刻运行代码检查。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.run_on_save",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="保存时检查",
        description="保存文件时自动运行代码检查。",
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="checker.timeout_ms",
        type=SettingValueType.INTEGER,
        default=30000,
        label="检查超时",
        description="单次代码检查的最长等待时间（毫秒）。",
        min=500,
        max=600000,
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="runner.timeout_ms",
        type=SettingValueType.INTEGER,
        default=30000,
        label="运行超时",
        description="运行代码的最长等待时间（毫秒）。",
        min=500,
        max=600000,
        scope=SettingsScope.GLOBAL,
    ),
    SettingSpec(
        key="runner.clear_output_before_run",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="运行前清空输出",
        description="每次运行前清空输出面板。",
        scope=SettingsScope.GLOBAL,
    ),

    SettingSpec(
        key="startup.restore_files",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="恢复上次打开的文件",
        description="启动时重新加载上次会话中打开的文件。",
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
        description="运行 Python 代码所使用的解释器绝对路径；留空则使用系统默认。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.entry_point",
        type=SettingValueType.PATH,
        default="",
        label="入口文件",
        description="F5 运行时的项目级入口；留空则使用当前打开的文件。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.c_compiler",
        type=SettingValueType.PATH,
        default="gcc",
        label="C 编译器",
        description="编译 C 代码所使用的编译器可执行文件名或绝对路径。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.cpp_compiler",
        type=SettingValueType.PATH,
        default="g++",
        label="C++ 编译器",
        description="编译 C++ 代码所使用的编译器可执行文件名或绝对路径。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="checker.enabled",
        type=SettingValueType.LIST,
        default=["flake8", "pyright"],
        label="启用的检查器",
        description="本项目使用的代码检查器 ID 列表。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="checker.ignore",
        type=SettingValueType.LIST,
        default=[],
        label="忽略的检查项",
        description="需要忽略的检查项 ID（例如 E501、W292）。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="project.exclude_paths",
        type=SettingValueType.LIST,
        default=["__pycache__", ".git", ".venv", "venv", "build", "dist"],
        label="排除路径",
        description="在文件浏览与全局搜索时忽略的路径（glob 模式）。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="project.tab_size",
        type=SettingValueType.INTEGER,
        default=4,
        label="项目 Tab 宽度",
        description="项目级 Tab 宽度覆盖；留空（0 表示未设置）时回退到全局设置。",
        min=0,
        max=16,
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.use_spaces",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="项目 Tab 转空格",
        description="项目级 Tab 转空格行为覆盖。",
        scope=SettingsScope.PROJECT,
    ),

    SettingSpec(
        key="project.name",
        type=SettingValueType.STRING,
        default="",
        label="项目名称",
        description="可选的项目显示名称；留空时使用目录名。",
        scope=SettingsScope.PROJECT,
    ),
    SettingSpec(
        key="project.description",
        type=SettingValueType.STRING,
        default="",
        label="项目描述",
        description="简短描述（仅展示用，不影响运行）。",
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