import { getTranslations } from "next-intl/server";

export async function ArticlePage({
  namespace,
}: {
  namespace: "HowItWorks" | "PublicSafety" | "Faq" | "About" | "Contact";
}) {
  const t = await getTranslations(namespace);
  const paragraphs = t.raw("paragraphs") as string[];
  return (
    <article className="mx-auto w-full max-w-3xl px-4 py-16 sm:px-6">
      <p className="text-muted-foreground text-sm font-semibold tracking-wide uppercase">
        {t("eyebrow")}
      </p>
      <h1 className="mt-3 text-4xl font-extrabold tracking-tight">{t("title")}</h1>
      <div className="mt-8 space-y-5 text-base leading-relaxed">
        {paragraphs.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </article>
  );
}
