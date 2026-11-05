"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiRequestError, type Account } from "@/features/auth/api";
import { apiErrorMessage } from "@/lib/api/error-message";
import { useSession } from "@/features/auth/session-provider";
import { apiJson } from "@/lib/api/json";
import { cn } from "@/lib/utils";

function shownNumber(value: string): string {
  if (value.startsWith("+20")) return `0${value.slice(3)}`;
  return value;
}

export function PhoneForm({ account }: { account: Account }) {
  const t = useTranslations("Account");
  const errorsT = useTranslations("Errors");
  const { refreshAccount } = useSession();
  const verified = Boolean(account.phoneVerified && account.phone);
  const [phone, setPhone] = useState(account.phone ? shownNumber(account.phone) : "");
  const [code, setCode] = useState("");
  const [devCode, setDevCode] = useState<string | undefined>();
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [changing, setChanging] = useState(false);

  const locked = verified && !changing;

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
      setError(apiErrorMessage(err, errorsT));
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
      setChanging(false);
      await refreshAccount();
    } catch (err) {
      setError(apiErrorMessage(err, errorsT));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="border-border mt-8 rounded-xl border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-bold">{t("phoneTitle")}</h2>
        {verified && !changing ? <StatusBadge tone="success">{t("phoneVerifiedBadge")}</StatusBadge> : null}
      </div>
      <p className="text-muted-foreground mt-1 text-sm">{t("phoneBody")}</p>

      {locked ? (
        <div className="bg-success/10 border-success/25 mt-4 rounded-xl border px-4 py-3">
          <p className="text-success text-base font-extrabold">{t("phoneVerifiedLabel")}</p>
          <p className="text-foreground mt-1 text-sm font-bold">
            {t("phoneOn", { phone: shownNumber(account.phone ?? phone) })}
          </p>
          <div className="mt-3">
            <Field id="mobile-locked" label={t("phone")}>
              <TextInput
                id="mobile-locked"
                type="tel"
                value={shownNumber(account.phone ?? phone)}
                readOnly
                disabled
                className="cursor-not-allowed opacity-55"
              />
            </Field>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => {
              setChanging(true);
              setSent(false);
              setCode("");
              setDevCode(undefined);
              setPhone(account.phone ? shownNumber(account.phone) : "");
            }}
          >
            {t("phoneChange")}
          </Button>
        </div>
      ) : (
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
          <Button
            type="button"
            variant="brand"
            className={cn(sent && "pointer-events-none opacity-45")}
            disabled={busy || phone.trim().length < 8 || sent}
            onClick={() => void sendCode()}
          >
            {sent ? t("phoneSent") : t("phoneSend")}
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
              {devCode ? (
                <p className="bg-brand-soft rounded-md px-3 py-2 text-sm">
                  {t("phoneDev", { code: devCode })}
                </p>
              ) : null}
              <Button
                type="button"
                disabled={busy || code.trim().length !== 6}
                onClick={() => void confirm()}
              >
                {t("phoneConfirm")}
              </Button>
            </>
          ) : null}
          {changing ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setChanging(false);
                setSent(false);
                setCode("");
                setDevCode(undefined);
                setPhone(account.phone ? shownNumber(account.phone) : "");
              }}
            >
              {t("phoneCancelChange")}
            </Button>
          ) : null}
          <FormError message={error} />
        </div>
      )}
    </section>
  );
}
