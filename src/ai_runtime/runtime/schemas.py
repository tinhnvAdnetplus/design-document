"""Small strict schemas for adapter result channels."""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "steps": {"type": "array", "items": {"type": "string"}},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "steps", "acceptance_criteria", "risks"],
    "additionalProperties": False,
}

IMPLEMENTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "tests": {"type": "array", "items": {"type": "string"}},
        "commit": {
            "type": "string",
            "minLength": 40,
            "maxLength": 40,
            "pattern": "^[0-9a-f]{40}$",
        },
    },
    "required": ["summary", "tests", "commit"],
    "additionalProperties": False,
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        # The runtime enforces the two accepted values after parsing. Antigravity
        # 1.1.10 currently returns an empty structured result for this enum.
        "verdict": {"type": "string"},
        "summary": {"type": "string"},
        "findings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "summary", "findings"],
    "additionalProperties": False,
}
