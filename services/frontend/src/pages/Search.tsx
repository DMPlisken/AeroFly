import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  searchAerodromes,
  type AerodromeSearchHit,
  type AerodromeType,
} from "@/api/aerodromes";
import { AerodromeCard } from "@/components/AerodromeCard";
import { useDebounce } from "@/hooks/useDebounce";
import { useI18n } from "@/i18n";

const LIMIT = 24;
const SEARCH_DEBOUNCE_MS = 250;

function paginationWindow(current: number, total: number): (number | "ellipsis")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i);
  const out: (number | "ellipsis")[] = [0];
  const start = Math.max(1, current - 1);
  const end = Math.min(total - 2, current + 1);
  if (start > 1) out.push("ellipsis");
  for (let i = start; i <= end; i++) out.push(i);
  if (end < total - 2) out.push("ellipsis");
  out.push(total - 1);
  return out;
}
const TYPES: (AerodromeType | "")[] = [
  "",
  "international",
  "regional",
  "general_aviation",
  "military",
  "private",
  "other",
];

export function SearchPage() {
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();

  const urlQ = params.get("q") ?? "";
  const type = (params.get("type") ?? "") as AerodromeType | "";
  const offset = Number(params.get("offset") ?? 0);

  // Local input state — typed character-by-character. Debounced version drives
  // the actual API call and syncs back into the URL once stable.
  const [inputQ, setInputQ] = useState(urlQ);
  const debouncedQ = useDebounce(inputQ, SEARCH_DEBOUNCE_MS);

  // If the URL is changed externally (back/forward, deep link, clear), reflect
  // that in the input.
  useEffect(() => {
    setInputQ(urlQ);
  }, [urlQ]);

  // Push debounced search term back into the URL — but only if it differs.
  useEffect(() => {
    if (debouncedQ === urlQ) return;
    const p = new URLSearchParams(params);
    if (debouncedQ) p.set("q", debouncedQ);
    else p.delete("q");
    p.delete("offset");
    setParams(p, { replace: true });
    // setParams is stable, params is captured at call time intentionally
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  const [items, setItems] = useState<AerodromeSearchHit[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    searchAerodromes({
      q: debouncedQ || undefined,
      type: type || undefined,
      limit: LIMIT,
      offset,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [debouncedQ, type, offset]);

  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + items.length, total);
  const page = Math.floor(offset / LIMIT);
  const totalPages = Math.max(1, Math.ceil(total / LIMIT));

  function update(next: Partial<{ type: string; offset: number }>) {
    const p = new URLSearchParams(params);
    if (next.type !== undefined) {
      if (next.type) p.set("type", next.type);
      else p.delete("type");
    }
    if (next.offset !== undefined) {
      if (next.offset > 0) p.set("offset", String(next.offset));
      else p.delete("offset");
    }
    setParams(p);
  }

  return (
    <>
      <div className="page-hero">
        <div>
          <h1>{t("search.title")}</h1>
          <p>
            <i className="fa-solid fa-database" />
            {t("search.subtitle", { total, from, to })}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-6)", flexWrap: "wrap" }}>
        <input
          className="input"
          style={{ maxWidth: 420 }}
          placeholder={t("search.input.placeholder")}
          value={inputQ}
          onChange={(e) => setInputQ(e.target.value)}
        />
        <select
          className="input"
          style={{ maxWidth: 220 }}
          value={type}
          onChange={(e) => update({ type: e.target.value, offset: 0 })}
          aria-label={t("search.filter.type")}
        >
          {TYPES.map((ty) => (
            <option key={ty || "all"} value={ty}>
              {ty
                ? t(`search.filter.type.${ty}` as const)
                : t("search.filter.type.all")}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <p style={{ color: "var(--color-text-muted)" }}>{t("search.loading")}</p>
      ) : error ? (
        <div className="empty-state">
          <i className="fa-solid fa-triangle-exclamation" />
          <p>{t("search.error", { message: error })}</p>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <i className="fa-solid fa-plane-slash" />
          <h4>{t("search.empty.title")}</h4>
          <p>{t("search.empty.body")}</p>
          <button className="btn btn-secondary" onClick={() => setParams(new URLSearchParams())}>
            {t("search.empty.clear")}
          </button>
        </div>
      ) : (
        <>
          <div className="results-grid">
            {items.map((ad) => (
              <AerodromeCard key={ad.icao} aerodrome={ad} matchType={ad.match_type} />
            ))}
          </div>

          {totalPages > 1 && (
            <div
              style={{
                marginTop: "var(--space-6)",
                display: "flex",
                justifyContent: "center",
              }}
            >
              <div className="pagination">
                <button
                  disabled={offset <= 0}
                  onClick={() => update({ offset: Math.max(0, offset - LIMIT) })}
                >
                  <i className="fa-solid fa-chevron-left" />
                </button>
                {paginationWindow(page, totalPages).map((entry, i) =>
                  entry === "ellipsis" ? (
                    <span
                      key={`e${i}`}
                      style={{ padding: "0 var(--space-2)", color: "var(--color-text-muted)" }}
                    >
                      …
                    </span>
                  ) : (
                    <button
                      key={entry}
                      className={entry === page ? "is-active" : ""}
                      onClick={() => update({ offset: entry * LIMIT })}
                    >
                      {entry + 1}
                    </button>
                  ),
                )}
                <button
                  disabled={offset + items.length >= total}
                  onClick={() => update({ offset: offset + LIMIT })}
                >
                  <i className="fa-solid fa-chevron-right" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
