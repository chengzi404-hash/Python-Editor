"""test_storage - JsonFileSettings 单元测试。

覆盖以下行为:

* 初始 get 返回 schema 默认值。
* set 后 has / get 正确;触发 listener,事件携带正确 scope/key/old/new。
* 重复 set 同一个值不会重复触发 listener。
* 类型校验失败(ValueError)不修改原值。
* all() 包含 schema 全部键,缺失键用默认值填充。
* defined() 只返回显式赋值的键。
* reset(key) 删除自定义值,回退默认;未定义 key 时 reset 不报错、不触发事件。
* reset() 全量清空触发 key=None 事件。
* save() 后文件存在且内容为合法 JSON;包含 version / scope / values。
* 重新构造实例 load() 能恢复所有值。
* JSON 中包含未知 key 被丢弃(schema 升级兼容性);包含非法值时也被丢弃。
* 文件不存在或内容损坏时 load() 静默回退。
* 多线程并发 set 不会破坏数据(用 concurrent.futures.ThreadPoolExecutor,写 50 个不同 key 后全部读取验证)。
* 监听器抛异常不影响其他监听器与后续 set。
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple

import pytest

from modules.settings.base import (
    SettingSpec,
    SettingValueType,
    SettingsChangeEvent,
    SettingsScope,
    SettingsSchema,
)
from modules.settings.storage import CURRENT_VERSION, JsonFileSettings




def _make_schema() -> SettingsSchema:
    """构造一个最小的 SettingsSchema，覆盖 STRING/INTEGER/BOOLEAN/CHOICE/LIST 五种类型。"""
    return SettingsSchema(
        (
            SettingSpec(
                key="ui.theme",
                type=SettingValueType.STRING,
                default="light",
                label="theme",
                scope=SettingsScope.GLOBAL,
            ),
            SettingSpec(
                key="editor.tab_size",
                type=SettingValueType.INTEGER,
                default=4,
                min=1,
                max=16,
                scope=SettingsScope.GLOBAL,
            ),
            SettingSpec(
                key="editor.word_wrap",
                type=SettingValueType.BOOLEAN,
                default=False,
                scope=SettingsScope.GLOBAL,
            ),
            SettingSpec(
                key="editor.eol",
                type=SettingValueType.CHOICE,
                default="lf",
                choices=("lf", "crlf", "cr"),
                scope=SettingsScope.GLOBAL,
            ),
            SettingSpec(
                key="editor.excluded_dirs",
                type=SettingValueType.LIST,
                default=[".git", "__pycache__"],
                scope=SettingsScope.GLOBAL,
            ),
        )
    )


class _TempJsonSettings(JsonFileSettings):
    """一个将数据写入 tmp_path/settings.json 的 JsonFileSettings 子类。 。"""

    def __init__(self, schema, tmp_dir, *, scope=SettingsScope.GLOBAL, auto_load=False):
        self._tmp_dir = tmp_dir
        super().__init__(schema, scope=scope, path=str(tmp_dir / "settings.json"), auto_load=auto_load)

    def _resolve_path(self):
        return str(self._tmp_dir / "settings.json")


def _make_store(tmp_path, *, scope=SettingsScope.GLOBAL, auto_load=False):
    """工厂函数：返回一个绑定到 tmp_path 的存储实例。"""
    return _TempJsonSettings(_make_schema(), tmp_path, scope=scope, auto_load=auto_load)


def _collect_events(store):
    """注册一个监听器，将所有事件追加到一个私有列表。"""
    events = []
    store._events = events

    def _listener(ev):
        events.append(ev)

    store.add_listener(_listener)
    return events





class TestDefaults:
    """初始状态下 get 返回 schema 默认值。"""

    def test_get_returns_schema_default(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.get("ui.theme") == "light"
        assert store.get("editor.tab_size") == 4
        assert store.get("editor.word_wrap") is False
        assert store.get("editor.eol") == "lf"
        assert store.get("editor.excluded_dirs") == [".git", "__pycache__"]

    def test_has_is_false_for_unset(self, tmp_path):
        store = _make_store(tmp_path)
        assert store.has("ui.theme") is False
        assert store.has("editor.tab_size") is False


class TestSet:
    """set / has / get 的写入路径。"""

    def test_set_updates_get_and_has(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("ui.theme", "dark")
        assert store.has("ui.theme") is True
        assert store.get("ui.theme") == "dark"

    def test_set_emits_event_with_correct_payload(self, tmp_path):
        store = _make_store(tmp_path)
        events = _collect_events(store)
        store.set("editor.tab_size", 2)
        assert len(events) == 1
        ev = events[0]
        assert ev.scope == SettingsScope.GLOBAL
        assert ev.key == "editor.tab_size"
        assert ev.old == 4
        assert ev.new == 2

    def test_set_same_value_does_not_emit_event(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("editor.tab_size", 2)
        events = _collect_events(store)
        store.set("editor.tab_size", 2)
        assert events == []

    def test_set_to_different_value_emits_event(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("editor.tab_size", 2)
        events = _collect_events(store)
        store.set("editor.tab_size", 8)
        assert len(events) == 1
        assert events[0].old == 2
        assert events[0].new == 8

    def test_invalid_value_raises_and_does_not_mutate(self, tmp_path):
        store = _make_store(tmp_path)
        with pytest.raises(ValueError):
            store.set("editor.tab_size", "not-an-int")
        assert store.has("editor.tab_size") is False
        assert store.get("editor.tab_size") == 4

    def test_invalid_choice_raises(self, tmp_path):
        store = _make_store(tmp_path)
        with pytest.raises(ValueError):
            store.set("editor.eol", "spaces")
        assert store.get("editor.eol") == "lf"

    def test_unknown_key_raises_key_error(self, tmp_path):
        store = _make_store(tmp_path)
        with pytest.raises(KeyError):
            store.set("no.such.key", 1)





class TestAllAndDefined:
    """all / defined 快照语义。"""

    def test_all_contains_every_schema_key(self, tmp_path):
        store = _make_store(tmp_path)
        snap = store.all()
        assert set(snap.keys()) == {
            "ui.theme",
            "editor.tab_size",
            "editor.word_wrap",
            "editor.eol",
            "editor.excluded_dirs",
        }
        assert snap["ui.theme"] == "light"
        assert snap["editor.tab_size"] == 4
        assert snap["editor.word_wrap"] is False
        assert snap["editor.eol"] == "lf"
        assert snap["editor.excluded_dirs"] == [".git", "__pycache__"]

    def test_all_reflects_overrides(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("ui.theme", "dark")
        store.set("editor.tab_size", 8)
        snap = store.all()
        assert snap["ui.theme"] == "dark"
        assert snap["editor.tab_size"] == 8
        assert snap["editor.word_wrap"] is False

    def test_defined_only_returns_overrides(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("ui.theme", "dark")
        store.set("editor.tab_size", 8)
        defined = store.defined()
        assert defined == {"ui.theme": "dark", "editor.tab_size": 8}




class TestReset:
    """reset 返回默认，事件载荷正确。"""

    def test_reset_key_restores_default(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("ui.theme", "dark")
        events = _collect_events(store)
        store.reset("ui.theme")
        assert store.has("ui.theme") is False
        assert store.get("ui.theme") == "light"
        assert len(events) == 1
        assert events[0].key == "ui.theme"
        assert events[0].old == "dark"
        assert events[0].new == "light"

    def test_reset_undefined_key_is_noop(self, tmp_path):
        store = _make_store(tmp_path)
        events = _collect_events(store)
        store.reset("ui.theme")
        assert events == []
        assert store.get("ui.theme") == "light"

    def test_reset_all_emits_bulk_event(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("ui.theme", "dark")
        store.set("editor.tab_size", 8)
        events = _collect_events(store)
        store.reset()
        assert store.defined() == {}
        assert len(events) == 1
        ev = events[0]
        assert ev.key is None
        assert ev.old["ui.theme"] == "dark"
        assert ev.new["ui.theme"] == "light"
        assert ev.old["editor.tab_size"] == 8
        assert ev.new["editor.tab_size"] == 4

    def test_reset_all_on_empty_does_not_emit(self, tmp_path):
        store = _make_store(tmp_path)
        events = _collect_events(store)
        store.reset()
        assert events == []





class TestSaveAndLoad:
    """save / load 磁盘互转行为。"""

    def test_save_creates_file_with_valid_json(self, tmp_path):
        store = _make_store(tmp_path)
        store.set("ui.theme", "dark")
        store.set("editor.tab_size", 2)
        store.save()
        target = tmp_path / "settings.json"
        assert target.is_file()
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["version"] == CURRENT_VERSION
        assert data["scope"] == SettingsScope.GLOBAL.value
        assert isinstance(data["values"], dict)
        assert data["values"]["ui.theme"] == "dark"
        assert data["values"]["editor.tab_size"] == 2

    def test_load_roundtrip_restores_values(self, tmp_path):
        store_a = _make_store(tmp_path)
        store_a.set("ui.theme", "dark")
        store_a.set("editor.tab_size", 2)
        store_a.set("editor.word_wrap", True)
        store_a.set("editor.eol", "crlf")
        store_a.set("editor.excluded_dirs", [".venv", "build"])
        store_a.save()
        store_b = _TempJsonSettings(_make_schema(), tmp_path, auto_load=True)
        assert store_b.get("ui.theme") == "dark"
        assert store_b.get("editor.tab_size") == 2
        assert store_b.get("editor.word_wrap") is True
        assert store_b.get("editor.eol") == "crlf"
        assert store_b.get("editor.excluded_dirs") == [".venv", "build"]

    def test_load_drops_unknown_keys(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps(
                {
                    "version": CURRENT_VERSION,
                    "scope": SettingsScope.GLOBAL.value,
                    "values": {
                        "ui.theme": "dark",
                        "future.unknown_key": "ignored",
                        "another.deprecated": 42,
                    },
                }
            ),
            encoding="utf-8",
        )
        store = _TempJsonSettings(_make_schema(), tmp_path, auto_load=True)
        assert store.get("ui.theme") == "dark"
        assert store.defined() == {"ui.theme": "dark"}

    def test_load_drops_invalid_values(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text(
            json.dumps(
                {
                    "version": CURRENT_VERSION,
                    "scope": SettingsScope.GLOBAL.value,
                    "values": {
                        "editor.tab_size": "not-an-int",
                        "editor.word_wrap": "yes",
                        "editor.eol": "spaces",
                        "ui.theme": "dark",
                    },
                }
            ),
            encoding="utf-8",
        )
        store = _TempJsonSettings(_make_schema(), tmp_path, auto_load=True)
        assert store.get("ui.theme") == "dark"
        assert store.get("editor.tab_size") == 4
        assert store.get("editor.word_wrap") is False
        assert store.get("editor.eol") == "lf"
        assert store.defined() == {"ui.theme": "dark"}

    def test_load_missing_file_is_silent(self, tmp_path):
        store = _make_store(tmp_path)
        store.load()
        assert store.defined() == {}
        assert store.get("ui.theme") == "light"

    def test_load_corrupt_file_silently_falls_back(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text("{ this is not valid json", encoding="utf-8")
        store = _TempJsonSettings(_make_schema(), tmp_path, auto_load=True)
        assert store.defined() == {}
        assert store.get("ui.theme") == "light"

    def test_load_non_dict_payload_silently_falls_back(self, tmp_path):
        target = tmp_path / "settings.json"
        target.write_text("[1, 2, 3]", encoding="utf-8")
        store = _TempJsonSettings(_make_schema(), tmp_path, auto_load=True)
        assert store.defined() == {}
        assert store.get("ui.theme") == "light"





class TestConcurrency:
    """多线程并发 set 不会破坏数据。"""

    def test_concurrent_sets_to_single_key(self, tmp_path):
        store = _make_store(tmp_path)
        n = 50

        def writer(idx):
            store.set(
                "editor.excluded_dirs",
                [f"dir_{idx}", f"other_{idx}"],
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(writer, range(n)))

        final = store.get("editor.excluded_dirs")
        assert isinstance(final, list)
        assert len(final) == 2
        assert final[0].startswith("dir_")
        assert final[1].startswith("other_")

    def test_concurrent_sets_across_many_keys(self, tmp_path):
        """50 个线程各自写入一个独立的 key，之后读取所有值验证。"""
        schema = SettingsSchema(
            tuple(
                SettingSpec(
                    key=f"k{i:03d}",
                    type=SettingValueType.LIST,
                    default=[],
                )
                for i in range(50)
            )
        )
        store = _TempJsonSettings(schema, tmp_path, auto_load=False)

        def writer(args):
            idx, payload = args
            store.set(f"k{idx:03d}", payload)

        payloads = [(i, [f"v{i}-{j}" for j in range(3)]) for i in range(50)]
        with ThreadPoolExecutor(max_workers=16) as pool:
            list(pool.map(writer, payloads))
        for i in range(50):
            assert store.get(f"k{i:03d}") == [f"v{i}-{j}" for j in range(3)]




class TestListenerIsolation:
    """单个监听器抛异常不影响其他监听器与后续 set。"""

    def test_failing_listener_does_not_break_others(self, tmp_path):
        store = _make_store(tmp_path)
        received = []

        def bad_listener(ev):
            raise RuntimeError("boom")

        def good_listener(ev):
            received.append(ev)

        store.add_listener(bad_listener)
        store.add_listener(good_listener)
        store.set("ui.theme", "dark")
        assert len(received) == 1
        assert received[0].new == "dark"
        assert store.get("ui.theme") == "dark"

    def test_subsequent_set_works_after_listener_exception(self, tmp_path):
        store = _make_store(tmp_path)

        def bad_listener(ev):
            raise RuntimeError("boom")

        store.add_listener(bad_listener)
        store.set("ui.theme", "dark")
        store.set("ui.theme", "high-contrast")
        assert store.get("ui.theme") == "high-contrast"
