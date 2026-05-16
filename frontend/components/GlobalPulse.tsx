"use client";

import { useEffect, useState } from "react";

export interface PulseMetric {
  key: string;
  label: string;
  value: number | string;
  unit?: string;
  delta_pct?: number;
  hint?: string;
}

interface Props {
  metrics?: PulseMetric[];
  apiUrl?: string;
}

const DEFAULT_METRICS: PulseMetric[] = [
  { key: "dxy", label: "DXY", value: 103.4, delta_pct: -0.2, hint: "USD index" },
  { key: "us10y", label: "US 10Y", value: 4.32, unit: "%", delta_pct: 0.4 },
  { key: "copper", label: "Cu Deficit", value: -8, unit: "%", delta_pct: 1.1, hint: "Supply balance" },
  { key: "lithium", label: "Li Deficit", value: -12, unit: "%", delta_pct: 0.6 },
  { key: "uranium", label: "U Deficit", value: -22, unit: "%", delta_pct: 0.9 },
];

/**
 * Global Pulse - top-row ticker (PRD v8.3 §5.1)
 * Shows DXY, 10y rate, top 3 macro deficits.
 */
export default function GlobalPulse({ metrics, apiUrl }: Props) {
  const [data, setData] = useState<PulseMetric[]>(metrics ?? DEFAULT_METRICS);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (metrics) return; // prop wins
    const api = apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const res = await fetch(`${api}/api/macro/pulse`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (mounted && Array.isArray(json.metrics)) setData(json.metrics);
      } catch {
        // silent fallback to defaults
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [metrics, apiUrl]);

  const colorFor = (d?: number) => {
    if (d === undefined) return "text-muted";
    if (d > 0) return "text-positive";
    if (d < 0) return "text-negative";
    return "text-muted";
  };

  return (
    <div className="w-full bg-surface border border-gray-200 rounded-lg px-4 py-3 flex items-center gap-6 overflow-x-auto">
      <span className="text-xs uppercase tracking-wider text-muted font-semibold whitespace-nowrap">
        Global Pulse {loading && "•"}
      </span>
      {data.map((m) => (
        <div key={m.key} className="flex flex-col min-w-[88px]" title={m.hint}>
          <span className="text-[10px] uppercase text-muted">{m.label}</span>
          <div className="flex items-baseline gap-1">
            <span className="text-lg font-semibold text-text tabular-nums">
              {typeof m.value === "number" ? m.value.toFixed(m.value % 1 === 0 ? 0 : 2) : m.value}
              {m.unit}
            </span>
            {m.delta_pct !== undefined && (
              <span className={`text-xs font-medium ${colorFor(m.delta_pct)}`}>
                {m.delta_pct > 0 ? "+" : ""}
                {m.delta_pct.toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
