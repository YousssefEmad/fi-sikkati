/** Shared account-form checks. Server-side rules in the API remain authoritative. */

function isoDate(year: number, monthIndex: number, day: number): string {
  const month = String(monthIndex + 1).padStart(2, "0");
  const date = String(day).padStart(2, "0");
  return `${year}-${month}-${date}`;
}

export function adultCutoffDate(minAge: number, now = new Date()): string {
  const cutoff = new Date(now.getFullYear() - minAge, now.getMonth(), now.getDate());
  return isoDate(cutoff.getFullYear(), cutoff.getMonth(), cutoff.getDate());
}

const E164 = /^\+[1-9][0-9]{7,14}$/;
const MOBILE = /^(01[0125]\d{8}|\+[1-9]\d{7,14})$/;

export function isMobileNumber(value: string): boolean {
  return MOBILE.test(value.replace(/[\s()-]/g, ""));
}

export function isOptionalE164(value: string | undefined): boolean {
  return value === undefined || E164.test(value);
}
