"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, FormError, TextInput } from "@/components/ui/field";
import { ApiRequestError, getMe, signIn } from "@/features/auth/api";
import { apiErrorMessage } from "@/lib/api/error-message";
import { AuthAlternatives } from "@/features/auth/auth-alternatives";
import { onValidSubmit } from "@/features/auth/form-submit";
import { useSession } from "@/features/auth/session-provider";
import { Link, useRouter } from "@/i18n/navigation";

export function SignInForm() {
  const t = useTranslations("Auth");
  const errorsT = useTranslations("Errors");
  const router = useRouter();
  const { refreshAccount } = useSession();
  const [formError, setFormError] = useState<string | undefined>();

  const schema = z.object({
    email: z.email(t("errors.email")),
    password: z.string().min(1, t("errors.required")),
  });
  type Values = z.infer<typeof schema>;

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    try {
      await signIn(values.email, values.password);
      await refreshAccount();
      let setupDone = false;
      let role: string | null = null;
      try {
        setupDone = localStorage.getItem("fi-sikkati-setup-done") === "1";
        role = localStorage.getItem("fi-sikkati-role-intent");
      } catch {
        setupDone = false;
      }
      const account = await getMe();
      const isDriver = account.roles.includes("DRIVER");
      if (!setupDone || !role || (role === "driver" && !isDriver)) {
        router.replace("/me/setup");
        return;
      }
      router.replace(role === "driver" ? "/trips/new" : "/search");
    } catch (error) {
      setFormError(apiErrorMessage(error, errorsT));
    }
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
      <Field id="password" label={t("password")} error={form.formState.errors.password?.message}>
        <TextInput
          id="password"
          type="password"
          autoComplete="current-password"
          {...form.register("password")}
        />
      </Field>
      <p className="text-sm">
        <Link
          href="/auth/forgot-password"
          className="text-primary font-semibold underline-offset-4 hover:underline"
        >
          {t("forgotLink")}
        </Link>
      </p>
      <FormError message={formError} />
      <Button type="submit" block disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? t("submitting") : t("signInSubmit")}
      </Button>
      <AuthAlternatives mode="signIn" />
      <p className="text-muted-foreground text-center text-sm">
        {t.rich("needAccount", {
          link: (chunks) => (
            <Link
              href="/auth/register"
              className="text-primary font-semibold underline-offset-4 hover:underline"
            >
              {chunks}
            </Link>
          ),
        })}
      </p>
    </form>
  );
}
