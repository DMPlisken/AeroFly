import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useI18n } from "@/i18n";

export function TopBar() {
  const { t, locale, setLocale } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [query, setQuery] = useState(() => params.get("q") ?? "");

  useEffect(() => {
    setQuery(params.get("q") ?? "");
  }, [params]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const q = query.trim();
    navigate({ pathname: "/search", search: q ? `?q=${encodeURIComponent(q)}` : "" });
  }

  return (
    <header className="topbar">
      <form className="topbar-search" onSubmit={submit} role="search">
        <i className="fa-solid fa-magnifying-glass" aria-hidden="true" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("topbar.search.placeholder")}
          aria-label={t("topbar.search.placeholder")}
        />
      </form>

      <div className="topbar-actions">
        <span className="status-pill" title={t("topbar.status.online")}>
          <span className="dot" />
          {t("topbar.status.online")}
        </span>

        <div className="lang-toggle" role="group" aria-label="Language">
          <button
            type="button"
            className={locale === "de" ? "is-active" : ""}
            onClick={() => setLocale("de")}
          >
            DE
          </button>
          <button
            type="button"
            className={locale === "en" ? "is-active" : ""}
            onClick={() => setLocale("en")}
          >
            EN
          </button>
        </div>

        <button className="icon-button" type="button" aria-label={t("topbar.notifications")}>
          <i className="fa-solid fa-bell" />
        </button>
        <button className="icon-button" type="button" aria-label={t("topbar.settings")}>
          <i className="fa-solid fa-gear" />
        </button>
      </div>
    </header>
  );
}
