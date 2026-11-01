import { cn } from "@/lib/utils";

export function Avatar({
  name,
  src,
  className,
}: {
  name: string;
  src?: string | null;
  className?: string;
}) {
  const initial = name.trim().slice(0, 1).toUpperCase() || "?";
  if (src) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt=""
        className={cn("size-10 rounded-full object-cover", className)}
      />
    );
  }
  return (
    <span
      aria-hidden="true"
      className={cn(
        "bg-brand text-brand-foreground inline-flex size-10 items-center justify-center rounded-full text-sm font-bold",
        className,
      )}
    >
      {initial}
    </span>
  );
}
