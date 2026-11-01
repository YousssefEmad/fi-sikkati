"""Export the OpenAPI document to a file (used to generate the TypeScript client, ADR-0009).

Usage: ``uv run python scripts/export_openapi.py ../../packages/types/openapi.json``
The file is written deterministically (sorted keys, stable indentation) so diffs are reviewable.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_EXPORT_ENV = {
    "APP_ENV": "development",
    "DATABASE_URL": "postgresql+asyncpg://export:export@localhost:5432/export",
    "REDIS_URL": "redis://localhost:6379/0",
    "PUBLIC_WEB_URL": "http://localhost:3000",
    "AUTH_JWT_ACTIVE_KID": "export-1",
    "AUTH_JWT_PRIVATE_KEY": "ZXhwb3J0LWVkMjU1MTktc2VlZC0zMi1ieXRlcSE=",
    "AUTH_PASSWORD_PEPPER": "export-pepper-" + "p" * 24,
    "AUTH_CSRF_SECRET": "export-csrf-" + "c" * 24,
    "AUTH_HASH_SECRET": "export-hash-" + "h" * 24,
    "EMAIL_FROM_ADDRESS": "no-reply@fisikkati.app",
    "SMTP_HOST": "127.0.0.1",
}


_EXPECTED_ARGC = 2


def main(argv: list[str]) -> int:
    if len(argv) != _EXPECTED_ARGC:
        sys.stderr.write("usage: export_openapi.py <output-path>\n")
        return 2
    # Schema generation needs a Settings instance but never connects anywhere.
    for key, value in _EXPORT_ENV.items():
        os.environ.setdefault(key, value)

    # Imported after the environment is prepared: Settings reads env on import of the app.
    from app.core.config import Settings  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    app = create_app(Settings(_env_file=None))
    document = app.openapi()
    output = Path(argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(f"wrote {output} ({len(document.get('paths', {}))} paths)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
