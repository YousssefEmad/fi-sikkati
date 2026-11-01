import { SecurityPageClient } from "@/features/account/security-page";
import { fetchPublicConfig } from "@/features/platform/api";

export default async function SecurityPage() {
  const config = await fetchPublicConfig();
  return (
    <SecurityPageClient
      passwordMinLength={config?.passwordMinLength ?? 10}
      deletionGraceDays={config?.deletionGraceDays ?? 14}
    />
  );
}
