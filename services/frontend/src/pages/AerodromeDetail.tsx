import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  getAerodrome,
  type AerodromeDetail as AerodromeDetailType,
} from "@/api/aerodromes";
import { FrequencyBadge } from "@/components/FrequencyBadge";
import { useI18n, type Locale } from "@/i18n";

function ilsLabel(
  t: (k: any, v?: any) => string,
  locale: Locale,
  le: boolean,
  he: boolean,
  leDes: string,
  heDes: string,
): string {
  void locale;
  if (le && he) return t("detail.runway.ilsBoth");
  if (le) return t("detail.runway.ilsLe", { le: leDes });
  if (he) return t("detail.runway.ilsLe", { le: heDes });
  return t("detail.runway.ilsNone");
}

export function AerodromeDetailPage() {
  const { t, locale } = useI18n();
  const { icao = "" } = useParams();
  const [data, setData] = useState<AerodromeDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getAerodrome(icao.toUpperCase())
      .then((res) => setData(res))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [icao]);

  if (loading) {
    return <p style={{ color: "var(--color-text-muted)" }}>{t("detail.loading")}</p>;
  }

  if (error && error.startsWith("404")) {
    return (
      <div className="empty-state">
        <i className="fa-solid fa-plane-slash" />
        <h4>{t("detail.notFound.title")}</h4>
        <p>{t("detail.notFound.body")}</p>
        <Link to="/search" className="btn btn-secondary">
          {t("detail.notFound.back")}
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <i className="fa-solid fa-triangle-exclamation" />
        <p>{t("detail.error", { message: error })}</p>
      </div>
    );
  }

  if (!data) return null;

  const name = locale === "de" && data.name_de ? data.name_de : data.name;
  const region = locale === "de" && data.region_de ? data.region_de : data.region;
  const city = locale === "de" && data.city_de ? data.city_de : data.city;

  const coords =
    data.latitude != null && data.longitude != null
      ? `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`
      : "—";

  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">{t("detail.breadcrumb.home")}</Link>
        <span className="sep">/</span>
        <Link to="/search">{t("detail.breadcrumb.search")}</Link>
        <span className="sep">/</span>
        <span className="current">{data.icao}</span>
      </nav>

      <div className="page-hero">
        <div>
          <h1>
            {data.icao}{" "}
            <span style={{ color: "var(--color-text-muted)", fontWeight: 300 }}>/</span> {name}
          </h1>
          <p>
            <i className="fa-solid fa-location-dot" />
            {[city, region, "Germany"].filter(Boolean).join(" · ")}
          </p>
        </div>
      </div>

      <div className="grid-12">
        <div className="col-span-8" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("detail.section.runways")}</span>
            </div>
            {data.runways.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>—</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--fs-sm)" }}>
                <thead>
                  <tr style={{ textAlign: "left", color: "var(--color-text-muted)", fontSize: "var(--fs-xs)" }}>
                    <th style={{ padding: "var(--space-2) var(--space-3)" }}>{t("detail.runway.designator")}</th>
                    <th style={{ padding: "var(--space-2) var(--space-3)" }}>{t("detail.runway.length")}</th>
                    <th style={{ padding: "var(--space-2) var(--space-3)" }}>{t("detail.runway.width")}</th>
                    <th style={{ padding: "var(--space-2) var(--space-3)" }}>{t("detail.runway.surface")}</th>
                    <th style={{ padding: "var(--space-2) var(--space-3)" }}>{t("detail.runway.ils")}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.runways.map((r) => (
                    <tr key={r.id} style={{ borderTop: "1px solid var(--color-border)" }}>
                      <td className="mono" style={{ padding: "var(--space-3)", color: "var(--color-primary)", fontWeight: 700 }}>
                        {r.designator_le} / {r.designator_he}
                      </td>
                      <td className="mono" style={{ padding: "var(--space-3)" }}>
                        {r.length_m != null ? `${r.length_m} m` : "—"}
                      </td>
                      <td className="mono" style={{ padding: "var(--space-3)" }}>
                        {r.width_m != null ? `${r.width_m} m` : "—"}
                      </td>
                      <td style={{ padding: "var(--space-3)" }}>
                        {t(`surface.${r.surface}` as const)}
                      </td>
                      <td style={{ padding: "var(--space-3)" }}>
                        {ilsLabel(t, locale, r.ils_le, r.ils_he, r.designator_le, r.designator_he)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("detail.section.frequencies")}</span>
            </div>
            {data.frequencies.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>—</p>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
                {data.frequencies.map((f) => (
                  <FrequencyBadge key={f.id} type={f.type} value={f.frequency_mhz} />
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("detail.section.charts")}</span>
            </div>
            <p style={{ color: "var(--color-text-muted)" }}>{t("detail.empty.charts")}</p>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("detail.section.notams")}</span>
            </div>
            <p style={{ color: "var(--color-text-muted)" }}>{t("detail.empty.notams")}</p>
          </div>
        </div>

        <div className="col-span-4">
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("detail.section.info")}</span>
            </div>
            <dl className="kv-grid">
              <dt>{t("detail.info.icao")}</dt>
              <dd>{data.icao}</dd>
              <dt>{t("detail.info.iata")}</dt>
              <dd>{data.iata ?? "—"}</dd>
              <dt>{t("detail.info.country")}</dt>
              <dd>{data.country}</dd>
              <dt>{t("detail.info.region")}</dt>
              <dd style={{ fontFamily: "var(--font-sans)" }}>{region ?? "—"}</dd>
              <dt>{t("detail.info.city")}</dt>
              <dd style={{ fontFamily: "var(--font-sans)" }}>{city ?? "—"}</dd>
              <dt>{t("detail.info.coords")}</dt>
              <dd>{coords}</dd>
              <dt>{t("detail.info.elevation")}</dt>
              <dd>{data.elevation_ft != null ? `${data.elevation_ft} ft` : "—"}</dd>
              <dt>{t("detail.info.type")}</dt>
              <dd style={{ fontFamily: "var(--font-sans)" }}>
                {t(`search.filter.type.${data.type}` as const)}
              </dd>
              <dt>{t("detail.info.airac")}</dt>
              <dd>{data.source_airac_cycle ?? "—"}</dd>
            </dl>
          </div>
        </div>
      </div>
    </>
  );
}
