import { Link } from "react-router-dom";

import type { Aerodrome, SearchMatchType } from "@/api/aerodromes";
import { FavoriteToggle } from "@/components/FavoriteToggle";
import { FrequencyBadge } from "@/components/FrequencyBadge";
import { useI18n } from "@/i18n";

interface Props {
  aerodrome: Aerodrome;
  runwayCount?: number;
  twrFrequency?: { type: "twr"; value: string | number } | null;
  /** When provided and equals "fuzzy", show a subtle "similar match" badge. */
  matchType?: SearchMatchType;
}

export function AerodromeCard({ aerodrome, runwayCount, twrFrequency, matchType }: Props) {
  const { t, locale } = useI18n();
  const name = locale === "de" && aerodrome.name_de ? aerodrome.name_de : aerodrome.name;
  const region =
    locale === "de" && aerodrome.region_de ? aerodrome.region_de : aerodrome.region;

  return (
    <Link to={`/aerodromes/${aerodrome.icao}`} className="aerodrome-card">
      <div className="ad-head">
        <div>
          <div className="ad-icao">{aerodrome.icao}</div>
          <div className="ad-name">{name}</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          {matchType === "fuzzy" && (
            <span className="match-hint" title={t("search.match.fuzzy.tooltip")}>
              <i className="fa-solid fa-wand-magic-sparkles" aria-hidden="true" />
              {t("search.match.fuzzy")}
            </span>
          )}
          <FavoriteToggle icao={aerodrome.icao} size="sm" />
        </div>
      </div>
      <div className="ad-meta">
        <i className="fa-solid fa-location-dot" aria-hidden="true" />
        {region ?? aerodrome.country}
      </div>
      <div className="ad-freqs">
        {twrFrequency ? (
          <FrequencyBadge type={twrFrequency.type} value={twrFrequency.value} />
        ) : null}
      </div>
      <div className="ad-stats">
        <div>
          <span className="lbl">{t("card.elevation")}</span>
          <span className="val">
            {aerodrome.elevation_ft != null ? `${aerodrome.elevation_ft} ft` : "—"}
          </span>
        </div>
        <div>
          <span className="lbl">{t("card.runways")}</span>
          <span className="val">{runwayCount ?? "—"}</span>
        </div>
        <div>
          <span className="lbl">{t("card.notams")}</span>
          <span className="val">0</span>
        </div>
      </div>
    </Link>
  );
}
