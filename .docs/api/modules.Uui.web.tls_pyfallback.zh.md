# `modules/Uui/web/tls_pyfallback.py`

源文件路径：`modules/Uui/web/tls_pyfallback.py`

纯 Python X.509v3 自签名证书生成器（用于 `openssl` 不可用时的兜底）。

## 函数

### `_b64(n: int) -> bytes`
把正整数编码为 DER INTEGER（首位为 1 时补 `\x00`）。

### `_seq(*parts: bytes) -> bytes`
拼接为 DER SEQUENCE。

### `_set(*parts: bytes) -> bytes`
拼接为 DER SET。

### `_encode_length(n: int) -> bytes`
DER 长度编码（短/长形式）。

### `_is_probable_prime(n, rounds=16) -> bool`
Miller–Rabin 素性测试（先排除小素数列表）。

### `generate_self_signed(cn: str = 'localhost', cert_path: str = 'cert.pem', key_path: str = 'key.pem', days: int = 3650) -> Tuple[str, str]`
生成 RSA-2048 + X.509v3 自签名证书：
- 用纯 Python Miller–Rabin 生成素数 p、q。
- 构造 PKCS#1 RSAPrivateKey（PEM）。
- 构造最小 X.509v3 证书（含 `SubjectAlternativeName(DNS:cn)`），PEM 写入 `cert_path` / `key_path`。
- 仅供开发/测试使用，不针对性能优化。