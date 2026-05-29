from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from stock_narrative_service.config import ServiceConfig
from stock_narrative_service.diagnostics import (
    operational_diagnostics,
    warning_payload,
)
from stock_narrative_service.storage import NarrativeStore, PromotionGateError


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
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "service": self.server.config.provider_name,
                    "provider_version": self.server.config.provider_version,
                },
            )
            return
        if path == "/api/v1/narratives/evidence-packs/detail":
            data = self.server.store.evidence_pack_detail(
                stock_code=_first_query_value(query, "stock_code"),
                narrative_id=_first_query_value(query, "narrative_id"),
            )
            if data is None:
                self._send_missing(
                    code="EVIDENCE_PACK_NOT_FOUND",
                    message="Evidence pack not found for the requested lookup.",
                    data={
                        "lookup": {
                            "stock_code": _first_query_value(query, "stock_code"),
                            "narrative_id": _first_query_value(query, "narrative_id"),
                        }
                    },
                )
                return
            self._send_json(
                HTTPStatus.OK,
                _envelope(
                    config=self.server.config,
                    data=data,
                    trust_status="candidate_untrusted",
                ),
            )
            return
        evidence_detail_prefix = "/api/v1/narratives/evidence-packs/"
        if path.startswith(evidence_detail_prefix):
            evidence_pack_id = unquote(path.removeprefix(evidence_detail_prefix)).strip()
            data = self.server.store.evidence_pack_detail(
                evidence_pack_id=evidence_pack_id,
            )
            if data is None:
                self._send_missing(
                    code="EVIDENCE_PACK_NOT_FOUND",
                    message=f"Evidence pack not found: {evidence_pack_id}",
                    data={"evidence_pack_id": evidence_pack_id},
                )
                return
            self._send_json(
                HTTPStatus.OK,
                _envelope(
                    config=self.server.config,
                    data=data,
                    trust_status="candidate_untrusted",
                ),
            )
            return
        candidate_detail_prefix = "/api/v1/narratives/candidates/"
        if path.startswith(candidate_detail_prefix):
            candidate_id = unquote(path.removeprefix(candidate_detail_prefix)).strip()
            data = self.server.store.candidate_detail(candidate_id)
            if data is None:
                code = "CANDIDATE_NOT_FOUND"
                message = f"Candidate narrative not found: {candidate_id}"
                self._send_missing(
                    code=code,
                    message=message,
                    data={"candidate_narrative_id": candidate_id},
                )
                return
            self._send_json(
                HTTPStatus.OK,
                _envelope(
                    config=self.server.config,
                    data=data,
                    trust_status="candidate_untrusted",
                ),
            )
            return
        routes = {
            "/api/v1/narratives/registry": self.server.store.registry,
            "/api/v1/narratives/mappings": self.server.store.mappings,
            "/api/v1/narratives/evidence-packs": self.server.store.evidence_packs,
            "/api/v1/narratives/candidates": self.server.store.candidates,
            "/api/v1/narratives/radar/contract": self.server.store.radar_contract,
            "/api/v1/narratives/radar/signals": self.server.store.radar_signals,
            "/api/v1/narratives/trust-audits/latest": (
                self.server.store.trust_audit_latest
            ),
            "/api/v1/narratives/ops/summary": self.server.store.ops_summary,
            "/api/v1/narratives/review-actions": self.server.store.review_actions,
        }
        if path == "/api/v1/narratives/review-queue":
            handler = lambda: self.server.store.review_queue(  # noqa: E731
                status=_first_query_value(query, "status")
            )
        else:
            handler = routes.get(path)
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
        if self.path == "/api/v1/narratives/promotion/commit":
            try:
                payload = self._read_json()
                data = self.server.store.commit_promotion(payload)
            except PromotionGateError as exc:
                self._send_promotion_gate_error(exc)
                return
            except Exception as exc:
                self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "INVALID_PROMOTION_COMMIT",
                    str(exc),
                )
                return
            self._send_json(
                HTTPStatus.OK,
                _envelope(
                    config=self.server.config,
                    data=data,
                    trust_status="trusted_validated",
                ),
            )
            return
        if self.path == "/api/v1/narratives/promotion/preflight":
            try:
                payload = self._read_json()
                data = self.server.store.promotion_preflight(payload)
            except Exception as exc:
                self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "INVALID_PROMOTION_PREFLIGHT",
                    str(exc),
                )
                return
            self._send_json(
                HTTPStatus.OK,
                _envelope(
                    config=self.server.config,
                    data=data,
                    trust_status="candidate_untrusted",
                ),
            )
            return
        if self.path == "/api/v1/narratives/review-actions":
            try:
                payload = self._read_json()
                data = self.server.store.apply_review_action(payload)
            except Exception as exc:
                self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "INVALID_REVIEW_ACTION",
                    str(exc),
                )
                return
            self._send_json(
                HTTPStatus.OK,
                _envelope(
                    config=self.server.config,
                    data=data,
                    trust_status="candidate_untrusted",
                ),
            )
            return
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
                warnings=[
                    warning_payload(
                        code=code,
                        message=message,
                        classification=(
                            "system_failure"
                            if code == "SERVICE_ERROR"
                            else "invalid_request"
                        ),
                    )
                ],
            ),
        )

    def _send_missing(
        self,
        *,
        code: str,
        message: str,
        data: dict[str, Any],
    ) -> None:
        self._send_json(
            HTTPStatus.OK,
            _envelope(
                config=self.server.config,
                status="missing",
                data={
                    **data,
                    "error": {"code": code, "message": message},
                },
                warnings=[
                    warning_payload(
                        code=code,
                        message=message,
                        classification="product_data_gap",
                    )
                ],
                trust_status="candidate_untrusted",
            ),
        )

    def _send_promotion_gate_error(self, exc: PromotionGateError) -> None:
        code = "PROMOTION_GATES_MISSING"
        message = str(exc)
        self._send_json(
            HTTPStatus.BAD_REQUEST,
            _envelope(
                config=self.server.config,
                status="failed",
                data={
                    "candidate_narrative_id": exc.candidate_id,
                    "missing_gates": exc.missing_gates,
                    "promotion_effect": "none",
                    "error": {"code": code, "message": message},
                },
                warnings=[
                    warning_payload(
                        code=code,
                        message=message,
                        classification="product_data_gap",
                    )
                ],
                trust_status="candidate_untrusted",
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
        "diagnostics": operational_diagnostics(
            config=config,
            status=status,
            warnings=warnings or [],
        ),
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


def _first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key, [])
    return str(values[0]).strip() if values else ""
