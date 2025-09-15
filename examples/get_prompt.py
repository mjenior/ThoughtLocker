import argparse
import json
import logging

from thoughtlocker.db import get_connection, ensure_schema
from thoughtlocker.repository import PromptRepository


def main():
    parser = argparse.ArgumentParser(description="Retrieve a prompt spec by name")
    parser.add_argument("--db", required=True, help="Absolute path to DuckDB database file")
    parser.add_argument("--name", required=True, help="Prompt name to retrieve")
    parser.add_argument("--json", action="store_true", help="Print full JSON instead of instruction text")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    conn = get_connection(args.db)
    ensure_schema(conn)
    repo = PromptRepository(conn)
    spec = repo.get_by_name(args.name)
    if spec is None:
        raise SystemExit(f"Prompt '{args.name}' not found")

    if args.json:
        print(json.dumps(spec.__dict__, default=str, ensure_ascii=False, indent=2))
    else:
        print(spec.system_instruction)


if __name__ == "__main__":
    main()
