import { useEffect, useRef, useState } from "react";

import { useI18n } from "@/i18n";
import { useFavorites } from "@/hooks/useFavorites";

type Size = "sm" | "md" | "lg";

interface Props {
  icao: string;
  /** Visual size variant — design kit §25.1. Default: md. */
  size?: Size;
  /** Use the overlay variant (dark translucent background) — design kit §25.2. */
  overlay?: boolean;
  /** Stop click event from bubbling (e.g. when inside a Link card). Default: true. */
  stopPropagation?: boolean;
  /** Disable the button. */
  disabled?: boolean;
  /** Extra className(s) to append (positioning, etc). */
  className?: string;
}

export function FavoriteToggle({
  icao,
  size = "md",
  overlay = false,
  stopPropagation = true,
  disabled = false,
  className,
}: Props) {
  const { t } = useI18n();
  const { isFavorite, toggle } = useFavorites();
  const active = isFavorite(icao);
  const [pulse, setPulse] = useState(false);
  const wasActiveRef = useRef(active);

  // Trigger the one-shot pulse only on inactive → active transitions.
  useEffect(() => {
    if (active && !wasActiveRef.current) {
      setPulse(true);
      const id = window.setTimeout(() => setPulse(false), 350);
      return () => window.clearTimeout(id);
    }
    wasActiveRef.current = active;
    return undefined;
  }, [active]);

  const classes = [
    "fav-toggle",
    size === "sm" ? "fav-toggle--sm" : size === "lg" ? "fav-toggle--lg" : "",
    overlay ? "fav-toggle--overlay" : "",
    active ? "is-active" : "",
    pulse ? "just-added" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type="button"
      className={classes}
      aria-pressed={active}
      aria-label={active ? t("favorites.toggle.remove") : t("favorites.toggle.add")}
      title={active ? t("favorites.toggle.remove") : t("favorites.toggle.add")}
      disabled={disabled}
      onClick={(event) => {
        if (stopPropagation) event.stopPropagation();
        event.preventDefault();
        void toggle(icao);
      }}
    >
      <i className={active ? "fa-solid fa-star" : "fa-regular fa-star"} aria-hidden="true" />
    </button>
  );
}
