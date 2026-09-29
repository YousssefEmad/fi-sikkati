# ADR-0013 — Private document storage with short-lived signed URLs

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §9, §38, §74 require identity/vehicle documents to be private, access-controlled,
audited, encrypted where supported, never in PostgreSQL, never via raw storage URLs.

## Decision

S3-compatible object storage (MinIO locally) with two buckets: `public-media` and
`private-documents` (block public access, SSE). The `files` module owns an `ObjectStorage`
protocol; documents are uploaded through the API (multipart), validated (size, extension,
sniffed MIME, image re-encode, PDF active-content check, AV scan where available) and stored
under generated keys. Access to private documents is only via presigned GET URLs with 120 s
TTL, issued exclusively to `ADMIN` through an audited endpoint. Retention is enforced by a purge
job using `stored_files.purge_after`.

## Alternatives

- Direct browser→S3 presigned PUT: fewer API bytes but validation happens after upload; MVP
  volume does not justify it. May adopt with post-upload validation later.
- Storing files in PostgreSQL `bytea`: forbidden (MEP §38).
- Streaming documents through the API instead of presigned URLs: simpler audit but ties API
  bandwidth; presigned with 120 s TTL + audit at issuance is the conventional choice.

## Consequences

- Users cannot re-download their own documents (metadata only) — reduces exposure surface.
- Requires same validation pipeline for profile photos (public bucket).
