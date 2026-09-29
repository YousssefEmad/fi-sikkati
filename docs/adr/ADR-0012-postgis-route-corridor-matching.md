# ADR-0012 — Geographic matching with PostGIS route corridors

**Status**: Accepted · **Date**: 2026-09-29

## Context

MEP §13–§15 require geometry-based route compatibility (not name matching, not naive lat/lon
maths), PostGIS, configurable thresholds, and a distinction between exact match and on-route
compatibility. Initial search must use PostgreSQL only (§34).

## Decision

- Each published trip stores its route `LineString` (from the map provider) and a precomputed
  **corridor** polygon = `ST_Buffer(route::geography, matching.corridor_width_meters)`, indexed
  with GiST.
- A passenger's pickup and drop-off are compatible when both are covered by the corridor and
  `ST_LineLocatePoint(route, pickup) < ST_LineLocatePoint(route, dropoff)`.
- Exact match when both points are within `matching.stop_proximity_meters` of trip stops in
  order.
- Distances use `geography` (metres); ranking per BR-MATCH-06.
- Thresholds are configuration (values pending OD-006); changing corridor width triggers a
  re-buffer job.

## Alternatives

- Name/area matching: explicitly forbidden (BR-MATCH-04).
- Compute detours via routing API per candidate: accurate but expensive; deferred until OD-006
  approves detours.
- H3/geohash bucketing: useful later as a pre-filter; unnecessary at this scale.

## Consequences

- Search is one indexed SQL query (`database.md` §4).
- Corridor storage adds a few KB per trip; acceptable.
