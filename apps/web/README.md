# Fi Sikkati Web

Next.js App Router application (passenger, driver and admin experiences). See
[`../../docs/architecture.md`](../../docs/architecture.md) §4.

```powershell
pnpm install                      # from the repository root
Copy-Item .env.example .env.local # then adjust if needed
pnpm dev                          # http://localhost:3000 → redirects to /ar
pnpm lint ; pnpm typecheck ; pnpm test ; pnpm build
```

- Routes live under `src/app/[locale]/…`; `ar` is the default locale and renders RTL.
- User-facing strings live in `messages/{ar,en}.json` only (lint warns on literals in JSX).
- API calls go through the generated client in `@fi-sikkati/types`; never hand-write API types.
