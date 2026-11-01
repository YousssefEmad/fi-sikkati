"use client";

import { useLocale } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { SuggestInput } from "@/components/ui/suggest-input";
import { autocompletePlaces } from "@/features/search/api";
import { placesFor, type PlaceOption } from "@/features/places/catalog";
import { fold, type SuggestOption } from "@/lib/suggest";

export interface PickedPlace {
  lat: number;
  lng: number;
  label: string;
}

export function PlaceSuggest({
  id,
  value,
  onValueChange,
  onPick,
  "aria-invalid": invalid,
  "aria-describedby": describedBy,
}: {
  id: string;
  value: string;
  onValueChange: (value: string) => void;
  onPick: (place: PickedPlace | null) => void;
  "aria-invalid"?: boolean | undefined;
  "aria-describedby"?: string | undefined;
}) {
  const locale = useLocale();
  const local = useMemo(() => placesFor(locale), [locale]);
  const [remote, setRemote] = useState<{ query: string; items: PlaceOption[] }>({
    query: "",
    items: [],
  });

  useEffect(() => {
    const query = value.trim();
    if (query.length < 2) return;
    const timer = setTimeout(() => {
      void autocompletePlaces(query)
        .then((items) => {
          const known = new Set(local.map((place) => fold(place.label)));
          setRemote({
            query,
            items: items
              .filter((item) => !known.has(fold(item.label)))
              .map((item) => ({
                id: `remote-${item.lat.toFixed(4)}-${item.lng.toFixed(4)}`,
                label: item.label,
                lat: item.lat,
                lng: item.lng,
              })),
          });
        })
        .catch(() => {
          setRemote({ query, items: [] });
        });
    }, 250);
    return () => {
      clearTimeout(timer);
    };
  }, [local, value]);

  const query = value.trim();
  const remoteItems = query.length >= 2 && remote.query === query ? remote.items : [];
  const options = [...local, ...remoteItems];

  function pick(option: SuggestOption): void {
    const place = options.find((item) => item.id === option.id);
    if (!place) return;
    onValueChange(place.label);
    onPick({ lat: place.lat, lng: place.lng, label: place.label });
  }

  return (
    <SuggestInput
      id={id}
      value={value}
      options={options}
      aria-invalid={invalid}
      aria-describedby={describedBy}
      onValueChange={(next) => {
        onValueChange(next);
        onPick(null);
      }}
      onPick={pick}
    />
  );
}
