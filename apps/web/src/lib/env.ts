/**
 * Validated environment (MEP §59). Importing this module fails the build/boot when a required
 * variable is missing or malformed, instead of failing later at request time.
 */
import { z } from "zod";

const serverSchema = z.object({
  API_INTERNAL_URL: z.url(),
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});

const clientSchema = z.object({
  NEXT_PUBLIC_API_URL: z.url(),
  NEXT_PUBLIC_SITE_URL: z.url(),
});

// NEXT_PUBLIC_* must be referenced literally so Next.js inlines them for the browser bundle.
const clientValues = {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
};

function parse<T extends z.ZodType>(schema: T, values: unknown, scope: string): z.output<T> {
  const result = schema.safeParse(values);
  if (!result.success) {
    const details = result.error.issues
      .map((issue) => `  ${issue.path.join(".")}: ${issue.message}`)
      .join("\n");
    throw new Error(`Invalid ${scope} environment variables:\n${details}`);
  }
  return result.data;
}

export const clientEnv = parse(clientSchema, clientValues, "client");

const isServer = typeof window === "undefined";
export const serverEnv = isServer
  ? parse(
      serverSchema,
      { API_INTERNAL_URL: process.env.API_INTERNAL_URL, NODE_ENV: process.env.NODE_ENV },
      "server",
    )
  : undefined;
