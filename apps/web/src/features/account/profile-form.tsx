"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useLocale, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Field, FormError, SelectInput, TextArea, TextInput } from "@/components/ui/field";
import { SuggestInput } from "@/components/ui/suggest-input";
import { placesFor } from "@/features/places/catalog";
import { ApiRequestError, updateMe, type Account } from "@/features/auth/api";
import { onValidSubmit } from "@/features/auth/form-submit";
import { useSession } from "@/features/auth/session-provider";

export function ProfileForm({ account }: { account: Account }) {
  const t = useTranslations("Account");
  const locale = useLocale();
  const cityOptions = useMemo(() => placesFor(locale), [locale]);
  const { refreshAccount } = useSession();
  const [formError, setFormError] = useState<string | undefined>();
  const [saved, setSaved] = useState(false);

  const schema = z.object({
    displayName: z.string().trim().min(2).max(60),
    fullName: z.string().trim().min(2).max(120),
    city: z.string().trim().max(80),
    bio: z.string().max(300),
    locale: z.enum(["ar", "en"]),
  });
  type Values = z.input<typeof schema>;

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      displayName: account.displayName,
      fullName: account.fullName,
      city: account.city ?? "",
      bio: account.bio ?? "",
      locale: account.locale === "en" ? "en" : "ar",
    },
  });
  const city = useWatch({ control: form.control, name: "city" });

  async function onSubmit(values: Values) {
    setFormError(undefined);
    setSaved(false);
    const parsed = schema.parse(values);
    try {
      await updateMe({
        displayName: parsed.displayName,
        fullName: parsed.fullName,
        city: parsed.city || null,
        bio: parsed.bio || null,
        locale: parsed.locale,
      });
      await refreshAccount();
      setSaved(true);
    } catch (error) {
      if (error instanceof ApiRequestError && error.problem.code === "DISPLAY_NAME_TAKEN") {
        form.setError("displayName", { message: t("errors.displayNameTaken") });
        return;
      }
      setFormError(error instanceof ApiRequestError ? error.message : t("errors.generic"));
    }
  }

  return (
    <form
      className="flex max-w-xl flex-col gap-5"
      onSubmit={onValidSubmit(form.handleSubmit, onSubmit)}
      noValidate
    >
      <Field
        id="displayName"
        label={t("displayName")}
        error={form.formState.errors.displayName?.message}
      >
        <TextInput id="displayName" {...form.register("displayName")} />
      </Field>
      <Field id="fullName" label={t("fullName")} error={form.formState.errors.fullName?.message}>
        <TextInput id="fullName" {...form.register("fullName")} />
      </Field>
      <Field id="city" label={t("city")} error={form.formState.errors.city?.message}>
        <SuggestInput
          id="city"
          value={city}
          options={cityOptions}
          onValueChange={(value) => {
            form.setValue("city", value, { shouldDirty: true, shouldValidate: true });
          }}
        />
      </Field>
      <Field id="bio" label={t("bio")} error={form.formState.errors.bio?.message}>
        <TextArea id="bio" maxLength={300} {...form.register("bio")} />
      </Field>
      <Field id="locale" label={t("locale")}>
        <SelectInput id="locale" {...form.register("locale")}>
          <option value="ar">{t("localeAr")}</option>
          <option value="en">{t("localeEn")}</option>
        </SelectInput>
      </Field>
      <FormError message={formError} />
      {saved ? <p className="text-success text-sm font-medium">{t("saved")}</p> : null}
      <Button type="submit" disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? t("saving") : t("save")}
      </Button>
    </form>
  );
}
