import { getTranslations } from "next-intl/server";

import { fetchPublicConfig } from "@/features/platform/api";

/** Server Component: shows whether the web app can reach the API (dev/staging aid). */
export async function SystemStatus() {
  const [t, config] = await Promise.all([getTranslations("SystemStatus"), fetchPublicConfig()]);
  const connected = config !== null;

  return (
    <p
      className="text-muted-foreground flex items-center gap-2 text-xs"
      data-testid="system-status"
    >
      <span
        aria-hidden="true"
        className={connected ? "bg-success size-2 rounded-full" : "bg-danger size-2 rounded-full"}
      />
      <span className="font-medium">{t("label")}</span>
      <span data-testid="system-status-value">
        {connected ? t("connected", { environment: config.environment }) : t("unavailable")}
      </span>
    </p>
  );
}
