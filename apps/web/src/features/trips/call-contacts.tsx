"use client";

import { useQuery } from "@tanstack/react-query";
import { Phone } from "lucide-react";
import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { apiJson } from "@/lib/api/json";
import { cn } from "@/lib/utils";

interface CallContact {
  userId: string;
  displayName: string;
  phone: string;
}

export function TripCalls({ tripId }: { tripId: string }) {
  const t = useTranslations("Trips");
  const query = useQuery({
    queryKey: ["call-contacts", tripId],
    queryFn: () => apiJson<{ items: CallContact[] }>(`/api/v1/trips/${tripId}/call-contacts`),
    refetchInterval: 15_000,
  });
  const items = query.data?.items ?? [];

  return (
    <section className="border-border mt-6 rounded-xl border p-4">
      <h2 className="text-lg font-bold">{t("callTitle")}</h2>
      <p className="text-muted-foreground mt-1 text-sm">{t("callBody")}</p>
      {items.length === 0 ? <p className="mt-3 text-sm">{t("callEmpty")}</p> : null}
      <ul className="mt-3 space-y-2">
        {items.map((item) => (
          <li key={item.userId} className="flex items-center justify-between gap-3">
            <span className="font-semibold">{item.displayName}</span>
            <a href={`tel:${item.phone}`} className={cn(buttonVariants({ variant: "brand" }))}>
              <Phone aria-hidden="true" className="size-4" />
              {t("callButton")}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
