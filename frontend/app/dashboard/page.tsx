"use client";

import { useEffect, useState } from "react";
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

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiFetch(`${apiUrl}/api/intelligence/signals?limit=20`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (mounted) setSignals(json.signals || []);
      } catch (e) {
        console.error("Failed to load signals", e);
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
      </div>
    </main>
  );
}
