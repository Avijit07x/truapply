import errno
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from truapply.core.paths import Paths
from truapply.tracker import resume_upload
from truapply.tracker.extension import EXTENSION_ORIGIN
from truapply.tracker.responses import Response, bad_request, forbidden
from truapply.tracker.views import respond_get, respond_post

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
ANY_FREE_PORT = 0
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
        "connect-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; "
        "base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
NO_STORE = "no-store"
FOREVER = "public, max-age=31536000, immutable"
MAX_BODY_BYTES = 200_000
JSON_TYPE = "application/json"
PENDING_CONNECTIONS = 128
NOT_JSON = "Send a JSON object."
IDLE_CONNECTION_S = 30

log = logging.getLogger(__name__)


class TrackerServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = PENDING_CONNECTIONS

    def __init__(self, paths: Paths, port: int = DEFAULT_PORT) -> None:
        super().__init__((HOST, port), TrackerHandler)
        self.paths = paths
        bound = self.server_address[1]
        self.hosts = frozenset({f"{HOST}:{bound}", f"localhost:{bound}"})
        self.origins = frozenset({EXTENSION_ORIGIN, *(f"http://{host}" for host in self.hosts)})

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.server_address[1]}"


def open_server(paths: Paths, port: int | None) -> TrackerServer:
    if port is not None:
        return TrackerServer(paths, port)
    try:
        return TrackerServer(paths, DEFAULT_PORT)
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        return TrackerServer(paths, ANY_FREE_PORT)


class TrackerHandler(BaseHTTPRequestHandler):
    server_version = "TruApply"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = IDLE_CONNECTION_S

    @property
    def tracker(self) -> TrackerServer:
        if not isinstance(self.server, TrackerServer):
            raise TypeError(self.server)
        return self.server

    def _send(self, response: Response) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", FOREVER if response.cacheable else NO_STORE)
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if self.close_connection:
            self.send_header("Connection", "close")
        try:
            self.end_headers()
            self.wfile.write(response.body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def _host_allowed(self) -> bool:
        return self.headers.get("Host", "") in self.tracker.hosts

    def _post_allowed(self) -> bool:
        kind = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        same_origin = self.headers.get("Origin", "") in self.tracker.origins
        return self._host_allowed() and same_origin and kind == JSON_TYPE

    def _body(self) -> dict[str, object] | None:
        try:
            parsed: object = json.loads(self.rfile.read(self._length()) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return parsed if isinstance(parsed, dict) else None

    def _limit(self) -> int:
        upload = urlsplit(self.path).path == f"/api{resume_upload.PATH}"
        return resume_upload.MAX_UPLOAD_BYTES if upload else MAX_BODY_BYTES

    def _length(self) -> int:
        try:
            return int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return MAX_BODY_BYTES + 1

    def do_GET(self) -> None:
        if not self._host_allowed():
            self._send(forbidden())
            return
        url = urlsplit(self.path)
        query = {key: values[-1] for key, values in parse_qs(url.query).items()}
        self._send(respond_get(self.tracker.paths, url.path, query))

    def do_POST(self) -> None:
        if not self._post_allowed() or not 0 <= self._length() <= self._limit():
            self.close_connection = True
            self._send(forbidden())
            return
        body = self._body()
        if body is None:
            self._send(bad_request(NOT_JSON))
            return
        self._send(respond_post(self.tracker.paths, urlsplit(self.path).path, body))

    def log_message(self, format: str, *args: object) -> None:
        log.debug(format, *args)
