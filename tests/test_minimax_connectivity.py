import json
import os
from types import SimpleNamespace

import pytest
from src.local_env import get_config_value
from src.modules.narrative_intelligence import (
    candidate_generation as candidate_generation_module,
)
from src.modules.narrative_intelligence.candidate_generation import (
    MiniMaxNarrativeCurator,
    NarrativeCurationError,
    build_generated_candidates,
)

TEST_MINIMAX_KEY = "test-minimax-key"


def _realistic_curator_inputs() -> tuple[dict, list[dict], list[dict]]:
    seed = {
        "seed_id": "SEED_TEST_515880",
        "seed_type": "exposure_tag_cluster",
        "triggering_stock_codes": ["002281", "600487", "600498", "600522"],
        "related_exclusion_ids": [],
        "supporting_source_item_ids": [
            "SRC_FINANCIAL_002281",
            "SRC_FINANCIAL_600487",
            "SRC_ANNOUNCEMENT_600522",
        ],
        "supporting_company_fact_ids": [
            "FACT_002281",
            "FACT_600487",
            "FACT_600498",
            "FACT_600522",
        ],
        "supporting_source_types": ["announcement", "financial_metric"],
        "supporting_fact_types": ["财务表现", "行业身份"],
        "key_terms": ["光通信"],
        "term_signature": ["光通信"],
        "supporting_item_count": 3,
        "distinct_source_type_count": 2,
        "seed_rationale": "Cross-stock exposure tag cluster for 光通信 across 4 holdings.",
        "first_seen_at": "2026-03-31",
    }
    holdings = [
        {
            "stock_code": "002281",
            "stock_name": "光迅科技",
            "industry": "通信",
            "weight": 0.0209,
        },
        {
            "stock_code": "600487",
            "stock_name": "亨通光电",
            "industry": "通信",
            "weight": 0.0530,
        },
        {
            "stock_code": "600498",
            "stock_name": "烽火通信",
            "industry": "通信",
            "weight": 0.0211,
        },
        {
            "stock_code": "600522",
            "stock_name": "中天科技",
            "industry": "通信",
            "weight": 0.0420,
        },
    ]
    source_items = [
        {
            "source_item_id": "SRC_FINANCIAL_002281",
            "source_type": "financial_metric",
            "provider_name": "eastmoney-financial-metrics",
            "stock_code": "002281",
            "stock_name": "光迅科技",
            "event_date": "2026-03-31",
            "title": "Financial metrics for 光迅科技",
            "summary": "光迅科技一季报收入和利润同比增长，业务聚焦光通信器件。",
            "source_url": "https://example.com/financial/002281",
        },
        {
            "source_item_id": "SRC_FINANCIAL_600487",
            "source_type": "financial_metric",
            "provider_name": "eastmoney-financial-metrics",
            "stock_code": "600487",
            "stock_name": "亨通光电",
            "event_date": "2026-03-31",
            "title": "Financial metrics for 亨通光电",
            "summary": "亨通光电一季报收入和利润同比增长，主营光通信与海缆相关业务。",
            "source_url": "https://example.com/financial/600487",
        },
        {
            "source_item_id": "SRC_ANNOUNCEMENT_600522",
            "source_type": "announcement",
            "provider_name": "announcements",
            "stock_code": "600522",
            "stock_name": "中天科技",
            "event_date": "2026-03-30",
            "title": "江苏中天科技股份有限公司关于第六期以集中竞价交易方式回购股份方案的公告暨回购报告书",
            "summary": "中天科技公告披露最新资本运作信息，市场通常将其视为光通信链公司之一。",
            "source_url": "https://example.com/announcement/600522",
        },
    ]
    return seed, holdings, source_items


def test_minimax_curator_uses_realistic_china_a_share_prompt(monkeypatch):
    seed, holdings, source_items = _realistic_curator_inputs()
    captured: dict[str, object] = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text=json.dumps(
                            {
                                "name": "光通信",
                                "canonical_taxonomy": "通信",
                                "aliases": ["光通信"],
                                "related_terms": ["光通信", "光纤"],
                                "rationale": "由多只通信持仓共同触发。",
                                "definition": "光通信是围绕光纤、光器件与通信网络建设展开的主题。",
                                "inclusion_criteria": [
                                    "至少两只核心持仓反复呈现光通信线索。"
                                ],
                                "exclusion_criteria": [
                                    "不能只是单一公司事件。"
                                ],
                                "confidence": 0.79,
                                "representative_citation_ids": [
                                    "SRC_FINANCIAL_002281",
                                    "SRC_FINANCIAL_600487",
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    )
                ]
            )

    class FakeAnthropicClient:
        def __init__(self, *, base_url, api_key):
            captured["base_url"] = base_url
            captured["api_key"] = api_key
            self.messages = FakeMessages()

    class FakeAnthropicModule:
        Anthropic = FakeAnthropicClient

    monkeypatch.setattr(
        candidate_generation_module,
        "import_module",
        lambda name: FakeAnthropicModule if name == "anthropic" else None,
    )

    curator = MiniMaxNarrativeCurator(
        **{"api_key": TEST_MINIMAX_KEY},
        model="MiniMax-M2.7",
        base_url="https://api.minimaxi.com/anthropic",
    )
    candidate = curator.curate_candidate(
        seed=seed,
        source_items=source_items,
        holdings=holdings,
    )

    assert captured["base_url"] == "https://api.minimaxi.com/anthropic"
    assert captured["api_key"] == TEST_MINIMAX_KEY
    assert captured["model"] == "MiniMax-M2.7"
    assert "China A-share investment research system" in captured["system"]
    assert "must be in Chinese" in captured["system"]
    request_payload = json.loads(captured["messages"][0]["content"])
    assert request_payload["seed"]["key_terms"] == ["光通信"]
    assert request_payload["holdings"][0]["stock_name"] == "光迅科技"
    assert request_payload["source_items"][0]["stock_name"] == "光迅科技"
    assert request_payload["fallback_candidate"]["canonical_name_zh"] == "光通信"
    assert candidate["canonical_name_zh"] == "光通信"
    assert candidate["derivation"]["curation_provider"] == "minimax-narrative-curator"


def test_minimax_curator_records_stop_reason_when_response_is_not_json(monkeypatch):
    seed, holdings, source_items = _realistic_curator_inputs()

    class FakeMessages:
        def create(self, **kwargs):
            del kwargs
            return SimpleNamespace(
                stop_reason="max_tokens",
                content=[
                    SimpleNamespace(
                        type="text",
                        text=(
                            "先分析这些持仓之间的共同点，再判断可能的主题方向。"
                            "这个回答不是 JSON。"
                        ),
                    )
                ],
            )

    class FakeAnthropicClient:
        def __init__(self, *, base_url, api_key):
            del base_url, api_key
            self.messages = FakeMessages()

    class FakeAnthropicModule:
        Anthropic = FakeAnthropicClient

    monkeypatch.setattr(
        candidate_generation_module,
        "import_module",
        lambda name: FakeAnthropicModule if name == "anthropic" else None,
    )

    curator = MiniMaxNarrativeCurator(**{"api_key": TEST_MINIMAX_KEY})
    with pytest.raises(NarrativeCurationError) as excinfo:
        curator.curate_candidate(
            seed=seed,
            source_items=source_items,
            holdings=holdings,
        )

    assert excinfo.value.provider_name == "minimax-narrative-curator"
    assert excinfo.value.attempt_count == 3
    assert "stop_reason=max_tokens" in excinfo.value.reason
    assert "这个回答不是 JSON" in excinfo.value.reason


def test_minimax_curator_retries_transient_failure_then_succeeds(monkeypatch):
    seed, holdings, source_items = _realistic_curator_inputs()
    attempts = {"count": 0}

    class FakeMessages:
        def create(self, **kwargs):
            del kwargs
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise TimeoutError("temporary network jitter")
            return SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="text",
                        text=json.dumps(
                            {
                                "name": "光通信",
                                "canonical_taxonomy": "通信",
                                "aliases": ["光通信"],
                                "related_terms": ["光通信"],
                                "rationale": "重试后成功返回。",
                                "definition": "光通信是围绕光纤与通信网络建设展开的主题。",
                                "inclusion_criteria": ["至少两只持仓共同指向光通信。"],
                                "exclusion_criteria": ["不能只是单一公司事件。"],
                                "confidence": 0.8,
                                "representative_citation_ids": [
                                    "SRC_FINANCIAL_002281"
                                ],
                            },
                            ensure_ascii=False,
                        ),
                    )
                ]
            )

    class FakeAnthropicClient:
        def __init__(self, *, base_url, api_key):
            del base_url, api_key
            self.messages = FakeMessages()

    class FakeAnthropicModule:
        Anthropic = FakeAnthropicClient

    monkeypatch.setattr(
        candidate_generation_module,
        "import_module",
        lambda name: FakeAnthropicModule if name == "anthropic" else None,
    )

    curator = MiniMaxNarrativeCurator(
        **{"api_key": TEST_MINIMAX_KEY},
        retry_delay_seconds=0,
    )
    candidate = curator.curate_candidate(
        seed=seed,
        source_items=source_items,
        holdings=holdings,
    )

    assert attempts["count"] == 3
    assert candidate["canonical_name_zh"] == "光通信"
    assert candidate["derivation"]["curation_provider"] == "minimax-narrative-curator"


def test_build_generated_candidates_records_curation_failures_without_fallback():
    seed, holdings, source_items = _realistic_curator_inputs()

    class FailingCurator:
        def curate_candidate(self, *, seed, source_items, holdings):
            del seed, source_items, holdings
            raise NarrativeCurationError(
                provider_name="minimax-narrative-curator",
                provider_version="anthropic-compatible-v1",
                model="MiniMax-M2.7",
                reason="timeout after retries",
                attempt_count=3,
            )

    payload = build_generated_candidates(
        candidate_seeds={
            "items": [seed],
            "summary": {"seed_count": 1},
        },
        source_catalog={"items": source_items},
        holdings=holdings,
        curator=FailingCurator(),
    )

    assert payload["items"] == []
    assert payload["summary"] == {
        "generated_candidate_count": 0,
        "failed_candidate_count": 1,
        "attempted_seed_count": 1,
    }
    assert payload["failures"] == [
        {
            "seed_id": "SEED_TEST_515880",
            "seed_type": "exposure_tag_cluster",
            "provider_name": "minimax-narrative-curator",
            "provider_version": "anthropic-compatible-v1",
            "model": "MiniMax-M2.7",
            "attempt_count": 3,
            "reason": "timeout after retries",
            "triggering_stock_codes": ["002281", "600487", "600498", "600522"],
            "supporting_source_item_ids": [
                "SRC_FINANCIAL_002281",
                "SRC_FINANCIAL_600487",
                "SRC_ANNOUNCEMENT_600522",
            ],
        }
    ]


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_MINIMAX_TESTS") != "1",
    reason="Set RUN_LIVE_MINIMAX_TESTS=1 to run live MiniMax connectivity checks.",
)
def test_minimax_live_connectivity_with_realistic_prompt():
    api_key = get_config_value("MINIMAX_API_KEY")
    if not api_key:
        pytest.skip("MINIMAX_API_KEY is not configured.")

    seed, holdings, source_items = _realistic_curator_inputs()
    curator = MiniMaxNarrativeCurator(
        **{"api_key": api_key},
        model=get_config_value("MINIMAX_MODEL") or "MiniMax-M2.7",
        base_url=(
            get_config_value("MINIMAX_ANTHROPIC_BASE_URL")
            or "https://api.minimaxi.com/anthropic"
        ),
    )
    candidate = curator.curate_candidate(
        seed=seed,
        source_items=source_items,
        holdings=holdings,
    )
    assert candidate["derivation"]["curation_provider"] == "minimax-narrative-curator"
    assert candidate["canonical_name_zh"]
    assert candidate["definition_zh"]
