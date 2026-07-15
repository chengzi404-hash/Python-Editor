# `modules/Uui/web/exceptions.py`

源文件路径：`modules/Uui/web/exceptions.py`

Uui.web 异常层次。

## 类

### `UWebError(Exception)`
所有 Uui.web 异常的基类。
- `status_code = 500`
- `default_message = 'Internal server error'`

### `Http404(UWebError)`
- `status_code = 404` / `default_message = 'Not found'`

### `Http405(UWebError)`
- `status_code = 405` / `default_message = 'Method not allowed'`

### `Http400(UWebError)`
- `status_code = 400` / `default_message = 'Bad request'`

### `Http403(UWebError)`
- `status_code = 403` / `default_message = 'Forbidden'`

### `Http500(UWebError)`
- `status_code = 500` / `default_message = 'Server error'`

### `ImproperlyConfigured(UWebError)`
应用配置错误（缺 `ROOT_URLCONF`、缺 `TEMPLATES` 等）。
- `default_message = 'Improperly configured'`

### `AppRegistryNotReady(UWebError)`
在注册中心准备好之前访问 apps。
- `default_message = 'Apps are not loaded yet'`