import { Link } from "react-router-dom";

import { useI18n } from "@/i18n";

export function NotFound() {
  const { t } = useI18n();
  return (
    <div className="empty-state">
      <i className="fa-solid fa-compass" />
      <h4>{t("notFound.title")}</h4>
      <p>{t("notFound.body")}</p>
      <Link to="/" className="btn btn-secondary">
        {t("notFound.back")}
      </Link>
    </div>
  );
}
