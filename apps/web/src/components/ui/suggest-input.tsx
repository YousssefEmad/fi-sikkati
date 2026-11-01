"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { TextInput } from "@/components/ui/field";
import { matchSuggest, type SuggestOption } from "@/lib/suggest";

export function SuggestInput({
  id,
  value,
  onValueChange,
  options,
  onPick,
  placeholder,
  "aria-invalid": invalid,
  "aria-describedby": describedBy,
}: {
  id: string;
  value: string;
  onValueChange: (value: string) => void;
  options: readonly SuggestOption[];
  onPick?: (option: SuggestOption) => void;
  placeholder?: string;
  "aria-invalid"?: boolean | undefined;
  "aria-describedby"?: string | undefined;
}) {
  const t = useTranslations("Common");
  const listId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [trackedValue, setTrackedValue] = useState(value);
  if (value !== trackedValue) {
    setTrackedValue(value);
    setActive(0);
  }
  const matches = matchSuggest(options, value);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  function pick(option: SuggestOption): void {
    onValueChange(option.label);
    onPick?.(option);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className="relative">
      <TextInput
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        onFocus={() => {
          setOpen(true);
        }}
        onChange={(event) => {
          onValueChange(event.target.value);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            setActive((index) => Math.min(index + 1, Math.max(matches.length - 1, 0)));
          } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((index) => Math.max(index - 1, 0));
          } else if (event.key === "Enter" && open && matches[active]) {
            event.preventDefault();
            pick(matches[active]);
          } else if (event.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="border-border bg-surface absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-md border py-1 shadow-[var(--shadow-card)]"
        >
          {matches.length === 0 ? (
            <li className="text-muted-foreground px-3 py-2 text-sm">{t("suggestEmpty")}</li>
          ) : (
            matches.map((option, index) => (
              <li key={option.id} role="option" aria-selected={index === active}>
                <button
                  type="button"
                  className={`flex w-full items-baseline justify-between gap-3 px-3 py-2 text-start text-sm ${
                    index === active ? "bg-brand-soft" : "hover:bg-brand-soft"
                  }`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    pick(option);
                  }}
                  onMouseEnter={() => {
                    setActive(index);
                  }}
                >
                  <span className="font-medium">{option.label}</span>
                  {option.hint ? (
                    <span className="text-muted-foreground shrink-0 text-xs">{option.hint}</span>
                  ) : null}
                </button>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </div>
  );
}
