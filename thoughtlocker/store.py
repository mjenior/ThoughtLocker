import logging
from typing import List, Optional

import duckdb

from .db import get_connection, ensure_schema, transaction
from .models import PromptSpec
from .repository import PromptRepository
from .loader import load_yaml_to_specs


logger = logging.getLogger(__name__)


class Locker:
    """
    High-level, importable API for prompt management.

    This wraps DuckDB connection handling and exposes convenient methods
    for use within multi-agent LLM systems.
    """

    def __init__(self, db_path: str = "prompts.duckdb"):
        self._db_path: str = db_path
        self._conn: duckdb.DuckDBPyConnection = get_connection(db_path)
        ensure_schema(self._conn)
        self._repo: PromptRepository = PromptRepository(self._conn)

    # ---------- lifecycle ----------
    def close(self) -> None:
        try:
            self._conn.close()
        except Exception as exc:
            logger.warning("Error closing DuckDB connection: %s", exc)

    def __enter__(self) -> "Locker":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---------- retrieval ----------
    def get(self, name_or_alias: str) -> PromptSpec:
        spec = self._repo.get_by_name_or_alias(name_or_alias)
        if spec is None:
            raise KeyError(f"Prompt spec not found: {name_or_alias}")
        return spec

    def try_get(self, name_or_alias: str) -> Optional[PromptSpec]:
        return self._repo.get_by_name_or_alias(name_or_alias)

    def get_system_instruction(self, name_or_alias: str) -> str:
        return self.get(name_or_alias).system_instruction

    # ---------- listing/search ----------
    def list(self, enabled: Optional[bool] = None) -> List[PromptSpec]:
        return self._repo.list(enabled=enabled)

    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        provider: Optional[str] = None,
        limit: int = 50,
    ) -> List[PromptSpec]:
        return self._repo.search(query=query, tags=tags, provider=provider, limit=limit)

    # ---------- mutation ----------
    def upsert(self, spec: PromptSpec) -> None:
        with transaction(self._conn):
            self._repo.upsert(spec)

    def seed_from_yaml(self, yaml_path: str) -> None:
        """Load prompt specs from YAML and upsert them transactionally."""
        specs = load_yaml_to_specs(yaml_path)
        with transaction(self._conn):
            for spec in specs:
                self._repo.upsert(spec)


