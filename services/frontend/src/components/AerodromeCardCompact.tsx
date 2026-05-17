import { Link } from "react-router-dom";

import type { Aerodrome } from "@/api/aerodromes";
import { FavoriteToggle } from "@/components/FavoriteToggle";
import { useI18n } from "@/i18n";

interface Props {
  aerodrome: Aerodrome;
  /** Optional TWR frequency (MHz). Rendered as a mono stat chip when set. */
  twrFrequency?: string | number | null;
  /** Optional runway count. Rendered as a mono stat chip when > 0. */
  runwayCount?: number;
}

/**
 * Compact list-item variant of `AerodromeCard` — design kit §28.
 *
 * Used in the dashboard favorites widget where multiple aerodromes stack
 * vertically inside a ~700 px panel. Click anywhere navigates to the detail
 * page; the embedded star toggle stops propagation.
 */
export function AerodromeCardCompact({ aerodrome, twrFrequency, runwayCount }: Props) {
  const { locale } = useI18n();
  const name = locale === "de" && aerodrome.name_de ? aerodrome.name_de : aerodrome.name;
  const region =
    locale === "de" && aerodrome.region_de ? aerodrome.region_de : aerodrome.region;
  const hasStats = (twrFrequency != null && twrFrequency !== "") || (runwayCount ?? 0) > 0;

  return (
    <Link
      to={`/aerodromes/${aerodrome.icao}`}
      className="aerodrome-card aerodrome-card--compact"
    >
      <div className="ad-icao">{aerodrome.icao}</div>
      <div className="ad-body">
        <span className="ad-name">{name}</span>
        {region && <span className="ad-meta">{region}</span>}
      </div>
      {hasStats && (
        <div className="ad-signals">
          {twrFrequency != null && twrFrequency !== "" && (
            <span className="ad-stat" title="Tower frequency">
              <i className="fa-solid fa-tower-broadcast" aria-hidden="true" /> {twrFrequency}
            </span>
          )}
          {(runwayCount ?? 0) > 0 && (
            <span className="ad-stat" title="Runways">
              <i className="fa-solid fa-road" aria-hidden="true" /> {runwayCount}
            </span>
          )}
        </div>
      )}
      <FavoriteToggle icao={aerodrome.icao} size="sm" />
    </Link>
  );
}
