"use client";

export interface MapPoint {
  lat: number;
  lng: number;
  label: string;
}

/** Google Maps directions for the route, meeting point and drop-off. */
export function GoogleRouteMap({ points, label }: { points: MapPoint[]; label: string }) {
  if (points.length < 2) return null;
  const origin = points[0];
  const destination = points[points.length - 1];
  if (!origin || !destination) return null;
  const via = points
    .slice(1, -1)
    .map((point) => `+to:${point.lat},${point.lng}`)
    .join("");
  const embed = `https://maps.google.com/maps?hl=ar&saddr=${origin.lat},${origin.lng}&daddr=${destination.lat},${destination.lng}${via}&output=embed`;
  const waypointQuery = points
    .slice(1, -1)
    .map((point) => `${point.lat},${point.lng}`)
    .join("|");
  const waypoints = waypointQuery ? `&waypoints=${encodeURIComponent(waypointQuery)}` : "";
  const open = `https://www.google.com/maps/dir/?api=1&origin=${origin.lat},${origin.lng}&destination=${destination.lat},${destination.lng}${waypoints}&travelmode=driving`;

  return (
    <figure className="mt-4">
      <iframe
        title={label}
        src={embed}
        className="border-border h-80 w-full rounded-lg border"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
      />
      <figcaption className="mt-2 flex flex-wrap items-center justify-between gap-2 text-sm">
        <span className="text-muted-foreground">
          {points.map((point) => point.label).join(" · ")}
        </span>
        <a
          href={open}
          target="_blank"
          rel="noreferrer"
          className="text-primary font-semibold underline-offset-4 hover:underline"
        >
          {label}
        </a>
      </figcaption>
    </figure>
  );
}
