# ADR-0001 — Modular monolith over microservices

**Status**: Accepted · **Date**: 2026-09-29

## Context

The initial community is ~2,000 users. The master prompt (§6, §65, §99) mandates a modular
monolith with clear domain boundaries and forbids premature microservices, brokers and
Kubernetes. The team needs to ship 12 phases with a small engineering footprint while keeping the
door open to extraction if scale demands.

## Decision

One FastAPI application organised into domain modules (`architecture.md` §2.1), each with its
own router/service/repository/models, communicating only via public service functions or
in-process post-commit domain events. One PostgreSQL database with module-owned tables. The
same codebase runs as `api` and `worker` processes. Module boundaries are enforced by
`import-linter` contracts in CI.

## Alternatives

- Microservices per domain: operational cost, distributed transactions for seat allocation,
  no benefit at this scale.
- Single unstructured monolith: fast initially, decays into the "giant files" the prompt forbids.
- Event-driven with a broker (Kafka/RabbitMQ): unnecessary; Redis + idempotent jobs suffice.

## Consequences

- Seat allocation stays a single ACID transaction.
- Extraction path: a module can become a service by replacing its in-process service interface
  with an HTTP/queue adapter; tables move with the module.
- Discipline required: cross-module table access is a CI failure.
