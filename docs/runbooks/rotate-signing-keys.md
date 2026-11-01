# Runbook — Rotate JWT signing keys

Status: **DONE** (Phase 2). Access tokens are Ed25519 JWTs with a `kid` (ADR-0004, security.md §1).

## Preconditions

- You can change API environment variables and restart the API process.
- Tokens issued with the old key must keep verifying until they expire (15 minutes).

## Steps

1. Generate a new 32-byte seed and a new key id (≤ 32 characters):

   ```
   python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
   ```

2. Derive the **public** key of the key you are retiring (32-byte raw public key, base64). The
   API process currently holding `AUTH_JWT_PRIVATE_KEY` can print it; do not log the private seed.

3. Set, atomically on restart:

   | Variable | Value |
   | --- | --- |
   | `AUTH_JWT_ACTIVE_KID` | the new kid |
   | `AUTH_JWT_PRIVATE_KEY` | base64 of the new 32-byte seed |
   | `AUTH_JWT_RETIRED_PUBLIC_KEYS` | `oldKid:base64publickey` (comma-separated if several) |

4. Restart the API. New access tokens use the new kid; refresh still rotates sessions as before.

## Verification

- `GET /health/ready` is `200`.
- Sign in; the access cookie is accepted on `GET /me`.
- A token signed with the old kid still verifies until `exp`.

## Rollback

Restore the previous three variables and restart. Do not delete a retired public key until every
access token signed with it has expired.
