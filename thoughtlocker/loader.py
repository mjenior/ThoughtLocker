import argparse
import hashlib
import json
import logging
from typing import Dict, List, Tuple

import yaml

from .db import get_connection, ensure_schema, transaction
from .models import PromptSpec
from .repository import PromptRepository

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "description",
    "provider",
    "model",
    "web_search",
    "reasoning_effort",
    "context_size",
    "temperature",
    "max_output_tokens",
    "system_instruction",
]


def _compute_checksum(payload: Dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _validate_and_build(name: str, data: Dict) -> PromptSpec:
    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Prompt '{name}' missing required field: {field}")
    metadata_for_checksum = {k: data.get(k) for k in REQUIRED_FIELDS}
    checksum = _compute_checksum(metadata_for_checksum)
    return PromptSpec(
        name=name,
        description=data.get("description"),
        provider=data.get("provider"),
        model=data.get("model"),
        web_search=data.get("web_search"),
        reasoning_effort=data.get("reasoning_effort"),
        context_size=data.get("context_size"),
        temperature=data.get("temperature"),
        max_output_tokens=data.get("max_output_tokens"),
        system_instruction=data.get("system_instruction") or "",
        use_cases=data.get("use_cases"),
        parameters=data.get("parameters"),
        tags=data.get("tags"),
        version=data.get("version"),
        enabled=data.get("enabled", True),
        aliases=data.get("aliases"),
        source=data.get("source"),
        checksum=checksum,
        token_limits=data.get("token_limits"),
        notes=data.get("notes"),
    )


def load_yaml_to_specs(yaml_path: str) -> List[PromptSpec]:
    with open(yaml_path, "r", encoding="utf-8") as f:
        content = yaml.safe_load(f)
    if not isinstance(content, dict):
        raise ValueError("YAML root must be a mapping of name -> spec")
    specs: List[PromptSpec] = []
    for name, data in content.items():
        if not isinstance(data, dict):
            raise ValueError(f"Entry '{name}' must be a mapping of fields")
        spec = _validate_and_build(name, data)
        specs.append(spec)
    return specs


def seed_from_yaml(db_path: str, yaml_path: str) -> Tuple[int, int]:
    conn = get_connection(db_path)
    ensure_schema(conn)
    repo = PromptRepository(conn)
    created = 0
    updated = 0
    with transaction(conn):
        for spec in load_yaml_to_specs(yaml_path):
            existing = repo.get_by_name(spec.name)
            if existing is None:
                repo.upsert(spec)
                created += 1
            else:
                if existing.checksum != spec.checksum:
                    repo.upsert(spec)
                    updated += 1
                else:
                    logger.info("No change for '%s'", spec.name)
    return created, updated


def main():
    parser = argparse.ArgumentParser(description="Seed DuckDB prompt specs from YAML")
    parser.add_argument("--db", required=True, help="Absolute path to DuckDB database file")
    parser.add_argument("--yaml", required=True, help="Path to prompts YAML")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    created, updated = seed_from_yaml(args.db, args.yaml)
    logger.info("Seeding complete. created=%d updated=%d", created, updated)


if __name__ == "__main__":
    main()


