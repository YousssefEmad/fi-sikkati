"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError, forgotPassword } from "@/features/auth/api";
import { apiErrorMessage } from "@/lib/api/error-message";
import { onValidSubmit } from "@/features/auth/form-submit";
import { Link } from "@/i18n/navigation";

export function ForgotPasswordForm() {
  const t = useTranslations("Auth");
  const errorsT = useTranslations("Errors");
  const [done, setDone] = useState(false);
  const [formError, setFormError] = useState<string | undefined>();

  const schema = z.object({ email: z.email(t("errors.email")) });
  type Values = z.infer<typeof schema>;
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    try {
      await forgotPassword(values.email);
      setDone(true);
    } catch (error) {
      setFormError(apiErrorMessage(error, errorsT));
    }
  }

  if (done) {
    return <p className="text-foreground leading-relaxed">{t("forgotSent")}</p>;
  }

  return (
    <form
      className="flex flex-col gap-5"
      method="post"
      onSubmit={onValidSubmit(form.handleSubmit, onSubmit)}
      noValidate
    >
      <Field id="email" label={t("email")} error={form.formState.errors.email?.message}>
        <TextInput id="email" type="email" autoComplete="email" {...form.register("email")} />
      </Field>
      <FormError message={formError} />
      <Button type="submit" block disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? t("submitting") : t("forgotSubmit")}
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
