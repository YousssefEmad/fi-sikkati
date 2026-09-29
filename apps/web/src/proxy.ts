import createMiddleware from "next-intl/middleware";

import { routing } from "@/i18n/routing";

/** Locale negotiation and `/ar` / `/en` prefix handling for every page route. */
export default createMiddleware(routing);

export const config = {
  // Skip Next internals, static files and API-style routes.
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
