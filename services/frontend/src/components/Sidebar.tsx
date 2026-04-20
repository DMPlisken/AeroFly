import { NavLink } from "react-router-dom";

import { useI18n } from "@/i18n";

export function Sidebar() {
  const { t } = useI18n();

  return (
    <aside className="sidebar">
      <NavLink to="/" className="sidebar-brand" style={{ textDecoration: "none", color: "inherit" }}>
        <span className="brand-mark">
          <i className="fa-solid fa-plane-up" />
        </span>
        <span>
          {t("brand.aero")}
          <span className="brand-accent">{t("brand.fly")}</span>
        </span>
      </NavLink>

      <div>
        <div className="sidebar-section-title">{t("nav.section.navigation")}</div>
        <div className="sidebar-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `nav-item${isActive ? " is-active" : ""}`}
          >
            <i className="fa-solid fa-grid-2" />
            <span>{t("nav.dashboard")}</span>
          </NavLink>
          <NavLink
            to="/search"
            className={({ isActive }) => `nav-item${isActive ? " is-active" : ""}`}
          >
            <i className="fa-solid fa-magnifying-glass" />
            <span>{t("nav.search")}</span>
          </NavLink>
          <span className="nav-item" aria-disabled="true" style={{ opacity: 0.5, cursor: "not-allowed" }}>
            <i className="fa-solid fa-map" />
            <span>{t("nav.charts")}</span>
          </span>
          <span className="nav-item" aria-disabled="true" style={{ opacity: 0.5, cursor: "not-allowed" }}>
            <i className="fa-solid fa-wind" />
            <span>{t("nav.weather")}</span>
          </span>
          <span className="nav-item" aria-disabled="true" style={{ opacity: 0.5, cursor: "not-allowed" }}>
            <i className="fa-solid fa-triangle-exclamation" />
            <span>{t("nav.notams")}</span>
          </span>
        </div>
      </div>

      <div>
        <div className="sidebar-section-title">{t("nav.section.system")}</div>
        <div className="sidebar-nav">
          <NavLink
            to="/usage"
            className={({ isActive }) => `nav-item${isActive ? " is-active" : ""}`}
          >
            <i className="fa-solid fa-chart-line" />
            <span>{t("nav.usage")}</span>
          </NavLink>
          <a className="nav-item" href="/api/docs" target="_blank" rel="noreferrer">
            <i className="fa-solid fa-circle-info" />
            <span>{t("nav.apiDocs")}</span>
          </a>
        </div>
      </div>

      <div className="sidebar-foot">
        <div className="avatar">D</div>
        <div style={{ fontSize: "var(--fs-sm)", lineHeight: 1.3 }}>
          <div style={{ fontWeight: 700 }}>Doron Marcu</div>
          <div style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-xs)" }}>
            {t("profile.demo")}
          </div>
        </div>
      </div>
    </aside>
  );
}
