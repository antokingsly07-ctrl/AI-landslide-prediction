"""Generate the full-schema Alembic migration for existing tables.

Run after installing backend deps (with DATABASE_URL pointing at the target DB):

    python scripts/make_migration.py -m "initial schema"

This autogenerates a single migration reflecting every model. The repo ships
with 0001 (system_config) only; regenerate this as the authoritative schema.
"""
import argparse
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    parser = argparse.ArgumentParser(description="Autogenerate Alembic migration")
    parser.add_argument("-m", "--message", default="initial schema")
    args = parser.parse_args()

    if "--needs-install" in sys.argv:
        print("This script must be run from an environment with backend/ deps installed.")

    cmd = [sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", args.message]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=REPO, check=True)


if __name__ == "__main__":
    main()