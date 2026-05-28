from src.scanners.trust_state_disclosure import (
    trust_state_disclosure,
    trust_state_display_zh,
)


def test_trust_state_disclosure_canonicalizes_legacy_reviewed_state():
    disclosure = trust_state_disclosure("untrusted_experimental")

    assert disclosure == {
        "state": "reviewed_experimental",
        "raw_state": "untrusted_experimental",
        "label_zh": "实验性复核",
        "description_zh": "经过有限人工复核或本地种子校验，但来源链条和映射逻辑尚未可信验证。",
        "display_zh": "实验性复核（reviewed_experimental）",
    }


def test_trust_state_display_has_stable_user_facing_labels():
    assert trust_state_display_zh("candidate_untrusted") == (
        "候选未信任（candidate_untrusted）"
    )
    assert trust_state_display_zh("ready_for_trust_audit") == (
        "待可信审计（ready_for_trust_audit）"
    )
    assert trust_state_display_zh("trusted_validated") == (
        "可信已验证（trusted_validated）"
    )
