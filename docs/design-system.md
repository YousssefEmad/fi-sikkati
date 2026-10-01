# Design System

Fi Sikkati has its own visual identity (MEP §49) derived from the brand logo. This document is
the reference for tokens, components and the accessibility rules every screen must satisfy.
Implementation lives in `apps/web/src/app/globals.css` (tokens) and `apps/web/src/components`.

## 1. Brand

| Asset | Path | Use |
| --- | --- | --- |
| Logo (disc on white) | `apps/web/public/brand/logo.png` | documents, light backgrounds |
| Logo (full-bleed square) | `apps/web/public/brand/logo-square.png` | app lockup, avatars, favicons |
| App icons | `apps/web/public/icons/icon-{192,512}.png` | web manifest (`any` + `maskable`) |
| Apple touch icon | `apps/web/src/app/apple-icon.png` | iOS home screen |
| Favicon | `apps/web/src/app/favicon.ico` | browser tab |
| Open Graph card | `apps/web/public/brand/og.png` | link previews |

All icon assets are generated from the single source logo, so re-exporting the logo is the only
step needed when the artwork is refreshed.

## 2. Colour

| Token | Value | Role |
| --- | --- | --- |
| `--color-brand` | `#CCF618` → `oklch(91.1% 0.216 121.5)` | the logo lime: identity, highlights, accent surfaces |
| `--color-brand-strong` | `oklch(72% 0.19 124)` | lime that still reads on white (icons, hover) |
| `--color-brand-soft` | `oklch(96% 0.09 122)` | hero wash, tints |
| `--color-brand-foreground` | ink | the only text colour allowed on lime |
| `--color-foreground` / `--color-primary` | `oklch(21% 0.012 125)` | body text and primary actions |
| `--color-inverse` | `oklch(19% 0.012 125)` | dark bands and footer |
| `--color-surface-muted` / `--color-surface-sunken` | near-white greens | section separation |
| `--color-success` / `--color-danger` | green / red | state only, never decoration |

**Rule:** lime is a *light* colour. White text on lime fails contrast, so lime is never a
background for white text; primary buttons are ink (`--color-primary`) and lime is used for
accent surfaces with ink text, icons, and badges. Page rhythm alternates
light → ink → white → mist → lime → ink(footer) so the brand colour lands as a highlight rather
than a wash.

## 3. Typography

| Locale | Stack | Source |
| --- | --- | --- |
| Arabic (default) | Cairo → Noto Sans Arabic → system | `next/font/google`, `--font-cairo` |
| English | Plus Jakarta Sans → Cairo → system | `next/font/google`, `--font-jakarta` |

`<body>` receives `font-arabic` or `font-latin` based on the active locale. Headings are
`font-extrabold` with tight tracking; body copy is `leading-relaxed`. `text-wrap: balance` on
headings and `pretty` on body text keep Arabic line breaks readable.

## 4. Shape, elevation, motion

- Radii: `sm 8px`, `md 14px`, `lg 20px`, `xl 28px`; buttons and badges are fully rounded (pills).
- Elevation: `shadow-card` for resting surfaces, `shadow-lift` for the hero/featured card. No
  more than two elevation levels on a screen.
- Motion: colour/shadow transitions only, plus a 1px press translation. Everything is disabled
  under `prefers-reduced-motion`.

## 5. Components (current)

| Component | File | Notes |
| --- | --- | --- |
| `Button` | `components/ui/button.tsx` | variants `primary`, `brand`, `outline`, `ghost`, `inverse`; sizes `sm/md/lg`; `block`; min height 44px; `type="button"` by default |
| `Badge` | `components/ui/badge.tsx` | variants `brand`, `soft`, `outline`, `inverse` |
| `Card` | `components/ui/card.tsx` | bordered surface with `shadow-card` |
| `Logo` | `components/brand/logo.tsx` | mark + live-text wordmark, `default`/`inverse` tone |
| `SiteHeader` / `SiteFooter` | `components/layout/*` | sticky blurred header; dark footer with status |
| `LanguageSwitcher` | `components/layout/language-switcher.tsx` | native `<select>`, labelled, works in both tones |

Product components (trip cards, search, chat) arrive with their phases; the hero on the landing
page contains a **static design preview** of a trip card, explicitly labelled as such so it is
never mistaken for working functionality.

## 6. Accessibility rules (NFR-01…NFR-03)

- Every interactive element: ≥ 44px hit target, visible `:focus-visible` ring with offset.
- Text contrast ≥ 4.5:1 (≥ 3:1 for ≥ 24px). Verified by `@axe-core/playwright` on every public
  page in both locales, desktop and mobile viewports; serious/critical violations fail CI.
- Icons are `aria-hidden`; meaning is always carried by text. Decorative images use `alt=""`.
- Direction comes from `dir` on `<html>`; layout uses logical properties (`ms-*`, `pe-*`,
  `start-*`) so RTL and LTR share one implementation.
- All user-facing strings come from `messages/{ar,en}.json` (enforced by `react/jsx-no-literals`
  and a message-parity test).

## 7. Open items

- Branded illustrations and a map style matching the palette: Phase 11 (map provider is OD-005).
- Dark mode: not planned for the MVP; tokens are structured so it can be added later.
- Logo wordmark vs product name: see OD-031 in `open-decisions.md`.
