"""HTTP/2-capable WSGI server.

Uses the ``h2`` library to add HTTP/2 framing while keeping the underlying
application WSGI-compatible (HTTP/1.1). Supports two transports:

* **h2c (cleartext)**: detects the protocol via the HTTP/1.1 Upgrade
  mechanism or, when ``prior-knowledge`` is set, assumes the client speaks
  HTTP/2 from the first byte.
* **HTTPS with ALPN**: the TLS handshake negotiates either ``h2`` or
  ``http/1.1``; the appropriate framing is selected per connection.

The WSGI app itself is unchanged — the server adapts the HTTP/2 streams
into WSGI environ dicts and translates the WSGI response back into
HTTP/2 frames.
"""
import socket
import ssl
import sys
import threading
from socketserver import ThreadingMixIn, BaseServer
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer

if TYPE_CHECKING:
    import h2  # type: ignore[import-not-found]
    import h2.connection  # type: ignore[import-not-found]
    import h2.config  # type: ignore[import-not-found]
    import h2.events  # type: ignore[import-not-found]
    import h2.exceptions  # type: ignore[import-not-found]

try:
    import h2.connection
    import h2.config
    import h2.events
    import h2.exceptions
    H2_AVAILABLE = True
except ImportError:  # pragma: no cover
    H2_AVAILABLE = False

from .exceptions import ImproperlyConfigured



def _h2_config(settings: Any) -> 'h2.config.H2Configuration':
    if not H2_AVAILABLE:
        raise ImproperlyConfigured(
            'HTTP/2 requires the `h2` package; install with `pip install h2 hpack hyperframe`'
        )
    return h2.config.H2Configuration(
        client_side=False,
        header_encoding='utf-8',
    )



_STATUS_REASONS = {
    200: 'OK', 201: 'Created', 202: 'Accepted', 204: 'No Content',
    301: 'Moved Permanently', 302: 'Found', 303: 'See Other',
    304: 'Not Modified', 307: 'Temporary Redirect', 308: 'Permanent Redirect',
    400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
    404: 'Not Found', 405: 'Method Not Allowed', 408: 'Request Timeout',
    409: 'Conflict', 410: 'Gone', 411: 'Length Required',
    413: 'Payload Too Large', 414: 'URI Too Long',
    418: "I'm a teapot", 422: 'Unprocessable Entity',
    429: 'Too Many Requests', 500: 'Internal Server Error',
    501: 'Not Implemented', 502: 'Bad Gateway', 503: 'Service Unavailable',
    504: 'Gateway Timeout',
}


def _build_http2_headers(status: str, headers: List[Tuple[str, str]]) -> List[Tuple[bytes, bytes]]:
    try:
        code = int(status.split(' ', 1)[0])
    except (TypeError, ValueError):
        code = 200
    reason = _STATUS_REASONS.get(code, '')
    out: List[Tuple[bytes, bytes]] = [(b':status', str(code).encode('ascii'))]
    if reason:
        out.append((b'reason', reason.encode('ascii')))
    for k, v in headers:
        if isinstance(k, str):
            kl = k.lower().encode('ascii')
        else:
            kl = k.lower()
        if kl in (b'connection', b'keep-alive', b'proxy-connection',
                  b'transfer-encoding', b'upgrade'):
            continue
        if kl == b'length':
            kl = b'content-length'
        if not kl.startswith(b':'):
            value = v.encode('latin-1', 'replace') if isinstance(v, str) else v
            out.append((kl, value))
    return out



def _consume_app_iter(app_iter: Any, chunks: List[bytes], max_bytes: int) -> int:
    """Pull bytes from a WSGI app iterable into ``chunks``. Stops if more than
    ``max_bytes`` have been collected (to avoid unbounded buffering)."""
    total = 0
    try:
        for piece in app_iter:
            if isinstance(piece, str):
                piece = piece.encode('utf-8')
            elif isinstance(piece, bytearray):
                piece = bytes(piece)
            if not isinstance(piece, bytes):
                continue
            if total + len(piece) > max_bytes:
                piece = piece[:max_bytes - total]
            if not piece:
                continue
            chunks.append(piece)
            total += len(piece)
            if total >= max_bytes:
                break
    finally:
        close = getattr(app_iter, 'close', None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
    return total



class _H2Stream:
    """Coordinates one HTTP/2 stream through the WSGI app."""

    __slots__ = ('stream_id', 'request_method', 'request_path',
                 'request_headers', 'request_body', 'response_started',
                 'response_status', 'response_headers', 'response_chunks',
                 'wsgi_result', 'environ', 'trailers', 'pushed')

    def __init__(self, stream_id: int) -> None:
        self.stream_id = stream_id
        self.request_method: str = ''
        self.request_path: str = ''
        self.request_headers: List[Tuple[bytes, bytes]] = []
        self.request_body: bytes = b''
        self.response_started: bool = False
        self.response_status: str = '200 OK'
        self.response_headers: List[Tuple[str, str]] = []
        self.response_chunks: List[bytes] = []
        self.wsgi_result: Any = None
        self.environ: Optional[dict] = None
        self.trailers: List[Tuple[bytes, bytes]] = []
        self.pushed: bool = False

    def add_request_data(self, data: bytes) -> None:
        if data:
            self.request_body += data

    def start_response(self, status: str, headers: List[Tuple[str, str]],
                       exc_info: Any = None) -> Callable[[bytes], None]:
        self.response_status = status
        merged: List[Tuple[str, str]] = []
        for k, v in headers:
            kl = k.lower()
            if kl == 'set-cookie':
                merged.append((k, v))
            else:
                found = False
                for i, (mk, mv) in enumerate(merged):
                    if mk.lower() == kl:
                        merged[i] = (mk, mv + ', ' + v)
                        found = True
                        break
                if not found:
                    merged.append((k, v))
        self.response_headers = merged
        self.response_started = True
        return lambda data: self.response_chunks.append(data)

    def finish_response(self, app_iter: Any, max_bytes: int) -> None:
        if not self.response_started:
            self.start_response('500 Internal Server Error',
                                [('content-type', 'text/plain')])
        _consume_app_iter(app_iter, self.response_chunks, max_bytes)

    def build_headers(self) -> List[Tuple[bytes, bytes]]:
        return _build_http2_headers(self.response_status, self.response_headers)



class _H2Connection:
    """One h2 connection + the per-stream dict for the underlying socket."""

    def __init__(self, sock: Any, settings: Any, wsgi_app: Callable) -> None:
        self.sock = sock
        self.settings = settings
        self.wsgi_app = wsgi_app
        self.h2 = h2.connection.H2Connection(config=_h2_config(settings))
        self.h2.initiate_connection()
        self.streams: dict = {}
        out = self.h2.data_to_send()
        if out:
            self.sock.sendall(out)


    def _send(self, data: bytes = b'') -> None:
        if data:
            self.sock.sendall(data)
        out = self.h2.data_to_send()
        if out:
            self.sock.sendall(out)

    def _recv_exact(self, n: int) -> bytes:
        buf = b''
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                return buf
            buf += chunk
        return buf

    def _read_some(self) -> bytes:
        try:
            self.sock.settimeout(0.5)
        except Exception:
            pass
        try:
            data = self.sock.recv(65535)
        except (socket.timeout, BlockingIOError, OSError):
            return b''
        return data or b''


    def _dispatch_stream(self, stream: _H2Stream) -> None:
        environ = self._build_environ(stream)
        stream.environ = environ
        try:
            result = self.wsgi_app(environ, stream.start_response)
        except Exception:
            stream.start_response('500 Internal Server Error',
                                  [('content-type', 'text/plain')])
            stream.response_chunks.append(b'Internal server error\n')
            result = iter(())
        stream.wsgi_result = result
        max_bytes = int(getattr(self.settings, 'HTTP2_MAX_FRAME_SIZE', 16384)) * 16
        stream.finish_response(result, max_bytes)
        self._send_response(stream)

    def _build_environ(self, stream: _H2Stream) -> dict:
        method = stream.request_method or 'GET'
        path = stream.request_path or '/'
        if '?' in path:
            path, _, qs = path.partition('?')
        else:
            qs = ''
        env = {
            'REQUEST_METHOD': method,
            'SCRIPT_NAME': '',
            'PATH_INFO': path,
            'QUERY_STRING': qs,
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/2.0',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https' if self._is_tls() else 'http',
            'wsgi.input': _StreamInput(stream.request_body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': True,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }
        for k, v in stream.request_headers:
            kl = k.lower()
            if kl.startswith(b':'):
                continue
            name = 'HTTP_' + kl.decode('latin-1').upper().replace('-', '_')
            value = v.decode('latin-1')
            env[name] = value
        if method in ('POST', 'PUT', 'PATCH'):
            env['CONTENT_LENGTH'] = str(len(stream.request_body))
        env['http2.stream_id'] = stream.stream_id
        return env

    def _is_tls(self) -> bool:
        return getattr(self.sock, '_h2_is_tls', False)

    def _send_response(self, stream: _H2Stream) -> None:
        h2_stream = self.h2.streams.get(stream.stream_id)
        if h2_stream is None:
            return
        headers = stream.build_headers()
        self.h2.send_headers(stream.stream_id, headers)
        max_frame = int(getattr(self.settings, 'HTTP2_MAX_FRAME_SIZE', 16384))
        for chunk in stream.response_chunks:
            i = 0
            while i < len(chunk):
                self.h2.send_data(stream.stream_id, chunk[i:i + max_frame])
                i += max_frame
        if stream.trailers:
            for k, v in stream.trailers:
                self.h2.send_headers(stream.stream_id, [(k, v)], end_stream=True)
        else:
            self.h2.end_stream(stream.stream_id)
        out = self.h2.data_to_send()
        if out:
            try:
                self.sock.sendall(out)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass


    def _handle_event(self, event: 'h2.events.Event') -> None:
        if isinstance(event, h2.events.RequestReceived):
            self._on_headers(event)
        elif isinstance(event, h2.events.DataReceived):
            self._on_data(event)
        elif isinstance(event, h2.events.WindowUpdated):
            pass
        elif isinstance(event, h2.events.StreamEnded):
            self._on_stream_ended(event)
        elif isinstance(event, h2.events.StreamReset):
            stream = self.streams.get(event.stream_id)
            if stream and stream.wsgi_result is not None:
                try:
                    close = getattr(stream.wsgi_result, 'close', None)
                    if close:
                        close()
                except Exception:
                    pass
        elif isinstance(event, h2.events.PingReceived):
            pass
        elif isinstance(event, h2.events.ConnectionTerminated):
            raise _H2Closed()

    def _on_headers(self, event: 'h2.events.RequestReceived') -> None:
        stream = _H2Stream(event.stream_id)
        for k, v in event.headers:
            if isinstance(k, str):
                k_bytes = k.lower().encode('ascii')  # type: ignore[union-attr]
            else:
                k_bytes = k.lower()
            if isinstance(v, str):
                v_bytes = v.encode('latin-1', 'replace')
            else:
                v_bytes = v
            if k_bytes == b':method':
                stream.request_method = v_bytes.decode('latin-1', 'replace')
            elif k_bytes == b':path':
                stream.request_path = v_bytes.decode('latin-1', 'replace')
            elif k_bytes == b':scheme':
                pass  # captured via environ
            elif k_bytes == b':authority':
                stream.request_headers.append((b'host', v_bytes))
            else:
                stream.request_headers.append((k_bytes, v_bytes))
        self.streams[event.stream_id] = stream
        if not event.stream_ended:
            return
        self._dispatch_stream(stream)

    def _on_data(self, event: 'h2.events.DataReceived') -> None:
        stream = self.streams.get(event.stream_id)
        if stream is None:
            return
        data = event.data
        if isinstance(data, str):
            data = data.encode('latin-1', 'replace')
        stream.add_request_data(data)
        self.h2.acknowledge_received_data(event.flow_controlled_length, event.stream_id)

    def _on_stream_ended(self, event: 'h2.events.StreamEnded') -> None:
        stream = self.streams.get(event.stream_id)
        if stream is None:
            return
        if stream.wsgi_result is None:
            self._dispatch_stream(stream)

    def serve(self) -> None:
        try:
            out = self.h2.data_to_send()
            if out:
                self.sock.sendall(out)
            self.sock.settimeout(30.0)
            while True:
                try:
                    data = self.sock.recv(65535)
                except socket.timeout:
                    break
                if not data:
                    break
                events = self.h2.receive_data(data)
                for ev in events:
                    self._handle_event(ev)
                self._send()
                if (not self.h2.open_inbound_streams and not self.h2.open_outbound_streams
                        and self.h2.state_machine.state in (
                            h2.connection.ConnectionState.IDLE,
                            h2.connection.ConnectionState.CLOSED,
                        )):
                    break
        except _H2Closed:
            pass
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            try:
                if (not self.h2.open_inbound_streams and not self.h2.open_outbound_streams
                        and self.h2.state_machine.state != h2.connection.ConnectionState.CLOSED):
                    self.h2.close_connection()
                    remaining = self.h2.data_to_send()
                    if remaining:
                        self.sock.sendall(remaining)
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass


class _H2Closed(Exception):
    pass


class _StreamInput:
    def __init__(self, data: bytes) -> None:
        self._buf = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0 or n > len(self._buf) - self._pos:
            n = len(self._buf) - self._pos
        chunk = self._buf[self._pos:self._pos + n]
        self._pos += n
        return chunk

    def readline(self) -> bytes:
        idx = self._buf.find(b'\n', self._pos)
        if idx < 0:
            chunk = self._buf[self._pos:]
            self._pos = len(self._buf)
            return chunk
        chunk = self._buf[self._pos:idx + 1]
        self._pos = idx + 1
        return chunk

    def __iter__(self):
        return iter([self.read()])



_HTTP2_PREFACE = b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'


class HybridRequestHandler:
    """A request handler that picks HTTP/1.1 or HTTP/2 per connection.

    Detection:
    * The first bytes of a new connection match the h2c connection preface:
      serve that connection as HTTP/2.
    * Otherwise treat as HTTP/1.1 and dispatch to the WSGIRequestHandler.
    * When wrapped in TLS, the ALPN result picks the protocol; ALPN
      ``h2`` chooses the HTTP/2 path, otherwise HTTP/1.1.
    """

    def __init__(self, wsgi_app: Callable, settings: Any) -> None:
        self.wsgi_app = wsgi_app
        self.settings = settings
        self.h1_handler = WSGIRequestHandler  # fallback
        self.h1_handler.wsgi_app = wsgi_app  # type: ignore[attr-defined]

    def __call__(self, request: 'socket.socket', client_address: Any, server: Any) -> None:
        alpn = getattr(request, 'selected_alpn_protocol', lambda: None)()
        if alpn and alpn.startswith('h2'):
            self._serve_h2(request, client_address, server)
            return
        if alpn and alpn == 'http/1.1':
            try:
                request.settimeout(None)
            except Exception:
                pass
            self.h1_handler(request, client_address, server)
            return

        try:
            request.settimeout(2.0)
        except Exception:
            pass
        try:
            head = self._peek(request, len(_HTTP2_PREFACE))
        except (socket.timeout, OSError):
            head = b''
        if head.startswith(_HTTP2_PREFACE):
            try:
                request.settimeout(None)
            except Exception:
                pass
            self._serve_h2(request, client_address, server)
            return
        if (head.startswith(b'GET ') or head.startswith(b'POST ') or
                head.startswith(b'PUT ') or head.startswith(b'DELETE ') or
                head.startswith(b'HEAD ') or head.startswith(b'OPTIONS ')):
            try:
                request.settimeout(None)
            except Exception:
                pass
            self.h1_handler(request, client_address, server)
            return
        try:
            request.close()
        except Exception:
            pass

    @staticmethod
    def _peek(sock: 'socket.socket', n: int) -> bytes:
        data = sock.recv(n, socket.MSG_PEEK)
        if not data:
            return b''
        return data[:n]

    def _serve_h2(self, request: 'socket.socket', client_address: Any, server: Any) -> None:
        try:
            request.settimeout(None)
            conn = _H2Connection(request, self.settings, self.wsgi_app)
            conn.serve()
        except Exception:
            try:
                request.close()
            except Exception:
                pass



class H2WSGIServer(ThreadingMixIn, WSGIServer):
    """A threaded WSGI server that supports HTTP/1.1 + HTTP/2 (h2c / h2)."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: Tuple[str, int], wsgi_app: Callable,
                 settings: Any, ssl_context: Optional[ssl.SSLContext] = None) -> None:
        self.settings = settings
        self._wsgi_app = wsgi_app
        self._ssl_context = ssl_context
        self.application = wsgi_app
        self.server_address = server_address
        self.socket = socket.socket(self.address_family, self.socket_type)
        if ssl_context is not None:
            self.socket = ssl_context.wrap_socket(self.socket, server_side=True)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(server_address)
        self.server_address = self.socket.getsockname()
        self.socket.listen(5)
        self._is_shut_down = threading.Event()
        try:
            self.setup_environ()
        except Exception:
            self.base_environ = {
                'SERVER_NAME': 'localhost',
                'GATEWAY_INTERFACE': 'CGI/1.1',
                'SERVER_PROTOCOL': 'HTTP/1.1',
                'wsgi.version': (1, 0),
                'wsgi.errors': sys.stderr,
                'wsgi.multithread': True,
                'wsgi.multiprocess': False,
                'wsgi.run_once': False,
            }

    def get_request(self) -> Tuple[socket.socket, Any]:
        conn, addr = self.socket.accept()
        if self._ssl_context is not None:
            pass
        return conn, addr

    def finish_request(self, request: Any, client_address: Any) -> None:
        handler = HybridRequestHandler(self._wsgi_app, self.settings)
        handler(request, client_address, self)

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        self._is_shut_down.clear()
        try:
            self._serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self._is_shut_down.set()
            try:
                self.server_close()
            except Exception:
                pass

    def _serve_forever(self) -> None:
        while not self._is_shut_down.is_set():
            try:
                self.socket.settimeout(0.5)
                self._handle_request_noblock()
            except (socket.timeout, OSError):
                continue

    def _handle_request_noblock(self) -> None:
        try:
            request, client_address = self.get_request()
        except (socket.timeout, OSError):
            return
        t = threading.Thread(target=self.process_request_thread,
                             args=(request, client_address))
        t.daemon = True
        t.start()

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            self.finish_request(request, client_address)
        finally:
            try:
                request.close()
            except Exception:
                pass

    def shutdown(self) -> None:
        self._is_shut_down.set()
        try:
            self.socket.close()
        except Exception:
            pass



def run_http2(host: str, port: int, settings: Any,
              ssl_certfile: str = '', ssl_keyfile: str = '',
              alpn_h2: bool = True, prior_knowledge: bool = True) -> None:
    """Start a server that supports HTTP/1.1 + HTTP/2 on the given host/port.

    If ``ssl_certfile`` and ``ssl_keyfile`` are provided, the server listens
    over TLS and advertises ``h2, http/1.1`` via ALPN. Otherwise it listens
    on cleartext and serves h2c (HTTP/1.1 Upgrade + prior-knowledge).
    """
    from .app import get_application
    app = get_application(settings)
    wsgi = app.wsgi()

    ssl_ctx: Optional[ssl.SSLContext] = None
    if ssl_certfile and ssl_keyfile:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=ssl_certfile, keyfile=ssl_keyfile)
        if alpn_h2:
            try:
                ctx.set_alpn_protocols(['h2', 'http/1.1'])
            except (AttributeError, NotImplementedError):
                pass
        ssl_ctx = ctx

    server = H2WSGIServer((host, port), wsgi, settings, ssl_context=ssl_ctx)
    scheme = 'https' if ssl_ctx else 'http'
    print(f'  Uui.web HTTP/1.1+HTTP/2 server listening on {scheme}://{host}:{port}/', flush=True)
    if ssl_ctx:
        print(f'  (ALPN: h2, http/1.1)', flush=True)
    else:
        print(f'  (h2c via Upgrade + prior-knowledge; for production, use --ssl-cert / --ssl-key)', flush=True)
    print(f'  (use Ctrl+C to stop)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            server.server_close()
        except Exception:
            pass
