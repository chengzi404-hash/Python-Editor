"""``modules.i18n`` —— 轻量级国际化(i18n)支持。

设计目标:

* **零依赖**: 不依赖 ``gettext`` / ``babel`` 等第三方包, 直接用 JSON
  作为翻译源, 便于用户在 PR 中直接修改。
* **键值查询**: 通过语义化 key (如 ``menu.file.new``) 取出当前语言
  下的字符串, 缺翻译时优雅降级到 key 本身, 避免 UI 出现空白。
* **运行时切换**: 提供监听器接口, 编辑器在收到语言变更事件后可以
  重建菜单 / 重渲状态栏等。
* **与设置系统集成**: 通过 ``modules.settings`` 中的
  ``i18n.language`` 选项持久化偏好, 启动时自动加载。

公开 API::

    from modules.i18n import t, translator, get_translator

    translator.set_language("en_US")
    print(t("menu.file.new"))          # -> "New"
    print(t("greeting", name="Alice")) # -> "Hello, Alice!"

    def on_change(lang):
        print("language switched to", lang)
    translator.add_listener(on_change)
"""

from __future__ import annotations

from .translator import (
    AVAILABLE_LANGUAGES,
    I18nListener,
    Translator,
    get_translator,
    t,
)
from . import marketplace as language_marketplace

__all__ = [
    "AVAILABLE_LANGUAGES",
    "I18nListener",
    "Translator",
    "get_translator",
    "t",
    "language_marketplace",
]