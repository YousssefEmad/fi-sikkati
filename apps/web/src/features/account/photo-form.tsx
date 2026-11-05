"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { ApiRequestError } from "@/features/auth/api";
import { useSession } from "@/features/auth/session-provider";
import { postMultipart } from "@/lib/api/upload";

export function PhotoForm({ photoUrl }: { photoUrl: string | null | undefined }) {
  const t = useTranslations("Account");
  const { refreshAccount } = useSession();
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  async function onUpload(): Promise<void> {
    if (!file) return;
    setBusy(true);
    setError(undefined);
    try {
      const form = new FormData();
      form.set("file", file);
      await postMultipart("/api/v1/me/photo", form);
      await refreshAccount();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("errors.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h2 className="text-xl font-bold">{t("photo")}</h2>
      <p className="text-muted-foreground mt-1 text-sm">{t("photoHint")}</p>
      {photoUrl ? (
        // Public media URL after re-encoding; not user-authored HTML.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={photoUrl}
          alt=""
          className="border-border mt-3 size-28 rounded-full border-4 object-cover shadow-card"
        />
      ) : (
        <p className="text-muted-foreground mt-3 text-sm font-semibold">{t("photoEmpty")}</p>
      )}
      <label htmlFor="profile-photo" className="mt-3 block text-sm font-semibold">
        {t("photo")}
      </label>
      <input
        id="profile-photo"
        className="mt-1 block text-sm"
        type="file"
        accept="image/jpeg,image/png"
        aria-label={t("photo")}
        onChange={(event) => {
          setFile(event.target.files?.[0] ?? null);
        }}
      />
      <FormError message={error} />
      <Button className="mt-3" disabled={busy || !file} onClick={() => void onUpload()}>
        {busy ? t("photoUploading") : t("photoSave")}
      </Button>
    </section>
  );
}
