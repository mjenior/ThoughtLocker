import logging
from typing import Any, Dict, List, Optional

import duckdb

from .models import PromptSpec

logger = logging.getLogger(__name__)


class PromptRepository:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn

    def upsert(self, spec: PromptSpec) -> None:
        """
        Insert or update a prompt spec by name, preserving created_at when updating.
        """
        row = self._get_row(spec.name)
        params = spec.to_db_params()
        if row is None:
            logger.info("Inserting new prompt spec: %s", spec.name)
            self.conn.execute(
                """
                INSERT INTO prompt_specs (
                    name, description, provider, model, web_search, reasoning_effort, context_size,
                    temperature, max_output_tokens, system_instruction, use_cases, parameters, tags,
                    version, enabled, aliases, source, checksum, token_limits, notes
                ) VALUES (
                    $name, $description, $provider, $model, $web_search, $reasoning_effort, $context_size,
                    $temperature, $max_output_tokens, $system_instruction, $use_cases, $parameters, $tags,
                    $version, $enabled, $aliases, $source, $checksum, $token_limits, $notes
                );
                """,
                params,
            )
            self._insert_version_row(spec.name, action="insert")
        else:
            logger.info("Updating existing prompt spec: %s", spec.name)
            self.conn.execute(
                """
                UPDATE prompt_specs SET
                    description = $description,
                    provider = $provider,
                    model = $model,
                    web_search = $web_search,
                    reasoning_effort = $reasoning_effort,
                    context_size = $context_size,
                    temperature = $temperature,
                    max_output_tokens = $max_output_tokens,
                    system_instruction = $system_instruction,
                    use_cases = $use_cases,
                    parameters = $parameters,
                    tags = $tags,
                    version = $version,
                    enabled = $enabled,
                    aliases = $aliases,
                    source = $source,
                    checksum = $checksum,
                    token_limits = $token_limits,
                    notes = $notes,
                    updated_at = current_timestamp
                WHERE name = $name;
                """,
                params,
            )
            self._insert_version_row(spec.name, action="update")

    def _get_row(self, name: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM prompt_specs WHERE name = $name LIMIT 1;",
            {"name": name},
        )
        res = cur.fetchone()
        if res is None:
            return None
        col_names = [d[0] for d in cur.description]
        return {k: v for k, v in zip(col_names, res)}

    def get_by_name(self, name: str) -> Optional[PromptSpec]:
        row = self._get_row(name)
        return PromptSpec.from_row(row) if row else None

    def get_by_name_or_alias(self, name_or_alias: str) -> Optional[PromptSpec]:
        """Retrieve a prompt by its primary name or any alias.

        Uses DuckDB's list_contains for alias lookup, safely handling NULLs.
        """
        cur = self.conn.execute(
            (
                """
                SELECT * FROM prompt_specs
                WHERE name = $name
                   OR coalesce(list_contains(aliases, $name), FALSE)
                LIMIT 1;
                """
            ),
            {"name": name_or_alias},
        )
        res = cur.fetchone()
        if res is None:
            return None
        col_names = [d[0] for d in cur.description]
        return PromptSpec.from_row({k: v for k, v in zip(col_names, res)})

    def list(self, enabled: Optional[bool] = None) -> List[PromptSpec]:
        if enabled is None:
            cur = self.conn.execute("SELECT * FROM prompt_specs ORDER BY name;")
        else:
            cur = self.conn.execute(
                "SELECT * FROM prompt_specs WHERE enabled = $enabled ORDER BY name;",
                {"enabled": enabled},
            )
        col_names = [d[0] for d in cur.description]
        return [PromptSpec.from_row({k: v for k, v in zip(col_names, row)}) for row in cur.fetchall()]

    def _next_version_seq(self, name: str) -> int:
        cur = self.conn.execute(
            "SELECT COALESCE(MAX(version_seq), 0) + 1 FROM prompt_spec_versions WHERE name = $name;",
            {"name": name},
        )
        seq = cur.fetchone()[0]
        try:
            return int(seq)
        except Exception:
            return 1

    def _insert_version_row(self, name: str, action: str) -> None:
        version_seq = self._next_version_seq(name)
        logger.info(
            "Recording prompt spec version: name=%s seq=%s action=%s", name, version_seq, action
        )
        self.conn.execute(
            """
            INSERT INTO prompt_spec_versions (
                name, version_seq, action,
                description, provider, model, web_search, reasoning_effort, context_size,
                temperature, max_output_tokens, system_instruction, use_cases, parameters, tags,
                version, enabled, aliases, source, checksum, token_limits, notes,
                created_at, updated_at, occurred_at
            )
            SELECT
                name, $version_seq AS version_seq, $action AS action,
                description, provider, model, web_search, reasoning_effort, context_size,
                temperature, max_output_tokens, system_instruction, use_cases, parameters, tags,
                version, enabled, aliases, source, checksum, token_limits, notes,
                created_at, updated_at, current_timestamp AS occurred_at
            FROM prompt_specs
            WHERE name = $name;
            """,
            {"name": name, "version_seq": version_seq, "action": action},
        )

    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        provider: Optional[str] = None,
        limit: int = 50,
    ) -> List[PromptSpec]:
        conditions: List[str] = []
        params: Dict[str, Any] = {}
        if query:
            conditions.append(
                "(lower(name) LIKE lower($q) OR lower(description) LIKE lower($q) OR lower(system_instruction) LIKE lower($q))"
            )
            params["q"] = f"%{query}%"
        if provider:
            conditions.append("provider = $provider")
            params["provider"] = provider
        if tags:
            for i, tag in enumerate(tags):
                conditions.append(f"list_contains(tags, $tag_{i})")
                params[f"tag_{i}"] = tag
        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        cur = self.conn.execute(
            f"SELECT * FROM prompt_specs{where_clause} ORDER BY updated_at DESC LIMIT $limit;",
            {**params, "limit": limit},
        )
        col_names = [d[0] for d in cur.description]
        return [PromptSpec.from_row({k: v for k, v in zip(col_names, row)}) for row in cur.fetchall()]
