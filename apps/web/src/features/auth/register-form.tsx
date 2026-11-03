"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useLocale, useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Field, FormError, TextInput } from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { ApiRequestError, registerAccount } from "@/features/auth/api";
import { onValidSubmit } from "@/features/auth/form-submit";
import { adultCutoffDate, isMobileNumber } from "@/features/auth/validation";
import { Link, useRouter } from "@/i18n/navigation";
import { useState } from "react";

export function RegisterForm({
  passwordMinLength,
  minimumAgeYears,
  termsVersion,
  privacyVersion,
}: {
  passwordMinLength: number;
  minimumAgeYears: number;
  termsVersion: string;
  privacyVersion: string;
}) {
  const t = useTranslations("Auth");
  const locale = useLocale();
  const router = useRouter();
  const [formError, setFormError] = useState<string | undefined>();

  const schema = z.object({
    email: z.email(t("errors.email")),
    password: z
      .string()
      .min(passwordMinLength, t("errors.passwordMin", { min: passwordMinLength })),
    displayName: z.string().trim().min(2, t("errors.displayName")).max(60),
    fullName: z.string().trim().min(2, t("errors.fullName")).max(120),
    dateOfBirth: z
      .string()
      .min(1, t("errors.required"))
      .refine(
        (value) => value <= adultCutoffDate(minimumAgeYears),
        t("errors.tooYoung", { age: minimumAgeYears }),
      ),
    phone: z
      .string()
      .trim()
      .refine((value) => value.length === 0 || isMobileNumber(value), t("errors.phone")),
    accepted: z.boolean().refine((value) => value, t("errors.legal")),
  });

  type Values = z.input<typeof schema>;

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      email: "",
      password: "",
      displayName: "",
      fullName: "",
      dateOfBirth: "",
      phone: "",
      accepted: false,
    },
  });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    const parsed = schema.parse(values);
    try {
      await registerAccount({
        email: parsed.email,
        password: parsed.password,
        displayName: parsed.displayName,
        fullName: parsed.fullName,
        dateOfBirth: parsed.dateOfBirth,
        locale: locale === "en" ? "en" : "ar",
        phone: parsed.phone.length > 0 ? parsed.phone : null,
        acceptedTermsVersion: termsVersion,
        acceptedPrivacyVersion: privacyVersion,
      });
      router.push("/auth/check-email");
    } catch (error) {
      if (error instanceof ApiRequestError && error.problem.code === "DISPLAY_NAME_TAKEN") {
        form.setError("displayName", { message: t("errors.displayNameTaken") });
        return;
      }
      if (error instanceof ApiRequestError && error.problem.code === "PHONE_TAKEN") {
        form.setError("phone", { message: t("errors.phoneTaken") });
        return;
      }
      setFormError(error instanceof ApiRequestError ? error.message : t("errors.generic"));
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
      <Field
        id="password"
        label={t("password")}
        hint={t("passwordHint", { min: passwordMinLength })}
        error={form.formState.errors.password?.message}
      >
        <TextInput
          id="password"
          type="password"
          autoComplete="new-password"
          {...form.register("password")}
        />
      </Field>
      <Field
        id="displayName"
        label={t("displayName")}
        error={form.formState.errors.displayName?.message}
      >
        <TextInput id="displayName" autoComplete="nickname" {...form.register("displayName")} />
      </Field>
      <Field id="fullName" label={t("fullName")} error={form.formState.errors.fullName?.message}>
        <TextInput id="fullName" autoComplete="name" {...form.register("fullName")} />
      </Field>
      <Field
        id="dateOfBirth"
        label={t("dateOfBirth")}
        hint={t("ageHint", { age: minimumAgeYears })}
        error={form.formState.errors.dateOfBirth?.message}
      >
        <TextInput id="dateOfBirth" type="date" {...form.register("dateOfBirth")} />
      </Field>
      <Field
        id="phone"
        label={t("phone")}
        hint={t("phoneHint")}
        error={form.formState.errors.phone?.message}
      >
        <TextInput
          id="phone"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          {...form.register("phone")}
        />
      </Field>
      <div className="flex items-start gap-3">
        <input
          id="accepted"
          type="checkbox"
          className="mt-1 size-4"
          aria-invalid={Boolean(form.formState.errors.accepted) || undefined}
          aria-describedby={form.formState.errors.accepted ? "accepted-error" : undefined}
          {...form.register("accepted")}
        />
        <label htmlFor="accepted" className="text-sm leading-relaxed">
          {t.rich("acceptLegal", {
            terms: (chunks) => (
              <Link
                href="/legal/terms"
                className="text-primary font-semibold underline-offset-4 hover:underline"
              >
                {chunks}
              </Link>
            ),
            privacy: (chunks) => (
              <Link
                href="/legal/privacy"
                className="text-primary font-semibold underline-offset-4 hover:underline"
              >
                {chunks}
              </Link>
            ),
          })}
        </label>
      </div>
      {form.formState.errors.accepted ? (
        <p role="alert" className="text-danger text-xs font-medium">
          {form.formState.errors.accepted.message}
        </p>
      ) : null}
      <FormError message={formError} />
      <Button type="submit" block disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? t("submitting") : t("registerSubmit")}
      </Button>
      <p className="text-muted-foreground text-center text-sm">
        {t.rich("haveAccount", {
          link: (chunks) => (
            <Link
              href="/auth/sign-in"
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
