from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from stock_narrative_service.config import ServiceConfig
from stock_narrative_service.storage import NarrativeStore


class NarrativeHTTPServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, config: ServiceConfig):
        super().__init__(server_address, RequestHandlerClass)
        self.config = config
        self.store = NarrativeStore(config)


def create_server(
    server_address: tuple[str, int],
    *,
    config: ServiceConfig | None = None,
) -> NarrativeHTTPServer:
    return NarrativeHTTPServer(
        server_address,
        NarrativeRequestHandler,
        config or ServiceConfig(),
    )


class NarrativeRequestHandler(BaseHTTPRequestHandler):
    server: NarrativeHTTPServer

    def do_GET(self) -> None:  # noqa: N802
        routes = {
            "/api/v1/narratives/registry": self.server.store.registry,
            "/api/v1/narratives/mappings": self.server.store.mappings,
            "/api/v1/narratives/evidence-packs": self.server.store.evidence_packs,
            "/api/v1/narratives/candidates": self.server.store.candidates,
            "/api/v1/narratives/trust-audits/latest": (
                self.server.store.trust_audit_latest
            ),
            "/api/v1/narratives/review-queue": self.server.store.review_queue,
        }
        handler = routes.get(self.path)
        if handler is None:
            self._send_error(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND", "Unknown route.")
            return
        try:
            data = handler()
        except Exception as exc:
            self._send_error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "SERVICE_ERROR",
                str(exc),
            )
            return
        self._send_json(HTTPStatus.OK, _envelope(config=self.server.config, data=data))

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/v1/narratives/intake/events":
            self._send_error(HTTPStatus.NOT_FOUND, "ROUTE_NOT_FOUND", "Unknown route.")
            return
        try:
            payload = self._read_json()
            data = self.server.store.ingest_events(payload)
        except Exception as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, "INVALID_INTAKE_PAYLOAD", str(exc))
            return
        self._send_json(
            HTTPStatus.OK,
            _envelope(
                config=self.server.config,
                data=data,
                trust_status="candidate_untrusted",
            ),
        )

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        del format
        del args

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def _send_error(
        self,
        status: HTTPStatus,
        code: str,
        message: str,
    ) -> None:
        self._send_json(
            status,
            _envelope(
                config=self.server.config,
                status="degraded",
                data={"error": {"code": code, "message": message}},
                warnings=[{"code": code, "message": message}],
            ),
        )

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _envelope(
    *,
    config: ServiceConfig,
    data: dict[str, Any],
    status: str = "available",
    warnings: list[dict[str, Any]] | None = None,
    trust_status: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "source": "narrative_service",
        "provider": config.provider_name,
        "provider_version": config.provider_version,
        "data": data,
        "warnings": warnings or [],
        "trust_metadata": {
            "trust_status": trust_status or _trust_status(data),
            "trust_note": (
                "Service preserves source trust state; candidate intake is not "
                "trusted promotion."
            ),
        },
    }


def _trust_status(data: dict[str, Any]) -> str:
    metadata = data.get("trust_metadata")
    if isinstance(metadata, dict):
        return str(metadata.get("trust_status") or "untrusted_experimental")
    if isinstance(data.get("trust_status"), str):
        return str(data["trust_status"])
    return "untrusted_experimental"

