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
        description="界面主题。",
        choices=("Dark", "Light", "Solarized Dark"),
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
        key="completion.auto_trigger",
        type=SettingValueType.BOOLEAN,
        default=True,
        label="自动触发补全",
        description="键入自动触发。",
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