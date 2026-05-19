import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  fetchAerodromeByIcao,
  listAerodromes,
  type Aerodrome,
} from "@/api/aerodromes";
import { AerodromeCardCompact } from "@/components/AerodromeCardCompact";
import { BulkSyncButton } from "@/components/BulkSyncButton";
import { useFavorites } from "@/hooks/useFavorites";
import { useI18n } from "@/i18n";

const FAVORITES_VISIBLE = 6;

export function Dashboard() {
  const { t } = useI18n();
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const {
    favorites,
    count: favoritesCount,
    loaded: favoritesLoaded,
  } = useFavorites();
  const [favoriteAerodromes, setFavoriteAerodromes] = useState<Aerodrome[]>([]);
  const [favoritesError, setFavoritesError] = useState<string | null>(null);

  useEffect(() => {
    listAerodromes({ limit: 1 })
      .then((res) => setTotal(res.total))
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!favoritesLoaded) return;
    if (favoritesCount === 0) {
      setFavoriteAerodromes([]);
      setFavoritesError(null);
      return;
    }
    const icaos = Array.from(favorites).sort();
    Promise.all(icaos.map(fetchAerodromeByIcao))
      .then((results) => {
        setFavoriteAerodromes(results.filter((a): a is Aerodrome => a !== null));
        setFavoritesError(null);
      })
      .catch((e) =>
        setFavoritesError(e instanceof Error ? e.message : String(e)),
      );
  }, [favoritesLoaded, favorites, favoritesCount]);

  const visibleFavorites = favoriteAerodromes.slice(0, FAVORITES_VISIBLE);
  const hiddenFavorites = favoriteAerodromes.length - visibleFavorites.length;

  return (
    <>
      <div className="page-hero">
        <div>
          <h1>{t("dashboard.welcome")}</h1>
          <p>
            <i className="fa-solid fa-plane-up" />
            {t("dashboard.subtitle")}
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-3)" }}>
          <Link to="/search" className="btn btn-primary">
            <i className="fa-solid fa-magnifying-glass" /> {t("nav.search")}
          </Link>
        </div>
      </div>

      <div className="grid-12" style={{ marginBottom: "var(--space-6)" }}>
        <div className="col-span-4 stat-card">
          <span className="stat-label">{t("dashboard.stats.aerodromes")}</span>
          <span className="stat-value">
            {error ? "—" : total === null ? "…" : total}
          </span>
          <span className="stat-trend">
            {total !== null && t("dashboard.stats.aerodromes.trend", { n: total })}
          </span>
        </div>
        <div className="col-span-4 stat-card">
          <span className="stat-label">{t("dashboard.stats.notams")}</span>
          <span className="stat-value">0</span>
          <span className="stat-trend" style={{ color: "var(--color-text-muted)" }}>
            {t("dashboard.stats.notams.trend")}
          </span>
        </div>
        <div className="col-span-4 stat-card">
          <span className="stat-label">{t("dashboard.stats.uptime")}</span>
          <span className="stat-value">100%</span>
          <span className="stat-trend">{t("dashboard.stats.uptime.trend")}</span>
        </div>
      </div>

      <div className="grid-12">
        <div className="col-span-8">
          <div className="card" style={{ marginBottom: "var(--space-4)" }}>
            <div className="card-header">
              <span className="card-title">
                {t("dashboard.section.favorites")}
                {favoritesCount > 0 && (
                  <span
                    style={{
                      marginLeft: "var(--space-2)",
                      padding: "1px 8px",
                      borderRadius: 999,
                      background: "var(--color-primary-soft)",
                      color: "var(--color-primary)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      fontWeight: 600,
                    }}
                  >
                    {favoritesCount}
                  </span>
                )}
              </span>
              <div style={{ display: "inline-flex", gap: "var(--space-2)", alignItems: "center" }}>
                <BulkSyncButton icaos={Array.from(favorites).sort()} />
                <Link to="/search?tab=favorites" className="btn btn-ghost btn-sm">
                  {t("favorites.tab.favorites")}
                </Link>
              </div>
            </div>

            {!favoritesLoaded ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-sm)", margin: 0 }}>
                {t("search.loading")}
              </p>
            ) : favoritesError ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-sm)", margin: 0 }}>
                {t("favorites.error", { message: favoritesError })}
              </p>
            ) : favoritesCount === 0 ? (
              <p
                style={{
                  color: "var(--color-text-secondary)",
                  fontSize: "var(--fs-sm)",
                  margin: 0,
                }}
              >
                {t("dashboard.favorites.empty")}
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
                {visibleFavorites.map((ad) => (
                  <AerodromeCardCompact key={ad.icao} aerodrome={ad} />
                ))}
                {hiddenFavorites > 0 && (
                  <Link
                    to="/search?tab=favorites"
                    className="btn btn-ghost btn-sm"
                    style={{ alignSelf: "flex-start", marginTop: "var(--space-2)" }}
                  >
                    {t("dashboard.favorites.more", { n: hiddenFavorites })}{" "}
                    <i className="fa-solid fa-arrow-right" aria-hidden="true" />
                  </Link>
                )}
              </div>
            )}
          </div>
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("dashboard.section.briefing")}</span>
            </div>
            <p style={{ fontSize: "var(--fs-sm)", color: "var(--color-text-secondary)" }}>
              {t("dashboard.briefing.body")}
            </p>
          </div>
        </div>

        <div className="col-span-4" style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("dashboard.section.syncStatus")}</span>
              <span className="status-pill">
                <span className="dot" />
                OK
              </span>
            </div>
            <dl className="kv-grid">
              <dt>{t("dashboard.sync.dfs")}</dt>
              <dd style={{ color: "var(--color-warning)" }}>{t("dashboard.sync.seeded")}</dd>
              <dt>{t("dashboard.sync.notams")}</dt>
              <dd style={{ color: "var(--color-text-muted)" }}>{t("dashboard.sync.idle")}</dd>
              <dt>{t("dashboard.sync.metar")}</dt>
              <dd style={{ color: "var(--color-text-muted)" }}>{t("dashboard.sync.idle")}</dd>
              <dt>{t("dashboard.sync.airac")}</dt>
              <dd>2026-04</dd>
            </dl>
          </div>
        </div>
      </div>
    </>
  );
}
