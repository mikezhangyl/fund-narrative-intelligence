from __future__ import annotations

import json
from pathlib import Path

from scripts.report_data_capabilities import build_inventory_report, build_report
from src.market_data.capabilities import (
    DataCapabilityRegistry,
    load_data_capability_registry,
)
from src.market_data.gateway_contract import load_gateway_contract


def test_data_capability_registry_loads_datasets_and_analysis_links():
    registry = load_data_capability_registry()

    daily_bars = registry.dataset("a_share_daily_bars")
    assert daily_bars.current_status == "available"
    assert daily_bars.primary_source.provider == "tushare"
    assert daily_bars.primary_source.endpoint == "daily"
    assert daily_bars.gateway_mode == "gateway_ready"

    northbound = registry.dataset("northbound_capital")
    assert northbound.current_status == "available"
    assert northbound.gateway_mode == "gateway_ready"

    sector_constituents = registry.dataset("sector_constituents")
    assert sector_constituents.current_status == "available"
    assert sector_constituents.gateway_mode == "gateway_ready"

    stock_membership = registry.dataset("stock_sector_membership")
    assert stock_membership.current_status == "unstable"
    assert stock_membership.gateway_mode == "gateway_ready"

    fund_holdings = registry.dataset("fund_holdings")
    assert fund_holdings.current_status == "available"
    assert fund_holdings.gateway_mode == "gateway_ready"

    breadth = registry.analysis_capability("market_breadth_ma20")
    assert "a_share_daily_bars" in breadth.required_datasets
    assert "trade_calendar" in breadth.required_datasets
    assert registry.missing_datasets_for_analysis("market_breadth_ma20") == []

    structure_mapping = registry.analysis_readiness("structure_mapping_report")
    assert structure_mapping["can_run"] is True
    assert structure_mapping["blockers"] == []


def test_data_capability_registry_summary_counts_status_and_difficulty():
    registry = load_data_capability_registry()

    summary = registry.summary()

    assert summary["dataset_count"] >= 10
    assert summary["analysis_capability_count"] >= 5
    assert summary["dataset_status_counts"]["available"] >= 5
    assert summary["dataset_status_counts"]["unstable"] >= 1
    assert summary["difficulty_counts"]["medium"] >= 1
    assert summary["gateway_mode_counts"]["gateway_ready"] >= 1


def test_data_capability_registry_covers_available_gateway_contract_datasets():
    registry = load_data_capability_registry()
    contract = load_gateway_contract()

    coverage = registry.gateway_contract_coverage(contract)

    assert coverage["missing_dataset_ids"] == []
    assert coverage["planned_contract_dataset_ids"] == []
    assert "etf_spot_ranking" in coverage["covered_dataset_ids"]
    assert "news_briefs" in coverage["covered_dataset_ids"]


def test_data_capability_registry_declares_gateway_ownership_policy():
    registry = load_data_capability_registry()

    policy = registry.ownership_policy

    assert policy["external_source_expansion_owner"] == "stock-data-gateway"
    assert policy["fni_role"] == "consumer_of_gateway_contracts"
    assert policy["direct_external_source_rule"] == "gateway_change_request_first"
    assert policy["report_disclosure_required"] is True
    assert policy["change_request_location"].endswith("/stock-data-gateway/docs/product/")


def test_data_capability_registry_reports_analysis_readiness_with_warnings():
    registry = load_data_capability_registry()

    breadth = registry.analysis_readiness("market_breadth_ma20")
    sector = registry.analysis_readiness("sector_rotation_scan")
    cost_basis = registry.analysis_readiness("cost_basis_analysis")
    holding_sector = registry.analysis_readiness("holding_sector_exposure")
    fund_gateway = registry.analysis_readiness("fund_gateway_foundation")
    fund_exposure = registry.analysis_readiness("fund_holding_exposure_report")
    fund_comparison = registry.analysis_readiness("fund_exposure_comparison_report")
    fund_matrix = registry.analysis_readiness("fund_narrative_exposure_matrix_report")

    assert breadth["can_run"] is True
    assert breadth["blockers"] == []
    assert breadth["warnings"] == []
    assert sector["can_run"] is True
    assert "unstable_dataset:sector_concepts" in sector["warnings"]
    assert cost_basis["can_run"] is True
    assert "planned_dataset:cyq_chips" not in cost_basis["blockers"]
    assert holding_sector["can_run"] is True
    assert "unstable_dataset:stock_sector_membership" in holding_sector["warnings"]
    assert fund_gateway["can_run"] is True
    assert fund_gateway["blockers"] == []
    assert fund_exposure["can_run"] is True
    assert "unstable_dataset:stock_sector_membership" in fund_exposure["warnings"]
    assert fund_comparison["can_run"] is True
    assert "unstable_dataset:stock_sector_membership" in fund_comparison["warnings"]
    assert fund_matrix["can_run"] is True
    assert "unstable_dataset:stock_sector_membership" in fund_matrix["warnings"]


def test_data_capability_registry_rejects_unknown_required_dataset(tmp_path: Path):
    config_path = tmp_path / "bad_capabilities.yaml"
    config_path.write_text(
        """
version: data-capabilities-v1
updated_at: "2026-05-25"
purpose: Test registry
datasets:
  known_dataset:
    description: Known
    current_status: available
    acquisition_difficulty: low
    gateway_mode: direct_only
    required_fields: [field]
    freshness: daily
    primary_source:
      provider: test
      endpoint: known
      access_mode: fixture
analysis_capabilities:
  broken_analysis:
    description: Broken
    complexity: simple
    implementation_status: planned
    required_datasets: [missing_dataset]
""",
        encoding="utf-8",
    )

    try:
        DataCapabilityRegistry.from_yaml(config_path)
    except ValueError as exc:
        assert "missing_dataset" in str(exc)
    else:
        raise AssertionError("expected unknown dataset validation failure")


def test_data_capability_report_builds_markdown_and_json():
    registry = load_data_capability_registry()

    markdown = build_report(registry, output_format="markdown")
    assert "# Data Capability Registry" in markdown
    assert "## Gateway Ownership Boundary" in markdown
    assert "stock-data-gateway" in markdown
    assert "a_share_daily_bars" in markdown
    assert "market_breadth_ma20" in markdown

    payload = json.loads(build_report(registry, output_format="json"))
    assert (
        payload["ownership_policy"]["external_source_expansion_owner"]
        == "stock-data-gateway"
    )
    assert payload["summary"]["dataset_count"] == len(registry.datasets)
    assert payload["datasets"]["a_share_daily_bars"]["primary_source"]["provider"] == "tushare"


def test_data_capability_inventory_groups_datasets_and_status_labels():
    registry = load_data_capability_registry()

    inventory = build_inventory_report(registry)

    group_ids = {group["group_id"] for group in inventory["inventory_groups"]}
    assert {
        "daily_bars",
        "fund_holdings",
        "sectors",
        "flows",
        "structure_mapping",
        "news",
        "cyq",
        "narrative_service",
    }.issubset(group_ids)
    assert set(inventory["status_labels"]) == {"can_do", "unstable", "blocked", "future"}

    rows_by_id = {row["dataset_id"]: row for row in inventory["dataset_rows"]}
    daily_bars = rows_by_id["a_share_daily_bars"]
    assert daily_bars["group_id"] == "daily_bars"
    assert daily_bars["fni_consumer_status"] == "available"
    assert daily_bars["source_provider"] == "tushare"
    assert daily_bars["last_smoke_status"]
    assert daily_bars["degradation_behavior"]
    assert daily_bars["trust_stability_label"] == "can_do"

    assert rows_by_id["etf_spot_ranking"]["group_id"] == "daily_bars"
    assert all(row["group_id"] != "other" for row in inventory["dataset_rows"])

    stock_membership = rows_by_id["stock_sector_membership"]
    assert stock_membership["group_id"] == "sectors"
    assert stock_membership["trust_stability_label"] == "unstable"
    assert "degraded" in stock_membership["degradation_behavior"].lower()

    narrative = rows_by_id["narrative_service"]
    assert narrative["group_id"] == "narrative_service"
    assert narrative["source_provider"] == "narrative-service"
    assert narrative["trust_stability_label"] == "can_do"


def test_data_capability_report_builds_html_summary():
    registry = load_data_capability_registry()

    html = build_report(registry, output_format="html")

    assert "<!doctype html>" in html
    assert 'lang="zh-CN"' in html
    assert "数据能力清单" in html
    assert "Can-Do" in html
    assert "unstable" in html
    assert "narrative_service" in html
