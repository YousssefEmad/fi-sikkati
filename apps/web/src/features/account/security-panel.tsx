"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError, changePassword, deleteMe, type Account } from "@/features/auth/api";
import { onValidSubmit } from "@/features/auth/form-submit";
import { useSession } from "@/features/auth/session-provider";
import { useRouter } from "@/i18n/navigation";

export function SecurityPanel({
  account,
  passwordMinLength,
  deletionGraceDays,
}: {
  account: Account;
  passwordMinLength: number;
  deletionGraceDays: number;
}) {
  const t = useTranslations("Account");
  const router = useRouter();
  const { refreshAccount } = useSession();
  const [passwordError, setPasswordError] = useState<string | undefined>();
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [deleteError, setDeleteError] = useState<string | undefined>();
  const [confirmEmail, setConfirmEmail] = useState("");

  const schema = z
    .object({
      currentPassword: z.string().min(1),
      newPassword: z
        .string()
        .min(passwordMinLength, t("errors.passwordMin", { min: passwordMinLength })),
      confirm: z.string(),
    })
    .refine((value) => value.newPassword === value.confirm, {
      path: ["confirm"],
      message: t("errors.passwordMatch"),
    });
  type Values = z.infer<typeof schema>;
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { currentPassword: "", newPassword: "", confirm: "" },
  });

  async function onChangePassword(values: Values) {
    setPasswordError(undefined);
    setPasswordSaved(false);
    try {
      await changePassword(values.currentPassword, values.newPassword);
      setPasswordSaved(true);
      form.reset();
    } catch (error) {
      setPasswordError(error instanceof ApiRequestError ? error.message : t("errors.generic"));
    }
  }

  async function onDelete() {
    setDeleteError(undefined);
    if (confirmEmail !== account.email) {
      setDeleteError(t("deleteMismatch"));
      return;
    }
    try {
      await deleteMe();
      await refreshAccount();
      router.replace("/");
    } catch (error) {
      setDeleteError(error instanceof ApiRequestError ? error.message : t("errors.generic"));
    }
  }

  return (
    <div className="flex max-w-xl flex-col gap-12">
      <section>
        <h2 className="text-xl font-bold">{t("changePassword")}</h2>
        <form
          className="mt-4 flex flex-col gap-4"
          method="post"
          onSubmit={onValidSubmit(form.handleSubmit, onChangePassword)}
          noValidate
        >
          <Field
            id="currentPassword"
            label={t("currentPassword")}
            error={form.formState.errors.currentPassword?.message}
          >
            <TextInput
              id="currentPassword"
              type="password"
              autoComplete="current-password"
              {...form.register("currentPassword")}
            />
          </Field>
          <Field
            id="newPassword"
            label={t("newPassword")}
            error={form.formState.errors.newPassword?.message}
          >
            <TextInput
              id="newPassword"
              type="password"
              autoComplete="new-password"
              {...form.register("newPassword")}
            />
          </Field>
          <Field
            id="confirm"
            label={t("confirmPassword")}
            error={form.formState.errors.confirm?.message}
          >
            <TextInput
              id="confirm"
              type="password"
              autoComplete="new-password"
              {...form.register("confirm")}
            />
          </Field>
          <FormError message={passwordError} />
          {passwordSaved ? <p className="text-success text-sm">{t("passwordChanged")}</p> : null}
          <Button type="submit" disabled={form.formState.isSubmitting}>
            {t("savePassword")}
          </Button>
        </form>
      </section>

      <section>
        <h2 className="text-xl font-bold">{t("deleteTitle")}</h2>
        <p className="text-muted-foreground mt-2 text-sm leading-relaxed">
          {t("deleteBody", { days: deletionGraceDays })}
        </p>
        <div className="mt-4 flex flex-col gap-3">
          <Field id="confirmEmail" label={t("deleteConfirm")} hint={account.email}>
            <TextInput
              id="confirmEmail"
              type="email"
              value={confirmEmail}
              onChange={(event) => {
                setConfirmEmail(event.target.value);
              }}
              autoComplete="off"
            />
          </Field>
          <FormError message={deleteError} />
          <Button variant="outline" onClick={() => void onDelete()}>
            {t("deleteSubmit")}
          </Button>
        </div>
      </section>
    </div>
  );
}
