"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError, type Account } from "@/features/auth/api";
import { useSession } from "@/features/auth/session-provider";
import { apiJson } from "@/lib/api/json";

function shownNumber(value: string): string {
  if (value.startsWith("+20")) return `0${value.slice(3)}`;
  return value;
}

export function PhoneForm({ account }: { account: Account }) {
  const t = useTranslations("Account");
  const { refreshAccount } = useSession();
  const [phone, setPhone] = useState(account.phone ? shownNumber(account.phone) : "");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | undefined>();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  async function sendCode(): Promise<void> {
    setBusy(true);
    setError(undefined);
    try {
      const response = await apiJson<{ devCode: string | null }>("/api/v1/me/phone/challenges", {
        method: "POST",
        body: JSON.stringify({ phone }),
      });
      setDevCode(response.devCode ?? undefined);
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("phoneError"));
    } finally {
      setBusy(false);
    }
  }

  async function confirm(): Promise<void> {
    setBusy(true);
    setError(undefined);
    try {
      await apiJson<undefined>("/api/v1/me/phone/confirm", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      setSent(false);
      setCode("");
      setDevCode(undefined);
      await refreshAccount();
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : t("phoneError"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="border-border mt-8 rounded-xl border p-4">
      <h2 className="text-lg font-bold">{t("phoneTitle")}</h2>
      <p className="text-muted-foreground mt-1 text-sm">{t("phoneBody")}</p>
      {account.phoneVerified && account.phone ? (
        <p className="mt-3 text-sm font-semibold">{t("phoneOn", { phone: shownNumber(account.phone) })}</p>
      ) : null}
      <div className="mt-4 flex flex-col gap-4">
        <Field id="mobile" label={t("phone")}>
          <TextInput
            id="mobile"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={phone}
            onChange={(event) => {
              setPhone(event.target.value);
              setSent(false);
            }}
          />
        </Field>
        <Button type="button" variant="brand" disabled={busy || phone.trim().length < 8} onClick={() => void sendCode()}>
          {t("phoneSend")}
        </Button>
        {sent ? (
          <>
            <Field id="phone-code" label={t("phoneCode")}>
              <TextInput
                id="phone-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(event) => {
                  setCode(event.target.value);
                }}
              />
            </Field>
            {devCode ? <p className="bg-brand-soft rounded-md px-3 py-2 text-sm">{t("phoneDev", { code: devCode })}</p> : null}
            <Button type="button" disabled={busy || code.trim().length !== 6} onClick={() => void confirm()}>
              {t("phoneConfirm")}
            </Button>
          </>
        ) : null}
        <FormError message={error} />
      </div>
    </section>
  );
}
