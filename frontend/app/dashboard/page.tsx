"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/apiClient";
import GlobalPulse from "@/components/GlobalPulse";
import KellyCalculator from "@/components/KellyCalculator";
import RiskCorrelationMatrix from "@/components/RiskCorrelationMatrix";
import MacroDeficitRadar from "@/components/MacroDeficitRadar";
import IntelligenceCard, {
  IntelligenceSignal,
  DebateStep,
} from "@/components/IntelligenceCard";
import ShadowPortfolio from "@/components/ShadowPortfolio";
import WatchlistStalker from "@/components/WatchlistStalker";
import SecondarySupplyChart from "@/components/SecondarySupplyChart";

// ---------------------------------------------------------------------------
// Types for dashboard summary
// ---------------------------------------------------------------------------
interface MATarget {
  asset_ticker: string;
  company_name: string;
  company_type: string;
  domicile_country: string | null;
  buyout_probability_score: number;
}
interface DilutionRisk {
  asset_ticker: string;
  company_name: string;
  company_type: string;
  domicile_country: string | null;
  dilution_risk_score: number;
}
interface ActiveDispute {
  id: string;
  asset_ticker: string;
  facility_name: string | null;
  region: string | null;
  dispute_type: string;
  severity_level: number;
  is_early_warning: boolean;
  triggered_at: string | null;
}
interface ChokepointAlert {
  id: string;
  upstream_ticker: string;
  downstream_ticker: string;
  raw_material_type: string | null;
  geopolitical_friction_cost: number;
  geo_status: string | null;
  upstream_country: string | null;
  upstream_name: string | null;
}
interface DashboardSummary {
  top_ma_targets: MATarget[];
  top_dilution_risks: DilutionRisk[];
  active_disputes: ActiveDispute[];
  chokepoint_alerts: ChokepointAlert[];
}

// ---------------------------------------------------------------------------
// God Mode Panel
// ---------------------------------------------------------------------------
function GodModePanel({ summary }: { summary: DashboardSummary }) {
  const router = useRouter();
  const go = (ticker: string) =>
    router.push(`/dashboard/nexus?upstream_ticker=${encodeURIComponent(ticker)}`);

  return (
    <section className="mb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">&#x26A1;</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-muted">
          God Mode Intelligence
        </h2>
        <span className="ml-auto text-[10px] text-muted">Sprint 17 · live data</span>
      </div>

      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">

        {/* Top M&A Targets */}
        <div className="bg-surface border border-amber-600/40 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-1.5 mb-3">
            <span className="text-base">💰</span>
            <span className="text-xs font-bold text-amber-500 uppercase tracking-wide">Top M&amp;A Targets</span>
          </div>
          {summary.top_ma_targets.length === 0 ? (
            <p className="text-xs text-muted text-center py-4">Run M&amp;A Predictor sweep first</p>
          ) : (
            <ol className="space-y-2">
              {summary.top_ma_targets.map((t, i) => (
                <li
                  key={t.asset_ticker}
                  className="flex items-center justify-between gap-2 cursor-pointer hover:bg-amber-900/10 rounded-lg px-1 py-0.5 transition-colors"
                  onClick={() => go(t.asset_ticker)}
                >
                  <span className="flex items-center gap-1.5 min-w-0">
                    <span className="text-[10px] text-amber-600 font-bold w-4 shrink-0">{i + 1}.</span>
                    <span className="text-xs font-semibold text-text truncate">{t.asset_ticker}</span>
                    {t.domicile_country && (
                      <span className="text-[10px] text-muted">{t.domicile_country}</span>
                    )}
                  </span>
                  <span
                    className="text-xs font-bold shrink-0"
                    style={{ color: t.buyout_probability_score > 75 ? "#d97706" : "#9ca3af" }}
                  >
                    {Math.round(t.buyout_probability_score)}%
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>

        {/* Critical Dilution Risks */}
        <div className="bg-surface border border-red-600/40 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-1.5 mb-3">
            <span className="text-base">⚠️</span>
            <span className="text-xs font-bold text-red-500 uppercase tracking-wide">Critical Dilution Risks</span>
          </div>
          {summary.top_dilution_risks.length === 0 ? (
            <p className="text-xs text-muted text-center py-4">No dilution scores yet</p>
          ) : (
            <ol className="space-y-2">
              {summary.top_dilution_risks.map((d, i) => (
                <li
                  key={d.asset_ticker}
                  className="flex items-center justify-between gap-2 cursor-pointer hover:bg-red-900/10 rounded-lg px-1 py-0.5 transition-colors"
                  onClick={() => go(d.asset_ticker)}
                >
                  <span className="flex items-center gap-1.5 min-w-0">
                    <span className="text-[10px] text-red-600 font-bold w-4 shrink-0">{i + 1}.</span>
                    <span className="text-xs font-semibold text-text truncate">{d.asset_ticker}</span>
                    {d.domicile_country && (
                      <span className="text-[10px] text-muted">{d.domicile_country}</span>
                    )}
                  </span>
                  <span
                    className="text-xs font-bold shrink-0"
                    style={{ color: d.dilution_risk_score > 75 ? "#ef4444" : d.dilution_risk_score > 50 ? "#f59e0b" : "#9ca3af" }}
                  >
                    {Math.round(d.dilution_risk_score)}%
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>

        {/* Active Labour Disputes */}
        <div className="bg-surface border border-red-800/40 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-1.5 mb-3">
            <span className="text-base">🚨</span>
            <span className="text-xs font-bold text-red-400 uppercase tracking-wide">Active Disputes</span>
          </div>
          {summary.active_disputes.length === 0 ? (
            <p className="text-xs text-muted text-center py-4">No active disputes</p>
          ) : (
            <ul className="space-y-2">
              {summary.active_disputes.map((d) => (
                <li
                  key={d.id}
                  className="flex items-start justify-between gap-2 cursor-pointer hover:bg-red-900/10 rounded-lg px-1 py-0.5 transition-colors"
                  onClick={() => go(d.asset_ticker)}
                >
                  <span className="min-w-0">
                    <span className="text-xs font-semibold text-text block truncate">{d.asset_ticker}</span>
                    <span className="text-[10px] text-muted block truncate">
                      {d.facility_name || d.region || d.dispute_type}
                    </span>
                  </span>
                  <span className="flex flex-col items-end shrink-0 gap-0.5">
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                      style={{
                        background: d.severity_level >= 4 ? "#7f1d1d" : d.severity_level >= 2 ? "#78350f" : "#1f2937",
                        color: d.severity_level >= 4 ? "#fca5a5" : d.severity_level >= 2 ? "#fcd34d" : "#9ca3af",
                      }}
                    >
                      S{d.severity_level}
                    </span>
                    {d.is_early_warning && (
                      <span className="text-[9px] text-cyan-400">📡 early</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Chokepoint Alerts */}
        <div className="bg-surface border border-orange-600/40 rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-1.5 mb-3">
            <span className="text-base">🚢</span>
            <span className="text-xs font-bold text-orange-400 uppercase tracking-wide">Chokepoint Alerts</span>
          </div>
          {summary.chokepoint_alerts.length === 0 ? (
            <p className="text-xs text-muted text-center py-4">No active friction</p>
          ) : (
            <ul className="space-y-2">
              {summary.chokepoint_alerts.slice(0, 5).map((c) => (
                <li
                  key={c.id}
                  className="flex items-start justify-between gap-2 cursor-pointer hover:bg-orange-900/10 rounded-lg px-1 py-0.5 transition-colors"
                  onClick={() => go(c.upstream_ticker)}
                >
                  <span className="min-w-0">
                    <span className="text-xs font-semibold text-text block">
                      {c.upstream_ticker} → {c.downstream_ticker}
                    </span>
                    <span className="text-[10px] text-muted block">
                      {c.raw_material_type || ""}{c.upstream_country ? ` · ${c.upstream_country}` : ""}
                    </span>
                  </span>
                  <span className="text-xs font-bold text-orange-400 shrink-0">
                    +{(c.geopolitical_friction_cost * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

      </div>
    </section>
  );
}

/**
 * Command Center - Bento Box (PRD v8.3 §5)
 *
 * Grid layout:
 *   ┌────────────────────────────────────────────────────────────────┐
 *   │                    Global Pulse (full width)                    │
 *   ├──────────────┬─────────────────────────────────┬───────────────┤
 *   │ Shadow       │  Intelligence Cards (feed)      │ Macro Deficit │
 *   │ Portfolio    │                                 │ Radar         │
 *   │              │                                 │               │
 *   ├──────────────┤                                 ├───────────────┤
 *   │ Kelly        │                                 │ Risk Corr     │
 *   │ Calculator   │                                 │ Matrix        │
 *   └──────────────┴─────────────────────────────────┴───────────────┘
 */
export default function DashboardPage() {
  const [signals, setSignals] = useState<IntelligenceSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [sigRes, sumRes] = await Promise.all([
          apiFetch(`${apiUrl}/api/intelligence/signals?limit=20`),
          apiFetch(`${apiUrl}/api/dashboard/summary`),
        ]);
        if (!sigRes.ok) throw new Error(`Signals HTTP ${sigRes.status}`);
        const json = await sigRes.json();
        if (mounted) setSignals(json.signals || []);
        if (sumRes.ok && mounted) setSummary(await sumRes.json());
      } catch (e) {
        console.error("Failed to load dashboard", e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [apiUrl]);

  const loadDebate = async (assetId: string): Promise<DebateStep[]> => {
    try {
      const res = await fetch(
        `${apiUrl}/api/intelligence/debate/${encodeURIComponent(assetId)}`
      );
      if (!res.ok) return [];
      const json = await res.json();
      return (json.debate_log || []) as DebateStep[];
    } catch {
      return [];
    }
  };

  return (
    <main className="min-h-screen bg-bg text-text p-4 md:p-6">
      {/* Header */}
      <header className="mb-4 flex items-baseline justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Mineral AI Command Center</h1>
          <p className="text-xs text-muted">PRD v8.3 · Sequential Multi-SLM · 06:00 daily sweep</p>
        </div>
      </header>

      {/* God Mode Intelligence Panel */}
      {summary && <GodModePanel summary={summary} />}
      {!summary && !loading && (
        <div className="mb-6 text-xs text-muted">God Mode data unavailable — ensure backend is running.</div>
      )}

      {/* Bento Box grid */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-12 lg:grid-rows-[auto_auto_auto] auto-rows-min">
        {/* Row 1: Global Pulse (full width) */}
        <div className="lg:col-span-12">
          <GlobalPulse />
        </div>

        {/* Row 2-3 Left column: Stalker + Shadow Portfolio + Kelly */}
        <div className="lg:col-span-3 lg:row-span-2 flex flex-col gap-4">
          <WatchlistStalker />
          <ShadowPortfolio />
          <KellyCalculator />
        </div>

        {/* Row 2-3 Center: Intelligence feed */}
        <div className="lg:col-span-6 lg:row-span-2">
          <div className="bg-surface border border-gray-200 rounded-lg p-5 h-full">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-semibold text-text uppercase tracking-wider">
                Intelligence Signals
              </h3>
              <span className="text-[10px] text-muted">
                {loading ? "Loading..." : `${signals.length} signals`}
              </span>
            </div>
            <div className="space-y-3 max-h-[820px] overflow-y-auto pr-1">
              {loading && (
                <p className="text-sm text-muted text-center py-8">
                  Waiting for Multi-SLM debate...
                </p>
              )}
              {!loading && signals.length === 0 && (
                <p className="text-sm text-muted text-center py-8">
                  No signals yet. Wait for 06:00 sweep or POST to{" "}
                  <code>/api/intelligence/analyze</code>.
                </p>
              )}
              {signals.map((s) => (
                <IntelligenceCard
                  key={`${s.asset_id}-${s.created_at}`}
                  signal={s}
                  onLoadDebate={loadDebate}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Row 2-3 Right column: Macro Radar + Risk Matrix */}
        <div className="lg:col-span-3 lg:row-span-2 flex flex-col gap-4">
          <MacroDeficitRadar />
          <RiskCorrelationMatrix />
        </div>

        {/* Row 4: Secondary Supply Pressure — full width */}
        <div className="lg:col-span-12">
          <SecondarySupplyChart />
        </div>
      </div>
    </main>
  );
}
