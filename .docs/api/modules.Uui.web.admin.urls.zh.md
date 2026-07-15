# `modules/Uui/web/admin/urls.py`

源文件路径：`modules/Uui/web/admin/urls.py`

Admin 的 URLconf 模块。被 `Include()` 动态加载。

## 内容

```python
from ..router import path
from . import views
from .site import site

urlpatterns = site.get_urls()
app_name = 'admin'
```

即 `urlpatterns` 直接是 `site.get_urls()` 的返回值；命名空间为 `'admin'`。