"""UUID v7 generation (ADR-0006)."""

from __future__ import annotations

import time

from app.core.ids import uuid7, uuid7_timestamp_ms


def test_uuid7_has_version_and_variant_bits() -> None:
    value = uuid7()
    assert value.version == 7
    # RFC 9562 variant: the two most significant bits of the clock-seq byte are 0b10.
    assert (value.int >> 62) & 0b11 == 0b10


def test_uuid7_embeds_current_time() -> None:
    before = time.time_ns() // 1_000_000
    value = uuid7()
    after = time.time_ns() // 1_000_000
    assert before <= uuid7_timestamp_ms(value) <= after


def test_uuid7_is_monotonic_within_the_same_millisecond() -> None:
    # String ordering must match generation order: cursor pagination sorts on the id.
    values = [str(uuid7()) for _ in range(500)]
    assert values == sorted(values)
    assert len(set(values)) == len(values)
