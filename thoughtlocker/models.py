from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _json_to_obj(value: Any):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
    return None


@dataclass
class PromptSpec:
    name: str
    description: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    web_search: Optional[bool]
    reasoning_effort: Optional[str]
    context_size: Optional[str]
    temperature: Optional[float]
    max_output_tokens: Optional[int]
    system_instruction: str
    use_cases: Optional[List[str]] = field(default=None)
    parameters: Optional[Dict[str, Any]] = field(default=None)
    tags: Optional[List[str]] = field(default=None)
    version: Optional[str] = field(default=None)
    enabled: bool = field(default=True)
    aliases: Optional[List[str]] = field(default=None)
    source: Optional[str] = field(default=None)
    checksum: Optional[str] = field(default=None)
    token_limits: Optional[Dict[str, Any]] = field(default=None)
    notes: Optional[str] = field(default=None)
    created_at: Optional[datetime] = field(default=None)
    updated_at: Optional[datetime] = field(default=None)

    @staticmethod
    def from_row(row: Dict[str, Any]) -> "PromptSpec":
        return PromptSpec(
            name=row["name"],
            description=row.get("description"),
            provider=row.get("provider"),
            model=row.get("model"),
            web_search=row.get("web_search"),
            reasoning_effort=row.get("reasoning_effort"),
            context_size=row.get("context_size"),
            temperature=row.get("temperature"),
            max_output_tokens=row.get("max_output_tokens"),
            system_instruction=row.get("system_instruction") or "",
            use_cases=row.get("use_cases"),
            parameters=_json_to_obj(row.get("parameters")),
            tags=row.get("tags"),
            version=row.get("version"),
            enabled=row.get("enabled", True),
            aliases=row.get("aliases"),
            source=row.get("source"),
            checksum=row.get("checksum"),
            token_limits=_json_to_obj(row.get("token_limits")),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def to_db_params(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "provider": self.provider,
            "model": self.model,
            "web_search": self.web_search,
            "reasoning_effort": self.reasoning_effort,
            "context_size": self.context_size,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "system_instruction": self.system_instruction,
            "use_cases": self.use_cases,
            "parameters": None if self.parameters is None else json.dumps(self.parameters),
            "tags": self.tags,
            "version": self.version,
            "enabled": self.enabled,
            "aliases": self.aliases,
            "source": self.source,
            "checksum": self.checksum,
            "token_limits": None if self.token_limits is None else json.dumps(self.token_limits),
            "notes": self.notes,
        }


