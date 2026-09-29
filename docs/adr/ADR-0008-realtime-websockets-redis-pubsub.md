# ADR-0008 — Real-time via FastAPI WebSockets + Redis Pub/Sub, persist-then-publish

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §35 allows real-time only for chat, trip updates, notifications and seat availability, and
requires Redis-backed coordination when needed. The API runs multiple stateless replicas.

## Decision

A single WebSocket endpoint `/ws` in the API, authenticated with the access token at connect.
Clients subscribe to authorised channels (`user:{id}`, `conversation:{id}`, `trip:{id}`);
membership is verified per subscription. Writes always go through HTTP (`POST …/messages`),
are persisted in PostgreSQL, and only then published to Redis Pub/Sub; every API replica
forwards to its local sockets. Clients reconnect with the last seen message id and catch up over
HTTP, so Pub/Sub at-most-once delivery is acceptable.

## Alternatives

- Server-Sent Events: simpler but one-directional and awkward for chat typing/read receipts;
  may be added for notification-only pages.
- Redis Streams for durability: unnecessary because PostgreSQL is the durable log.
- Third-party realtime (Pusher, Ably): vendor, cost; not approved.

## Consequences

- No sticky sessions needed.
- Real-time is an accelerator, never the source of truth; the UI must work with HTTP alone.
