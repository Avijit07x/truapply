import logging
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from satyaapply.core.paths import Paths
from satyaapply.store.db import connect
from satyaapply.tracker.responses import Response
from satyaapply.tracker.views import respond_get, respond_post

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
MAX_FORM_BYTES = 200_000
FORBIDDEN = Response(HTTPStatus.FORBIDDEN, b"Forbidden", "text/plain; charset=utf-8")

log = logging.getLogger(__name__)


class TrackerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, paths: Paths, port: int = DEFAULT_PORT) -> None:
        super().__init__((HOST, port), TrackerHandler)
        self.paths = paths
        bound = self.server_address[1]
        self.hosts = frozenset({f"{HOST}:{bound}", f"localhost:{bound}"})
        self.origins = frozenset(f"http://{host}" for host in self.hosts)

    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.server_address[1]}"


class TrackerHandler(BaseHTTPRequestHandler):
    server_version = "SatyaApply"
    sys_version = ""

    @property
    def tracker(self) -> TrackerServer:
        if not isinstance(self.server, TrackerServer):
            raise TypeError(self.server)
        return self.server

    def _send(self, response: Response) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        if response.location:
            self.send_header("Location", response.location)
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(response.body)

    def _host_allowed(self) -> bool:
        return self.headers.get("Host", "") in self.tracker.hosts

    def _same_origin(self) -> bool:
        return self.headers.get("Origin", "") in self.tracker.origins

    def do_GET(self) -> None:
        if not self._host_allowed():
            self._send(FORBIDDEN)
            return
        url = urlsplit(self.path)
        with closing(connect(self.tracker.paths.database)) as db:
            self._send(respond_get(db, self.tracker.paths, url.path, parse_qs(url.query)))

    def do_POST(self) -> None:
        if not (self._host_allowed() and self._same_origin()):
            self._send(FORBIDDEN)
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_FORM_BYTES:
            self._send(FORBIDDEN)
            return
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = {key: values[-1] for key, values in parse_qs(raw, keep_blank_values=True).items()}
        with closing(connect(self.tracker.paths.database)) as db:
            self._send(respond_post(db, self.tracker.paths, urlsplit(self.path).path, form))

    def log_message(self, format: str, *args: object) -> None:
        log.debug(format, *args)
