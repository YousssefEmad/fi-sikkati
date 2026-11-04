/** Client-only onboarding intent: driver must finish car/driver data; passenger may soft-skip. */

export type SetupRole = "driver" | "passenger";

const ROLE_KEY = "fi-sikkati-role-intent";
const DONE_KEY = "fi-sikkati-setup-done";
const DRIVE_SKIP_KEY = "fi-sikkati-drive-skip-until";
const SKIP_DAYS = 7;

export function readSetupRole(): SetupRole | null {
  try {
    const value = localStorage.getItem(ROLE_KEY);
    return value === "driver" || value === "passenger" ? value : null;
  } catch {
    return null;
  }
}

export function writeSetupRole(role: SetupRole): void {
  try {
    localStorage.setItem(ROLE_KEY, role);
  } catch {
    /* ignore */
  }
}

export function readSetupDone(): boolean {
  try {
    return localStorage.getItem(DONE_KEY) === "1";
  } catch {
    return false;
  }
}

export function markSetupDone(): void {
  try {
    localStorage.setItem(DONE_KEY, "1");
  } catch {
    /* ignore */
  }
}

export function skipDriveTemporarily(): void {
  const until = Date.now() + SKIP_DAYS * 24 * 60 * 60 * 1000;
  try {
    localStorage.setItem(DRIVE_SKIP_KEY, String(until));
  } catch {
    /* ignore */
  }
}

export function isDriveSkipped(): boolean {
  try {
    return Number(localStorage.getItem(DRIVE_SKIP_KEY) ?? "0") > Date.now();
  } catch {
    return false;
  }
}

export function shouldRemindDrive(): boolean {
  try {
    const until = Number(localStorage.getItem(DRIVE_SKIP_KEY) ?? "0");
    return until > 0;
  } catch {
    return false;
  }
}

export { DRIVE_SKIP_KEY };
