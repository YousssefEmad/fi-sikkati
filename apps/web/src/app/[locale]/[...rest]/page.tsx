import { notFound } from "next/navigation";

/** Any path under a valid locale that no route matched renders the locale-aware 404. */
export default function CatchAllPage(): never {
  notFound();
}
