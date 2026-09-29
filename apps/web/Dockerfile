# syntax=docker/dockerfile:1.7
# Build context is the repository root (pnpm workspace). See deployment.md §3.
ARG NODE_VERSION=24

FROM node:${NODE_VERSION}-alpine AS base
RUN corepack enable && corepack prepare pnpm@12.6.0 --activate
WORKDIR /repo

# ---------------------------------------------------------------------------
# deps: install workspace dependencies with the lockfile
# ---------------------------------------------------------------------------
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY packages/config/package.json packages/config/
COPY packages/types/package.json packages/types/
COPY apps/web/package.json apps/web/
COPY tests/e2e/package.json tests/e2e/
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile --filter @fi-sikkati/web...

# ---------------------------------------------------------------------------
# dev: hot reload; source is bind-mounted by compose
# ---------------------------------------------------------------------------
FROM deps AS dev
COPY packages ./packages
COPY apps/web ./apps/web
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_SITE_URL=http://localhost:3000
WORKDIR /repo/apps/web
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0"]

# ---------------------------------------------------------------------------
# builder: production build (standalone output)
# ---------------------------------------------------------------------------
FROM deps AS builder
COPY packages ./packages
COPY apps/web ./apps/web
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL} \
    API_INTERNAL_URL=http://api:8000
WORKDIR /repo/apps/web
RUN pnpm build

# ---------------------------------------------------------------------------
# runtime: minimal standalone server, non-root
# ---------------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
RUN addgroup --system --gid 1001 app && adduser --system --uid 1001 --ingroup app app
WORKDIR /app
COPY --from=builder --chown=app:app /repo/apps/web/.next/standalone ./
COPY --from=builder --chown=app:app /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=app:app /repo/apps/web/public ./apps/web/public
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD wget -qO- http://localhost:3000/ar >/dev/null || exit 1
CMD ["node", "apps/web/server.js"]
