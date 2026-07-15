import pytest

from modules.i18n.translator import AVAILABLE_LANGUAGES, Translator, _load_locale, get_translator, t


class TestLoadLocale:
    def test_load_locale_returns_dict(self):
        result = _load_locale("en_US")
        assert isinstance(result, dict)

    def test_load_locale_invalid_lang_returns_empty(self):
        result = _load_locale("invalid_lang_xyz")
        assert result == {}


class TestTranslator:
    def test_singleton(self):
        translator1 = get_translator()
        translator2 = get_translator()
        assert translator1 is translator2

    def test_current_language_default(self):
        translator = Translator()
        assert translator.current_language == "en_US"

    def test_available_languages(self):
        translator = Translator()
        assert "zh_CN" in translator.available_languages
        assert "en_US" in translator.available_languages

    def test_set_language_valid(self):
        translator = Translator()
        result = translator.set_language("zh_CN")
        assert result == True
        assert translator.current_language == "zh_CN"

    def test_set_language_invalid(self):
        translator = Translator()
        result = translator.set_language("invalid_lang")
        assert result == False

    def test_set_language_same(self):
        translator = Translator()
        translator.set_language("zh_CN")
        result = translator.set_language("zh_CN")
        assert result == False

    def test_translate_key_exists(self):
        translator = Translator()
        translator.set_language("zh_CN")
        result = translator.translate("menu.file.new")
        assert isinstance(result, str)

    def test_translate_key_not_exists_returns_key(self):
        translator = Translator()
        translator.set_language("zh_CN")
        result = translator.translate("nonexistent.key.xyz")
        assert result == "nonexistent.key.xyz"

    def test_translate_with_default(self):
        translator = Translator()
        result = translator.translate("nonexistent.key", default="default value")
        assert result == "default value"

    def test_translate_with_kwargs(self):
        translator = Translator()
        translator.set_language("zh_CN")
        result = translator.translate("menu.greeting", default="Hello {name}", name="World")
        assert isinstance(result, str)

    def test_translate_fallback_to_en_US(self):
        translator = Translator()
        translator.set_language("zh_CN")
        result = translator.translate("menu.file.new")
        fallback_result = translator.translate("menu.file.new", locale="en_US")
        assert isinstance(result, str)
        assert isinstance(fallback_result, str)

    def test_has_key(self):
        translator = Translator()
        assert translator.has("menu.file.new") == True

    def test_has_key_false(self):
        translator = Translator()
        assert translator.has("nonexistent.key.xyz") == False

    def test_has_key_with_locale(self):
        translator = Translator()
        assert translator.has("menu.file.new", locale="zh_CN") == True

    def test_add_listener(self):
        translator = Translator()
        calls = []
        def listener(lang):
            calls.append(lang)
        translator.add_listener(listener)
        translator.set_language("zh_CN")
        assert "zh_CN" in calls

    def test_remove_listener(self):
        translator = Translator()
        calls = []
        def listener(lang):
            calls.append(lang)
        translator.add_listener(listener)
        translator.remove_listener(listener)
        translator.set_language("zh_CN")
        assert len(calls) == 0

    def test_reload(self):
        translator = Translator()
        translator.reload()
        assert translator.current_language == "en_US"


class TestModuleLevelFunctions:
    def test_t_function(self):
        result = t("menu.file.new")
        assert isinstance(result, str)

    def test_t_with_default(self):
        result = t("nonexistent.key", default="default")
        assert result == "default"

    def test_t_with_kwargs(self):
        result = t("menu.greeting", default="Hello {name}", name="World")
        assert "World" in result
