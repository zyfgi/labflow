"""Start (or reuse) a local embedded PostgreSQL for development.

Usage: python scripts/dev_pg.py [pgdata_dir]
Prints the SQLAlchemy connection URI. The server keeps running after exit.
"""
import os
import sys

import pgserver


def main() -> None:
    pgdata = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", ".local_pgdata")
    pgdata = os.path.abspath(pgdata)
    server = pgserver.get_server(pgdata, cleanup_mode=None)
    print(server.get_uri())


if __name__ == "__main__":
    main()
