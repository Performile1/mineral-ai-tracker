"use client";

import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "@/lib/apiClient";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Conviction {
  ticker: string;
  signal_type: string;
  signal_label: string;
  node_count: number;
  avg_confidence: number;
  last_seen: string | null;
}

interface ApiResponse {
  convictions: Conviction[];
  as_of: string;
  source: "db" | "mock";
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const SIGNAL_ICONS: Record<string, string> = {
  dilution_risk: "⚠️",
  ma_radar: "💰",
  scrap_surge: "♻️",
  early_sentiment: "📡",
  chokepoint: "🚢",
};

function heatColor(nodeCount: number): string {
  if (nodeCount >= 7) return "#f0abfc"; // fuchsia-300
  if (nodeCount >= 4) return "#e879f9"; // fuchsia-400
  return "#d946ef";                     // fuchsia-500
}

function fmtRelative(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just nu";
  if (mins < 60) return `${mins}m sedan`;
  return `${Math.floor(mins / 60)}h sedan`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
const POLL_INTERVAL_MS = 60_000; // refresh every 60 s

export default function HiveMindPulse() {
  const [convictions, setConvictions] = useState<Conviction[]>([]);
  const [source, setSource] = useState<"db" | "mock" | null>(null);
  const [asOf, setAsOf] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiFetch("/api/pulse/top-convictions")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<ApiResponse>;
      })
      .then((data) => {
        setConvictions(data.convictions);
        setSource(data.source);
        setAsOf(data.as_of);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div
      className="rounded-xl p-4 shadow-lg border"
      style={{
        background: "linear-gradient(135deg, #2d0036 0%, #4a044e 60%, #1e0020 100%)",
        borderColor: "#7e22ce",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-base">🧠</span>
          <h3
            className="text-xs font-bold uppercase tracking-widest"
            style={{ color: "#e879f9" }}
          >
            Hive Mind
          </h3>
          {convictions.length > 0 && (
            <span
              className="px-1.5 py-0.5 rounded text-[10px] font-bold"
              style={{ background: "#581c87", color: "#f0abfc", border: "1px solid #7e22ce" }}
            >
              {convictions.reduce((s, c) => s + c.node_count, 0)} noder aktiva
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {source === "mock" && (
            <span
              className="text-[10px] rounded px-1.5 py-0.5"
              style={{ color: "#c084fc", border: "1px solid #6b21a8" }}
            >
              demo
            </span>
          )}
          {source === "db" && (
            <span
              className="text-[10px] rounded px-1.5 py-0.5"
              style={{ color: "#86efac", border: "1px solid #166534" }}
            >
              live
            </span>
          )}
          <span className="text-[10px]" style={{ color: "#9f4fb5" }}>
            24h · 60s poll
          </span>
        </div>
      </div>

      <p className="text-[10px] mb-3 ml-6" style={{ color: "#9f4fb5" }}>
        Anonyma övertygelser från nätverket — extern data
      </p>

      {loading && (
        <div
          className="flex items-center justify-center h-32 text-sm"
          style={{ color: "#c084fc" }}
        >
          Ansluter till nätverket…
        </div>
      )}

      {error && (
        <div className="flex items-center justify-center h-32 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && convictions.length === 0 && (
        <div
          className="flex items-center justify-center h-32 text-xs"
          style={{ color: "#9f4fb5" }}
        >
          Inga nätverkssignaler ännu — var den första att bidra
        </div>
      )}

      {!loading && !error && convictions.length > 0 && (
        <ul className="space-y-2">
          {convictions.map((c, i) => {
            const icon = SIGNAL_ICONS[c.signal_type] ?? "🔍";
            const heat = heatColor(c.node_count);
            return (
              <li
                key={`${c.ticker}-${c.signal_type}`}
                className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5"
                style={{ background: "rgba(126,34,206,0.15)", border: "1px solid rgba(126,34,206,0.3)" }}
              >
                <span className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[10px]" style={{ color: "#9f4fb5" }}>
                    {i + 1}.
                  </span>
                  <span className="text-xs shrink-0">{icon}</span>
                  <span className="text-xs font-bold shrink-0" style={{ color: heat }}>
                    {c.node_count}
                  </span>
                  <span className="text-xs" style={{ color: "#d8b4fe" }}>
                    noder flaggar{" "}
                    <span style={{ color: "#e879f9" }}>{c.signal_label}</span>
                    {" på "}
                    <span className="font-bold" style={{ color: "#f0abfc" }}>
                      {c.ticker}
                    </span>
                  </span>
                </span>
                <div className="flex flex-col items-end shrink-0 gap-0.5">
                  <span className="text-[10px] font-bold" style={{ color: heat }}>
                    {c.avg_confidence.toFixed(0)}%
                  </span>
                  {c.last_seen && (
                    <span className="text-[9px]" style={{ color: "#7e22ce" }}>
                      {fmtRelative(c.last_seen)}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
