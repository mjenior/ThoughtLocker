# Thought Locker

Version: 0.1.0

A DuckDB-backed storage and retrieval for system instruction prompts. Provides an importable module API for multi-agent systems, plus a YAML seeding CLI and a simple retrieval example.

## Features
- Required fields supported: `description`, `provider`, `model`, `web_search`, `reasoning_effort`, `context_size`, `temperature`, `max_output_tokens`, `system_instruction`.
- Useful optional metadata: `use_cases`, `parameters`, `tags`, `version`, `aliases`, `source`, `checksum`, `token_limits`, `notes`.
- Repository API: upsert, get by name, list, search by text/tags/provider.
 - Version history: every upsert snapshots the "after" state into an append-only `prompt_spec_versions` table with a per-name `version_seq`, `action`, and `occurred_at` timestamp.

## Setup (uv)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv
. .venv/bin/activate
uv pip install -e .
```

## Importable usage
```python
from thoughtlocker import Locker

# Create or open the DuckDB at a path of your choice
locker = Locker(db_path="/Users/you/prompts.duckdb")

# Seed from YAML
locker.seed_from_yaml("prompts.yaml")

# Retrieve by name or alias
instruction = locker.get_system_instruction("summarize_for_prompt")
print(instruction)

# Search and list
specs = locker.search(query="summarize", tags=["summarization"])  # returns List[PromptSpec]
for spec in specs:
    print(spec.name, spec.model)

# Context-manager friendly
with Locker(db_path="/Users/you/prompts.duckdb") as s:
    print(s.get("summarize_for_prompt").system_instruction)
```

## Seed from YAML
```bash
python scripts/seed_prompts.py --db "$HOME/prompts.duckdb" --yaml prompts.yaml
```

## Retrieve a prompt (CLI)
```bash
python examples/get_prompt.py --db "$HOME/prompts.duckdb" --name summarize_for_prompt
```

Or the full JSON:
```bash
python examples/get_prompt.py --db "$HOME/prompts.duckdb" --name summarize_for_prompt --json
```

## Version history
The store maintains an append-only audit log for each prompt in `prompt_spec_versions`. A new row is recorded inside the same transaction after every insert or update of `prompt_specs`.

- `version_seq` is a monotonically increasing integer per `name`.
- `action` is `insert` or `update`.
- Snapshots capture the stored values (including `created_at` and `updated_at`) at the moment after the change.

### List versions for a prompt
```sql
-- Parameters: $name
SELECT version_seq,
       action,
       updated_at,
       occurred_at,
       model,
       version,
       checksum
FROM prompt_spec_versions
WHERE name = $name
ORDER BY version_seq;
```

### Inspect a specific historical version
```sql
-- Parameters: $name, $version_seq
SELECT *
FROM prompt_spec_versions
WHERE name = $name AND version_seq = $version_seq;
```

### Restore `prompt_specs` to a historical version
This promotes a historical snapshot back into `prompt_specs` for a given `name`, updating all mutable fields and refreshing `updated_at`.

```sql
-- Parameters: $name, $version_seq
WITH h AS (
  SELECT * FROM prompt_spec_versions WHERE name = $name AND version_seq = $version_seq
)
UPDATE prompt_specs AS p
SET
  description = h.description,
  provider = h.provider,
  model = h.model,
  web_search = h.web_search,
  reasoning_effort = h.reasoning_effort,
  context_size = h.context_size,
  temperature = h.temperature,
  max_output_tokens = h.max_output_tokens,
  system_instruction = h.system_instruction,
  use_cases = h.use_cases,
  parameters = h.parameters,
  tags = h.tags,
  version = h.version,
  enabled = h.enabled,
  aliases = h.aliases,
  source = h.source,
  checksum = h.checksum,
  token_limits = h.token_limits,
  notes = h.notes,
  updated_at = current_timestamp
FROM h
WHERE p.name = h.name;
```

Note: Restoring will itself create a new snapshot (action `update`) capturing the restored state.

## Security & Validation
- YAML loader validates required fields and computes a checksum over those fields. Upserts occur only if checksum changes, avoiding unnecessary writes.
- JSON fields are serialized safely; parsing is tolerant to pre-parsed values.

## Notes
- Schema is created automatically if missing.
- Adjust DuckDB pragmas in `thoughtlocker/db.py` if needed for performance.
