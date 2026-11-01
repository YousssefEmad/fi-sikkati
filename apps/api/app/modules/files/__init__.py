"""Private and public object storage (ADR-0013, security.md §3).

Owns ``stored_files``. Other modules call :class:`FileService` and receive dataclasses — the
ORM model never leaves this package.
"""
