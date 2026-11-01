"""Append-only audit log (security.md §9).

Entries are written in the same transaction as the change they describe, so the log can never
diverge from the data. The application database role holds only ``INSERT, SELECT`` on
``audit_logs`` (database.md §8) — nothing in the codebase can update or delete an entry.
"""
