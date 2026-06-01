from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_DIRECT_SOURCE_ARTIFACTS = (
    "src/providers/sec_edgar.py",
    "src/scanners/cninfo_disclosure_events.py",
    "src/scanners/public_news_context.py",
    "src/scanners/stocktwits_heat_signal.py",
    "scripts/run_sec_edgar_source_smoke.py",
    "scripts/run_cninfo_disclosure_event_smoke.py",
    "scripts/run_public_news_context_smoke.py",
    "scripts/run_stocktwits_heat_signal_smoke.py",
    "tests/test_sec_edgar_provider.py",
    "tests/test_cninfo_disclosure_events.py",
    "tests/test_public_news_context.py",
    "tests/test_stocktwits_heat_signal.py",
)


def test_fni_keeps_narrative_source_acquisition_in_gateway() -> None:
    existing = [
        relative_path
        for relative_path in FORBIDDEN_DIRECT_SOURCE_ARTIFACTS
        if (PROJECT_ROOT / relative_path).exists()
    ]

    assert existing == []


def test_fni_keeps_gateway_consumer_surface() -> None:
    assert (PROJECT_ROOT / "src/market_data/providers/narrative_source_gateway.py").exists()
    assert (PROJECT_ROOT / "scripts/run_narrative_source_gateway_probe.py").exists()
    assert (PROJECT_ROOT / "tests/test_narrative_source_gateway_consumer.py").exists()


def test_legacy_cninfo_provider_is_not_live_by_default() -> None:
    source = (PROJECT_ROOT / "src/providers/cninfo.py").read_text(encoding="utf-8")

    assert "urlopen" not in source
    assert "urllib.request" not in source
