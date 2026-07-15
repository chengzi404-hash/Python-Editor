# `modules/Uui/web/auth/password.py`

源文件路径：`modules/Uui/web/auth/password.py`

基于 `pbkdf2_sha256` 的密码哈希（仅使用标准库）。

## 模块常量

- `ALGO = 'pbkdf2_sha256'`
- `ITERATIONS = 320_000`
- `SALT_LEN = 16`
- `HASH_LEN = 32`

## 函数

### `make_password(password: str, *, iterations=ITERATIONS) -> str`
使用 `secrets.token_bytes(SALT_LEN)` 生成随机 salt，调用 `hashlib.pbkdf2_hmac('sha256', ...)` 输出编码：

```
pbkdf2_sha256$<iterations>$<base64-salt>$<base64-hash>
```

`password is None` 时抛 `ValueError`。

### `check_password(password: str, encoded: str) -> bool`
常量时间比较（`hmac.compare_digest`）。解析失败或算法不一致返回 `False`。

### `needs_rehash(encoded: str) -> bool`
若编码使用旧算法或 iterations 低于当前默认，返回 `True`。

## 内部辅助

- `_b64(b)` / `_b64d(s)`：base64 编码/解码（无填充）。