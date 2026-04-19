import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listAerodromes } from "@/api/aerodromes";
import { useI18n } from "@/i18n";

export function Dashboard() {
  const { t } = useI18n();
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAerodromes({ limit: 1 })
      .then((res) => setTotal(res.total))
      .catch((e) => setError(e.message));
  }, []);

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
              <span className="card-title">{t("dashboard.section.favorites")}</span>
              <Link to="/search" className="btn btn-ghost btn-sm">
                {t("nav.search")}
              </Link>
            </div>
            <p style={{ color: "var(--color-text-secondary)", fontSize: "var(--fs-sm)", margin: 0 }}>
              {t("dashboard.favorites.empty")}
            </p>
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
