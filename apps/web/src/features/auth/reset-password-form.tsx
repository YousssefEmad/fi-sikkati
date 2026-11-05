"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError, resetPassword } from "@/features/auth/api";
import { apiErrorMessage } from "@/lib/api/error-message";
import { onValidSubmit } from "@/features/auth/form-submit";
import { Link, useRouter } from "@/i18n/navigation";

export function ResetPasswordForm({
  token,
  passwordMinLength,
}: {
  token: string;
  passwordMinLength: number;
}) {
  const t = useTranslations("Auth");
  const errorsT = useTranslations("Errors");
  const router = useRouter();
  const [formError, setFormError] = useState<string | undefined>();

  const schema = z
    .object({
      password: z
        .string()
        .min(passwordMinLength, t("errors.passwordMin", { min: passwordMinLength })),
      confirm: z.string(),
    })
    .refine((value) => value.password === value.confirm, {
      message: t("errors.passwordMatch"),
      path: ["confirm"],
    });
  type Values = z.infer<typeof schema>;
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirm: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    try {
      await resetPassword(token, values.password);
      router.replace("/auth/sign-in");
    } catch (error) {
      setFormError(apiErrorMessage(error, errorsT));
    }
  }

  if (!token) {
    return <p className="text-danger">{t("missingToken")}</p>;
  }

  return (
    <form
      className="flex flex-col gap-5"
      method="post"
      onSubmit={onValidSubmit(form.handleSubmit, onSubmit)}
      noValidate
    >
      <Field id="password" label={t("newPassword")} error={form.formState.errors.password?.message}>
        <TextInput
          id="password"
          type="password"
          autoComplete="new-password"
          {...form.register("password")}
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
      <FormError message={formError} />
      <Button type="submit" block disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? t("submitting") : t("resetSubmit")}
      </Button>
      <p className="text-center text-sm">
        <Link
          href="/auth/sign-in"
          className="text-primary font-semibold underline-offset-4 hover:underline"
        >
          {t("backToSignIn")}
        </Link>
      </p>
    </form>
  );
}
