import {
  cloneElement,
  isValidElement,
  type InputHTMLAttributes,
  type ReactElement,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

import { cn } from "@/lib/utils";

const controlClass =
  "border-border bg-surface text-foreground min-h-11 w-full rounded-md border px-3 text-sm disabled:opacity-50";

export function Field({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string | undefined;
  error?: string | undefined;
  children: ReactNode;
}) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const a11y: { "aria-describedby"?: string; "aria-invalid"?: boolean } = {};
  if (describedBy) a11y["aria-describedby"] = describedBy;
  if (error) a11y["aria-invalid"] = true;
  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<typeof a11y>, a11y)
    : children;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-semibold">
        {label}
      </label>
      {control}
      {hint ? (
        <p id={hintId} className="text-muted-foreground text-xs">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="text-danger text-xs font-medium">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(controlClass, className)} {...props} />;
}

export function TextArea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(controlClass, "min-h-24 py-2", className)} {...props} />;
}

export function SelectInput({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(controlClass, className)} {...props} />;
}

export function FormError({ message }: { message: string | undefined }) {
  if (!message) return null;
  return (
    <p role="alert" className="text-danger text-sm font-medium">
      {message}
    </p>
  );
}
