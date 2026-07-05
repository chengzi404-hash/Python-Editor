"""pytest 全局配置。

将项目根目录加入 ``sys.path``,使得 ``import modules.xxx`` 能正常解析。
同时关闭 ``modules`` 子包中以 ``__init__.py`` 为入口的可选依赖(如 flake8、pyright)
对测试的副作用。
"""

from __future__ import annotations

import os
import sys

# 项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)