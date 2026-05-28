from __future__ import annotations

from typing import Any

TRUST_STATE_DISCLOSURES = {
    "local_fixture": {
        "label_zh": "本地夹具",
        "description_zh": "本地测试或回退夹具，只能用于开发、演示或离线兜底。",
    },
    "candidate_untrusted": {
        "label_zh": "候选未信任",
        "description_zh": "由 intake、规则或人工提出，尚未通过完整证据和可信审核。",
    },
    "reviewed_experimental": {
        "label_zh": "实验性复核",
        "description_zh": (
            "经过有限人工复核或本地种子校验，但来源链条和映射逻辑尚未可信验证。"
        ),
    },
    "ready_for_trust_audit": {
        "label_zh": "待可信审计",
        "description_zh": "预检门槛已满足，等待独立可信审计和 promotion command。",
    },
    "trusted_validated": {
        "label_zh": "可信已验证",
        "description_zh": "已通过证据、理由、排除条件、人工批准、可信审计和 promotion 事务。",
    },
    "rejected": {
        "label_zh": "已拒绝",
        "description_zh": "人工复核或审核流程明确拒绝，不应进入可信映射。",
    },
    "deferred": {
        "label_zh": "已暂缓",
        "description_zh": "需要补充证据或后续判断，暂不进入可信映射。",
    },
}

STATE_ALIASES = {
    "untrusted_experimental": "reviewed_experimental",
    "reviewed_untrusted": "reviewed_experimental",
}


def trust_state_disclosure(value: Any) -> dict[str, str]:
    raw_state = str(value or "local_fixture").strip() or "local_fixture"
    state = STATE_ALIASES.get(raw_state, raw_state)
    disclosure = TRUST_STATE_DISCLOSURES.get(
        state,
        {
            "label_zh": "未知状态",
            "description_zh": "未在当前信任状态机中声明；请检查数据来源或契约版本。",
        },
    )
    label = str(disclosure["label_zh"])
    return {
        "state": state,
        "raw_state": raw_state,
        "label_zh": label,
        "description_zh": str(disclosure["description_zh"]),
        "display_zh": f"{label}（{state}）",
    }


def trust_state_display_zh(value: Any) -> str:
    return trust_state_disclosure(value)["display_zh"]
