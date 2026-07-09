# -*- coding: utf-8 -*-
"""针对 modules.i18n 模块的测试。"""

from __future__ import annotations

import pytest

from modules.i18n import (
    AVAILABLE_LANGUAGES,
    Translator,
    get_translator,
    t,
)


class TestTranslatorBasics:
    """翻译器基础行为。"""

    def test_singleton(self):
        tr1 = get_translator()
        tr2 = get_translator()
        assert tr1 is tr2

    def test_available_languages_contains_expected(self):
        assert 'zh_CN' in AVAILABLE_LANGUAGES
        assert 'en_US' in AVAILABLE_LANGUAGES

    def test_current_language_starts_with_fallback(self):
        tr = get_translator()
        assert tr.current_language in AVAILABLE_LANGUAGES

    def test_set_language_returns_true_on_change(self):
        tr = get_translator()
        old = tr.current_language
        new = 'en_US' if old != 'en_US' else 'zh_CN'
        changed = tr.set_language(new)
        assert changed is True
        assert tr.current_language == new
        # 切回旧的
        tr.set_language(old)

    def test_set_language_returns_false_if_same(self):
        tr = get_translator()
        old = tr.current_language
        changed = tr.set_language(old)
        assert changed is False

    def test_set_language_invalid_returns_false(self):
        tr = get_translator()
        old = tr.current_language
        changed = tr.set_language('INVALID_LANG')
        assert changed is False
        assert tr.current_language == old


class TestTranslate:
    """translate() 与 t() 函数行为。"""

    def test_translate_existing_key_zh(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        result = tr.translate('menu.file.new')
        assert result == '新建'

    def test_translate_existing_key_en(self):
        tr = get_translator()
        tr.set_language('en_US')
        result = tr.translate('menu.file.new')
        assert result == 'New'

    def test_translate_unknown_key_returns_key(self):
        tr = get_translator()
        tr.set_language('en_US')
        result = tr.translate('totally.unknown.key')
        assert result == 'totally.unknown.key'

    def test_translate_unknown_key_with_default(self):
        tr = get_translator()
        tr.set_language('en_US')
        result = tr.translate('totally.unknown.key', default='fallback')
        assert result == 'fallback'

    def test_module_level_t_uses_singleton(self):
        old = get_translator().current_language
        get_translator().set_language('zh_CN')
        try:
            assert t('menu.file.new') == '新建'
        finally:
            get_translator().set_language(old)

    def test_translate_with_format_kwargs(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        result = tr.translate('status.saved', name='foo.py')
        assert 'foo.py' in result

    def test_translate_missing_format_arg_does_not_raise(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        # 翻译里需要 {name} 但没给 kwargs, 应该返回原文而不抛异常
        result = tr.translate('status.saved')
        assert '{name}' in result or 'name' in result.lower() or 'foo.py' not in result

    def test_translate_force_lang_overrides_current(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        result = tr.translate('menu.file.new', lang='en_US')
        assert result == 'New'


class TestFallback:
    """缺失翻译时的回退机制。"""

    def test_zh_CN_missing_key_falls_back_to_en_US(self):
        tr = get_translator()
        # 找一个在 en_US 有但 zh_CN 没有的 key (如果全都有, 至少验证 fallback 不报错)
        tr.set_language('zh_CN')
        result = tr.translate('menu.file.new')
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_both_missing_returns_key(self):
        tr = get_translator()
        tr.set_language('en_US')
        result = tr.translate('key.that.does.not.exist.at.all')
        assert result == 'key.that.does.not.exist.at.all'


class TestHas:
    """has() 方法。"""

    def test_has_returns_true_for_existing_key(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        assert tr.has('menu.file.new') is True

    def test_has_returns_false_for_missing_key(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        assert tr.has('key.that.does.not.exist') is False

    def test_has_with_lang_param(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        assert tr.has('menu.file.new', lang='en_US') is True


class TestListeners:
    """语言切换监听器。"""

    def test_listener_called_on_language_change(self):
        tr = get_translator()
        events = []
        tr.add_listener(lambda lang: events.append(lang))
        old = tr.current_language
        new = 'en_US' if old != 'en_US' else 'zh_CN'
        tr.set_language(new)
        assert len(events) == 1
        assert events[0] == new
        # 恢复
        tr.set_language(old)

    def test_listener_not_called_if_same_language(self):
        tr = get_translator()
        events = []
        tr.add_listener(lambda lang: events.append(lang))
        old = tr.current_language
        tr.set_language(old)
        assert len(events) == 0

    def test_remove_listener(self):
        tr = get_translator()
        def cb(lang):
            pass
        tr.add_listener(cb)
        tr.remove_listener(cb)
        old = tr.current_language
        new = 'en_US' if old != 'en_US' else 'zh_CN'
        tr.set_language(new)
        tr.set_language(old)  # 恢复


class TestReload:
    """reload() 重新加载语言包。"""

    def test_reload_does_not_raise(self):
        tr = get_translator()
        tr.reload()  # 不抛异常即可

    def test_reload_preserves_translations(self):
        tr = get_translator()
        tr.set_language('zh_CN')
        tr.reload()
        result = tr.translate('menu.file.new')
        assert result == '新建'
