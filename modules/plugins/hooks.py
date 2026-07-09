"""``modules.plugins.hooks`` — 编辑器钩子事件常量与参数约定。

钩子命名风格
============

``<namespace>:<event>``, 命名空间分两类:

* ``editor.*`` —— 编辑器核心生命周期事件 (打开文件、运行完成等), \
  所有插件可订阅。
* ``language.*`` —— 语言相关事件 (预留, 当前未发出, 但保留命名空间)。

参数约定
========

每个事件以 :class:`HookSpec` 描述形参, 插件回调按声明顺序接收位置参数。

* ``editor:file_opened`` —— ``(path: str)``
* ``editor:file_saved`` —— ``(path: str)``
* ``editor:file_created`` —— ``()`` (新建空文件)
* ``editor:content_changed`` —— ``(code: str, cursor_pos: int)``
* ``editor:language_changed`` —— ``(lang: str)``
* ``editor:cursor_moved`` —— ``(line: int, col: int)``
* ``editor:run_started`` —— ``(lang: str, temp_path: str)``
* ``editor:run_finished`` —— ``(lang: str, returncode: int, stdout: str, stderr: str)``
* ``editor:check_finished`` —— ``(lang: str, issues: list)``
* ``editor:closing`` —— ``()``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


class HookEvents:
    """钩子事件名常量。直接 ``ctx.on(HookEvents.EDITOR_FILE_OPENED, cb)`` 即可。"""

    EDITOR_FILE_OPENED = "editor:file_opened"
    EDITOR_FILE_SAVED = "editor:file_saved"
    EDITOR_FILE_CREATED = "editor:file_created"
    EDITOR_CONTENT_CHANGED = "editor:content_changed"
    EDITOR_LANGUAGE_CHANGED = "editor:language_changed"
    EDITOR_CURSOR_MOVED = "editor:cursor_moved"
    EDITOR_RUN_STARTED = "editor:run_started"
    EDITOR_RUN_FINISHED = "editor:run_finished"
    EDITOR_CHECK_FINISHED = "editor:check_finished"
    EDITOR_CLOSING = "editor:closing"


@dataclass(frozen=True)
class HookSpec:
    """钩子事件的形参签名描述, 仅供 UI 展示 / 类型检查使用。"""

    name: str
    params: Tuple[str, ...]
    description: str = ""


HOOK_SPECS = (
    HookSpec(HookEvents.EDITOR_FILE_OPENED, ("path",), "文件被加载进编辑器"),
    HookSpec(HookEvents.EDITOR_FILE_SAVED, ("path",), "文件被保存"),
    HookSpec(HookEvents.EDITOR_FILE_CREATED, (), "新建空文件"),
    HookSpec(
        HookEvents.EDITOR_CONTENT_CHANGED, ("code", "cursor_pos"),
        "编辑器内容变更 (经过防抖)",
    ),
    HookSpec(HookEvents.EDITOR_LANGUAGE_CHANGED, ("lang",), "切换语言"),
    HookSpec(HookEvents.EDITOR_CURSOR_MOVED, ("line", "col"), "光标移动"),
    HookSpec(
        HookEvents.EDITOR_RUN_STARTED, ("lang", "temp_path"),
        "开始运行代码 (临时文件已生成)",
    ),
    HookSpec(
        HookEvents.EDITOR_RUN_FINISHED, ("lang", "returncode", "stdout", "stderr"),
        "代码运行结束",
    ),
    HookSpec(
        HookEvents.EDITOR_CHECK_FINISHED, ("lang", "issues"),
        "静态检查结束, issues 是 issue 对象列表",
    ),
    HookSpec(HookEvents.EDITOR_CLOSING, (), "编辑器即将关闭"),
)


__all__ = ["HookEvents", "HookSpec", "HOOK_SPECS"]