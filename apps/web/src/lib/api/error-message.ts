import { ApiRequestError } from "@/features/auth/api";

type ErrorsTranslator = {
  (key: string): string;
  has: (key: string) => boolean;
};

/** Map API Problem Details codes to localized copy. Never show raw English API text. */
export function apiErrorMessage(error: unknown, t: ErrorsTranslator): string {
  if (!(error instanceof ApiRequestError)) {
    return t("generic");
  }

  const code = error.problem.code;
  if (code && t.has(code)) {
    return t(code);
  }

  const fieldCode = error.problem.errors?.[0]?.code;
  if (fieldCode) {
    const fieldKey = `fields.${fieldCode}`;
    if (t.has(fieldKey)) {
      return t(fieldKey);
    }
  }

  if (error.problem.status === 400 || error.problem.status === 422) {
    return t("VALIDATION_ERROR");
  }

  return t("generic");
}
