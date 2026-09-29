-- Local development bootstrap (runs once on an empty data volume).
-- Creates the three database roles from docs/database.md §8 and the dev/test databases.
-- Passwords here are DEVELOPMENT ONLY and match apps/api/.env.example. Production roles are
-- provisioned by the hosting platform with secrets from its secret store.

CREATE ROLE fisikkati_migrator LOGIN PASSWORD 'fisikkati_migrator_dev';
CREATE ROLE fisikkati_app       LOGIN PASSWORD 'fisikkati_app_dev';
CREATE ROLE fisikkati_readonly  LOGIN PASSWORD 'fisikkati_readonly_dev';

CREATE DATABASE fisikkati      OWNER fisikkati_migrator;
CREATE DATABASE fisikkati_test OWNER fisikkati_migrator;

\connect fisikkati
\include /docker-entrypoint-initdb.d/grants.psql

\connect fisikkati_test
\include /docker-entrypoint-initdb.d/grants.psql
