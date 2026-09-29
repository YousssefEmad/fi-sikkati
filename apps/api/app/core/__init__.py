"""Cross-cutting infrastructure: configuration, logging, errors, database, redis, middleware.

Nothing in ``app.core`` may import from ``app.modules`` (enforced by import-linter, ADR-0001).
"""
