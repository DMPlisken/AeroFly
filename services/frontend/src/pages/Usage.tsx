import { useEffect, useState } from "react";

import {
  getUsageRecent,
  getUsageSummary,
  type UsageCall,
  type UsageSummary,
} from "@/api/usage";
import { useI18n } from "@/i18n";

const REFRESH_MS = 10_000;

export function UsagePage() {
  const { t, locale } = useI18n();
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [recent, setRecent] = useState<UsageCall[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const [s, r] = await Promise.all([getUsageSummary(), getUsageRecent(50)]);
        if (!alive) return;
        setSummary(s);
        setRecent(r);
        setError(null);
      } catch (e: unknown) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    tick();
    const id = window.setInterval(tick, REFRESH_MS);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, []);

  if (loading && !summary) {
    return <p style={{ color: "var(--color-text-muted)" }}>{t("usage.loading")}</p>;
  }
  if (error && !summary) {
    return (
      <div className="empty-state">
        <i className="fa-solid fa-triangle-exclamation" />
        <p>{t("usage.error", { message: error })}</p>
      </div>
    );
  }
  if (!summary || !recent) return null;

  return (
    <>
      <div className="page-hero">
        <div>
          <h1>{t("usage.title")}</h1>
          <p>
            <i className="fa-solid fa-circle-dot" style={{ color: "var(--color-success)" }} />
            {t("usage.subtitle")}
          </p>
        </div>
        <span style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-xs)" }}>
          {t("usage.refreshingEvery")} · {t("usage.lastUpdated", { at: new Date(summary.generated_at).toLocaleTimeString(locale) })}
        </span>
      </div>

      <div className="grid-12" style={{ marginBottom: "var(--space-6)" }}>
        <div className="col-span-4 stat-card">
          <span className="stat-label">{t("usage.stats.calls")}</span>
          <span className="stat-value">{summary.total_calls.toLocaleString(locale)}</span>
          <span className="stat-trend">
            {summary.total_input_tokens.toLocaleString(locale)} in · {summary.total_output_tokens.toLocaleString(locale)} out
          </span>
        </div>
        <div className="col-span-4 stat-card">
          <span className="stat-label">{t("usage.stats.cost")}</span>
          <span className="stat-value">${Number(summary.total_cost_usd).toFixed(4)}</span>
          <span className="stat-trend">
            {summary.total_cached_input_tokens > 0 ? `${summary.total_cached_input_tokens.toLocaleString(locale)} cached` : "no cache hits"}
          </span>
        </div>
        <div className="col-span-4 stat-card">
          <span className="stat-label">{t("usage.stats.avgLatency")}</span>
          <span className="stat-value">{summary.avg_latency_ms.toLocaleString(locale)}<span style={{ fontSize: "var(--fs-base)", color: "var(--color-text-muted)" }}> ms</span></span>
          <span className={`stat-trend${summary.failed_calls > 0 ? " neg" : ""}`}>
            {summary.failed_calls} {t("usage.stats.failedCalls")}
          </span>
        </div>
      </div>

      <div className="grid-12" style={{ marginBottom: "var(--space-6)" }}>
        <div className="col-span-6">
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("usage.perProvider")}</span>
            </div>
            <table style={{ width: "100%", fontSize: "var(--fs-sm)" }}>
              <thead>
                <tr style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-xs)", textTransform: "uppercase" }}>
                  <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.provider")}</th>
                  <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.status")}</th>
                  <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.inputTokens")}</th>
                  <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.outputTokens")}</th>
                  <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.cost")}</th>
                </tr>
              </thead>
              <tbody>
                {summary.per_provider.map((p) => (
                  <tr key={p.provider} style={{ borderTop: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "var(--space-2)", fontWeight: 600 }}>{p.provider}</td>
                    <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)" }}>{p.calls}</td>
                    <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)" }}>{p.input_tokens.toLocaleString(locale)}</td>
                    <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)" }}>{p.output_tokens.toLocaleString(locale)}</td>
                    <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)", color: "var(--color-primary)" }}>${Number(p.total_cost_usd).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="col-span-6">
          <div className="card">
            <div className="card-header">
              <span className="card-title">{t("usage.perPurpose")}</span>
            </div>
            <table style={{ width: "100%", fontSize: "var(--fs-sm)" }}>
              <thead>
                <tr style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-xs)", textTransform: "uppercase" }}>
                  <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.purpose")}</th>
                  <th style={{ textAlign: "right", padding: "var(--space-2)" }}>Calls</th>
                  <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.cost")}</th>
                </tr>
              </thead>
              <tbody>
                {summary.per_purpose.map((p) => (
                  <tr key={p.purpose} style={{ borderTop: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "var(--space-2)", fontFamily: "var(--font-mono)" }}>{p.purpose}</td>
                    <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)" }}>{p.calls}</td>
                    <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)", color: "var(--color-primary)" }}>${Number(p.total_cost_usd).toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">{t("usage.recent")}</span>
        </div>
        {recent.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)" }}>{t("usage.empty")}</p>
        ) : (
          <table style={{ width: "100%", fontSize: "var(--fs-sm)" }}>
            <thead>
              <tr style={{ color: "var(--color-text-muted)", fontSize: "var(--fs-xs)", textTransform: "uppercase" }}>
                <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.time")}</th>
                <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.provider")}</th>
                <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.purpose")}</th>
                <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.icao")}</th>
                <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.inputTokens")}</th>
                <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.outputTokens")}</th>
                <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.cost")}</th>
                <th style={{ textAlign: "right", padding: "var(--space-2)" }}>{t("usage.col.latency")}</th>
                <th style={{ textAlign: "left", padding: "var(--space-2)" }}>{t("usage.col.status")}</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((c) => (
                <tr key={c.id} style={{ borderTop: "1px solid var(--color-border)" }}>
                  <td style={{ padding: "var(--space-2)", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                    {new Date(c.created_at).toLocaleTimeString(locale)}
                  </td>
                  <td style={{ padding: "var(--space-2)" }}>{c.provider}</td>
                  <td style={{ padding: "var(--space-2)", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>{c.purpose}</td>
                  <td style={{ padding: "var(--space-2)", fontFamily: "var(--font-mono)" }}>{c.aerodrome_icao ?? "—"}</td>
                  <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)" }}>{c.input_tokens.toLocaleString(locale)}</td>
                  <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)" }}>{c.output_tokens.toLocaleString(locale)}</td>
                  <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)", color: "var(--color-primary)" }}>${Number(c.total_cost_usd).toFixed(4)}</td>
                  <td style={{ padding: "var(--space-2)", textAlign: "right", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>{c.latency_ms ?? "—"} ms</td>
                  <td style={{ padding: "var(--space-2)" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        padding: "2px 8px",
                        borderRadius: "var(--radius-md)",
                        fontSize: "10px",
                        fontWeight: 700,
                        letterSpacing: "0.06em",
                        textTransform: "uppercase",
                        background: c.success
                          ? "rgba(16,185,129,0.18)"
                          : "rgba(239,68,68,0.18)",
                        color: c.success ? "var(--color-success)" : "var(--color-danger)",
                      }}
                    >
                      {c.success
                        ? t("usage.status.ok")
                        : `${t("usage.status.fail")}${c.error_code ? `: ${c.error_code}` : ""}`}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
