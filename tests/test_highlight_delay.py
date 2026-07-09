"""针对 ``main._Debouncer`` 防抖调度器的单元测试。

``_Debouncer`` 与 GUI 框架解耦,只依赖注入的 ``after`` / ``cancel`` 钩子,
因此可以在不创建 Tk 根窗口的前提下验证其语义。
"""

from __future__ import annotations
from typing import Callable

import pytest

from main import _Debouncer


class _FakeScheduler:
    """记录 ``after`` 与 ``after_cancel`` 调用的伪调度器。

    ``after`` 返回递增的整数 id;``cancel`` 记录被取消的 id。
    不会真正等到 ``delay_ms`` 后再回调 — 由测试显式触发回调。
    """

    def __init__(self):
        self.next_id = 1
        self.cancelled: list[int] = []
        self.scheduled: list[tuple[int, Callable]] = []

    def after(self, delay_ms: int, callback):
        self.scheduled.append((delay_ms, callback))
        job_id = self.next_id
        self.next_id += 1
        return job_id

    def cancel(self, job_id):
        self.cancelled.append(job_id)

    def fire(self, delay_match: int = -1):
        """触发最近一次 ``after(delay_match, cb)`` 调度的回调。"""

        for i in range(len(self.scheduled) - 1, -1, -1):
            delay, cb = self.scheduled[i]
            if delay_match < 0 or delay == delay_match:
                cb()
                return True
        return False


class TestDebouncerBasic:
    def test_schedule_returns_after_id(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 100)
        assert d.pending_id == 1

    def test_first_schedule_uses_given_delay(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 250)
        assert sched.scheduled[0][0] == 250

    def test_schedule_passes_callable(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        cb = lambda: None
        d.schedule(cb, 50)
        _, callback = sched.scheduled[-1]
        assert callback is cb

    def test_pending_id_is_none_after_cancel(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 100)
        d.cancel()
        assert d.pending_id is None

    def test_cancel_without_pending_is_noop(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.cancel()
        assert sched.cancelled == []


class TestDebouncerReschedule:
    def test_reschedule_cancels_previous(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 100)
        d.schedule(lambda: None, 100)
        assert sched.cancelled == [1]
        assert d.pending_id == 2

    def test_many_reschedules_only_keep_last(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        for _ in range(5):
            d.schedule(lambda: None, 50)
        assert sched.cancelled == [1, 2, 3, 4]
        assert d.pending_id == 5

    def test_callbacks_only_last_fires(self) -> None:
        """模拟'用户连续按键', 只有最后一次按键的回调会被实际调用。"""

        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        calls: list[str] = []

        d.schedule(lambda: calls.append("first"), 100)
        d.schedule(lambda: calls.append("second"), 100)
        d.schedule(lambda: calls.append("third"), 100)

        sched.fire(100)
        assert calls == ["third"]


class TestDebouncerDelayValues:
    def test_zero_delay_is_allowed(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 0)
        assert sched.scheduled[-1][0] == 0

    def test_negative_delay_is_clamped_to_zero(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, -50)
        assert sched.scheduled[-1][0] == 0

    def test_float_delay_is_coerced_to_int(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 12.9)  # type: ignore[arg-type]
        assert sched.scheduled[-1][0] == 12

    def test_dynamic_delay_each_call(self) -> None:
        """同实例可以连续使用不同的延迟值,每次取最新的。"""

        sched = _FakeScheduler()
        d = _Debouncer(sched.after, sched.cancel)
        d.schedule(lambda: None, 100)
        d.schedule(lambda: None, 500)
        assert sched.scheduled[-1][0] == 500


class TestDebouncerRobustness:
    def test_after_exception_is_swallowed(self) -> None:
        def broken_after(*a, **kw):
            raise RuntimeError("boom")

        d = _Debouncer(broken_after, lambda _id: None)
        d.schedule(lambda: None, 100)  # 不应抛出
        assert d.pending_id is None

    def test_cancel_exception_is_swallowed(self) -> None:
        sched = _FakeScheduler()
        d = _Debouncer(sched.after, lambda _id: (_ for _ in ()).throw(RuntimeError("boom")))
        d.schedule(lambda: None, 100)
        d.cancel()  # 不应抛出
        assert d.pending_id is None