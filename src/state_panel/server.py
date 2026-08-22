"""Lightweight web and API server for State Panel."""

import asyncio
import contextlib
import json
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from state_panel.config import PanelConfig
from state_panel.engine import Engine


class StatePanelHTTPHandler(SimpleHTTPRequestHandler):
    """Custom request handler serving static frontend and live check APIs."""

    engine: Engine
    web_dir: Path

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(self.web_dir), **kwargs)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for static files and /api/status."""
        if self.path.startswith("/api/status"):
            self._handle_get_status()
        elif self.path.startswith("/api/check"):
            self._handle_trigger_check()
        else:
            super().do_GET()

    def do_POST(self) -> None:
        """Handle POST requests to trigger checks on demand."""
        if self.path.startswith("/api/check"):
            self._handle_trigger_check()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _handle_get_status(self) -> None:
        """Return latest status JSON."""
        status_file = Path(self.engine.config.settings.output_dir) / "status.json"
        if status_file.exists():
            with open(status_file, encoding="utf-8") as f:
                data = f.read()
        else:
            # Generate on the fly
            _, out_path = asyncio.run(self.engine.run_and_export())
            with open(out_path, encoding="utf-8") as f:
                data = f.read()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(data.encode("utf-8"))

    def _handle_trigger_check(self) -> None:
        """Execute live checks on demand and return fresh JSON."""
        try:
            _, out_path = asyncio.run(self.engine.run_and_export())
            with open(out_path, encoding="utf-8") as f:
                payload = json.load(f)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.end_headers()
            err_body = json.dumps({"error": str(exc)})
            self.wfile.write(err_body.encode("utf-8"))


def start_server(
    config: PanelConfig,
    host: str = "127.0.0.1",
    port: int = 8000,
    web_dir: str | Path | None = None,
) -> None:
    """Start local web server with API and background monitoring daemon."""
    engine = Engine(config)

    # Determine directory to serve
    if web_dir:
        static_dir = Path(web_dir)
    elif Path("web/dist").exists():
        static_dir = Path("web/dist")
    else:
        static_dir = Path("web/public")

    # Initial check & export
    asyncio.run(engine.run_and_export())

    StatePanelHTTPHandler.engine = engine
    StatePanelHTTPHandler.web_dir = static_dir.resolve()

    # Background monitoring thread
    def _background_checker() -> None:
        interval = max(config.settings.refresh_interval_seconds, 10)
        while True:
            time.sleep(interval)
            with contextlib.suppress(Exception):
                asyncio.run(engine.run_and_export())

    bg_thread = threading.Thread(target=_background_checker, daemon=True)
    bg_thread.start()

    server = ThreadingHTTPServer((host, port), StatePanelHTTPHandler)
    server.serve_forever()
