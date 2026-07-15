# `modules/Uui/web/tls.py`

源文件路径：`modules/Uui/web/tls.py`

TLS 辅助：使用 `openssl` 命令生成自签名证书；若 `openssl` 不在 PATH 则回退到 `tls_pyfallback.py`（纯 Python）；若已安装 `cryptography` 则优先用其生成"正经"证书。

## 函数

### `openssl_available() -> bool`
返回 `shutil.which('openssl') is not None`。

### `_generate_via_cryptography(cn, cert_path, key_path, days=3650) -> (cert_path, key_path)`
使用可选的 `cryptography` 库签发 RSA-2048 自签名证书，含 `SubjectAlternativeName(DNS:cn)`，PEM 写入 `cert_path` / `key_path`。

### `_generate_via_openssl(cn, cert_path, key_path, days=3650) -> (cert_path, key_path)`
调用 `openssl req -x509 -newkey rsa:2048 -nodes -subj "/CN=<cn>" ...` 生成 PEM。

### `_generate_via_python(cn, cert_path, key_path, days=3650) -> (cert_path, key_path)`
委托给 `tls_pyfallback.generate_self_signed`（纯 Python 实现）。

### `ensure_dev_cert(*, cn='localhost', cert_path='cert.pem', key_path='key.pem') -> (cert_path, key_path)`
若 `cert_path` / `key_path` 已存在则直接返回；否则按以下顺序尝试：
1. `_generate_via_cryptography`（若可用）
2. `_generate_via_openssl`（若 `openssl_available()`）
3. `_generate_via_python`（兜底）

最终抛错时给出详细指引。