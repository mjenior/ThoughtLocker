import os
import logging
from contextlib import contextmanager
import duckdb

logger = logging.getLogger(__name__)


def get_connection(db_path: str = "prompts.duckdb") -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection to the specified database path.

    Ensures that the parent directory exists and configures sensible pragmas.
    """
    abs_path = os.path.abspath(db_path)
    parent_dir = os.path.dirname(abs_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    conn = duckdb.connect(abs_path)
    conn.execute("PRAGMA threads=4;")
    conn.execute("PRAGMA enable_progress_bar=false;")
    return conn


def ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables and indices if they don't exist."""
    logger.debug("Ensuring DuckDB schema for prompt specs")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_specs (
            name TEXT PRIMARY KEY,
            description TEXT,
            provider TEXT,
            model TEXT,
            web_search BOOLEAN,
            reasoning_effort TEXT,
            context_size TEXT,
            temperature DOUBLE,
            max_output_tokens INTEGER,
            system_instruction TEXT,
            use_cases VARCHAR[],
            parameters JSON,
            tags VARCHAR[],
            version TEXT,
            enabled BOOLEAN DEFAULT TRUE,
            aliases VARCHAR[],
            source TEXT,
            checksum TEXT,
            token_limits JSON,
            notes TEXT,
            created_at TIMESTAMP DEFAULT current_timestamp,
            updated_at TIMESTAMP DEFAULT current_timestamp
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_specs_provider ON prompt_specs(provider);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_specs_model ON prompt_specs(model);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_specs_enabled ON prompt_specs(enabled);")

    # Append-only version history table for prompt specs
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prompt_spec_versions (
            name TEXT,
            version_seq INTEGER,
            action TEXT, -- 'insert' or 'update'
            description TEXT,
            provider TEXT,
            model TEXT,
            web_search BOOLEAN,
            reasoning_effort TEXT,
            context_size TEXT,
            temperature DOUBLE,
            max_output_tokens INTEGER,
            system_instruction TEXT,
            use_cases VARCHAR[],
            parameters JSON,
            tags VARCHAR[],
            version TEXT,
            enabled BOOLEAN,
            aliases VARCHAR[],
            source TEXT,
            checksum TEXT,
            token_limits JSON,
            notes TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            occurred_at TIMESTAMP DEFAULT current_timestamp,
            PRIMARY KEY (name, version_seq)
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_psv_name ON prompt_spec_versions(name);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_psv_name_updated ON prompt_spec_versions(name, updated_at);")


@contextmanager
def transaction(conn: duckdb.DuckDBPyConnection):
    """Simple transaction context manager."""
    try:
        conn.execute("BEGIN TRANSACTION;")
        yield
        conn.execute("COMMIT;")
    except Exception as exc:
        logger.exception("Transaction failed, rolling back: %s", exc)
        conn.execute("ROLLBACK;")
        raise


