#!/usr/bin/env node
/**
 * One-shot local development setup (idempotent). Run with `pnpm setup` from the repo root.
 *
 *  1. Verifies required tooling (node, pnpm, uv, docker).
 *  2. Copies every `.env.example` to its local counterpart when missing (never overwrites).
 *  3. Generates the local development secrets that `.env.example` deliberately leaves empty.
 *  4. Starts the infrastructure containers (PostgreSQL/PostGIS, Redis, MinIO, Mailpit).
 *  5. Installs API dependencies and applies migrations.
 *  6. Installs web dependencies and regenerates the typed API client.
 *
 * It never overwrites an existing value and never runs against a non-development environment.
 */
import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { copyFileSync, existsSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const isWindows = process.platform === "win32";

const ENV_FILES = [
  ["apps/api/.env.example", "apps/api/.env"],
  ["apps/web/.env.example", "apps/web/.env.local"],
  ["infra/compose/.env.example", "infra/compose/.env"],
];

function log(message) {
  console.log(`\u25B8 ${message}`);
}

function run(command, args, options = {}) {
  const display = [command, ...args].join(" ");
  log(display);
  const result = spawnSync(command, args, {
    cwd: options.cwd ? resolve(ROOT, options.cwd) : ROOT,
    stdio: "inherit",
    shell: isWindows,
    env: { ...process.env, ...(options.env ?? {}) },
  });
  if (result.status !== 0) {
    console.error(`\nCommand failed (${result.status ?? "signal"}): ${display}`);
    process.exit(result.status ?? 1);
  }
}

function has(command, args = ["--version"]) {
  const result = spawnSync(command, args, { stdio: "ignore", shell: isWindows });
  return result.status === 0;
}

function readEnv(file) {
  if (!existsSync(file)) return {};
  return Object.fromEntries(
    readFileSync(file, "utf8")
      .split(/\r?\n/)
      .filter((line) => line && !line.startsWith("#") && line.includes("="))
      .map((line) => {
        const index = line.indexOf("=");
        const key = line.slice(0, index).trim();
        let value = line.slice(index + 1).trim();
        // Inline comments in .env.example must not become part of the value.
        if (!value.startsWith('"') && !value.startsWith("'") && value.includes(" #")) {
          value = value.slice(0, value.indexOf(" #")).trim();
        }
        return [key, value];
      }),
  );
}

// 1. Tooling -----------------------------------------------------------------------------------
const missing = [];
if (!has("pnpm")) missing.push("pnpm (npm install -g pnpm)");
if (!has("docker", ["version"])) missing.push("docker (Docker Desktop / Engine, running)");
const uvCommand = has("uv")
  ? ["uv"]
  : has("python", ["-m", "uv", "--version"])
    ? ["python", "-m", "uv"]
    : null;
if (!uvCommand)
  missing.push("uv (https://docs.astral.sh/uv/ or `python -m pip install --user uv`)");
if (missing.length > 0) {
  console.error("Missing required tools:\n  - " + missing.join("\n  - "));
  process.exit(1);
}

// 2. Environment files -------------------------------------------------------------------------
for (const [example, target] of ENV_FILES) {
  const targetPath = resolve(ROOT, target);
  if (existsSync(targetPath)) {
    log(`${target} exists — left untouched`);
  } else {
    copyFileSync(resolve(ROOT, example), targetPath);
    log(`created ${target} from ${example}`);
  }
}

const apiEnvPath = resolve(ROOT, "apps/api/.env");
const apiEnv = readEnv(apiEnvPath);
if (apiEnv.APP_ENV && apiEnv.APP_ENV !== "development") {
  console.error(
    `apps/api/.env has APP_ENV=${apiEnv.APP_ENV}; dev setup only runs for development.`,
  );
  process.exit(1);
}

// 3. Local secrets -----------------------------------------------------------------------------
// `.env.example` ships these keys empty on purpose: a committed signing key or pepper would be a
// real secret in version control, even if it is "only for development".
const GENERATED_SECRETS = {
  // 32-byte Ed25519 seed for signing access tokens.
  AUTH_JWT_PRIVATE_KEY: () => randomBytes(32).toString("base64"),
  AUTH_PASSWORD_PEPPER: () => randomBytes(32).toString("base64"),
  AUTH_CSRF_SECRET: () => randomBytes(32).toString("base64"),
  AUTH_HASH_SECRET: () => randomBytes(32).toString("base64"),
};

function fillEmptySecrets(path) {
  if (!existsSync(path)) return;
  const original = readFileSync(path, "utf8");
  let updated = original;
  const filled = [];
  for (const [key, generate] of Object.entries(GENERATED_SECRETS)) {
    const pattern = new RegExp(`^${key}=[ \\t]*$`, "m");
    if (pattern.test(updated)) {
      updated = updated.replace(pattern, `${key}=${generate()}`);
      filled.push(key);
    }
  }
  if (filled.length > 0) {
    writeFileSync(path, updated);
    log(`generated local values for ${filled.join(", ")}`);
  }
}

fillEmptySecrets(apiEnvPath);

// 4. Infrastructure ----------------------------------------------------------------------------
run("docker", ["compose", "-f", "infra/compose/docker-compose.yml", "up", "-d", "--wait"]);

// 5. API ---------------------------------------------------------------------------------------
const [uvBin, ...uvPrefix] = uvCommand;
run(uvBin, [...uvPrefix, "sync", "--frozen"], { cwd: "apps/api" });
run(uvBin, [...uvPrefix, "run", "alembic", "upgrade", "head"], { cwd: "apps/api" });

// 6. Web ---------------------------------------------------------------------------------------
run("pnpm", ["install", "--frozen-lockfile"]);
run("pnpm", ["types:generate"]);

log("Done. Next:");
log("  API : cd apps/api && uv run uvicorn app.main:create_app --factory --reload --port 8000");
log("  Web : pnpm dev   (http://localhost:3000)");
log("  Docs: docs/runbooks/local-development.md");
