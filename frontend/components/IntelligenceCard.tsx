"use client";

import { useState, useCallback } from "react";
import LiveTicker, { LiveQuote } from "./LiveTicker";

const DRIFT_THRESHOLD_PCT = 5;
// PRD v8.6 Phase 8: only attach LiveTicker when the asset_id is a recognizable
// Yahoo-style ticker. Examples that match: AAPL, BOL.ST, RIO.L, BHP.AX, BMW.DE.
// Examples that DON'T match (and so won't spam the quote endpoint): generic
// nightly-sweep IDs like "sig_1731453200" or free-form discovery names.
const TICKER_REGEX = /^[A-Z0-9]{1,6}(\.[A-Z]{1,3})?$/;

export interface DebateStep {
  slm: string;
  timestamp: string;
  reasoning: string;
  confidence: number;
  output_data?: Record<string, any>;
}

export interface IntelligenceSignal {
  asset_id: string;
  signal_type: "BUY" | "SELL" | "HOLD" | "SHORT" | string;
  confidence_score: number;
  recommendation: string;
  consensus_score: number;
  pydantic_passed: boolean;
  source: string;
  created_at?: string;
  debate_log?: DebateStep[];
  /** Optional Yahoo ticker for live drift monitoring (PRD v8.6). */
  ticker_symbol?: string;
  /** Optional analysis-time close price - the anchor for drift alerts. */
  anchor_price?: number;
}

interface Props {
  // Either a full signal payload or a bare asset_id (the latter renders a
  // placeholder until upstream wires real signal data).
  signal?: IntelligenceSignal;
  asset_id?: string;
  onLoadDebate?: (assetId: string) => Promise<DebateStep[]>;
}

const signalColor = (type: string) => {
  switch (type.toUpperCase()) {
    case "BUY":
      return "bg-[#4F8A8B] text-white";
    case "SELL":
    case "SHORT":
      return "bg-[#B35A44] text-white";
    case "HOLD":
      return "bg-gray-400 text-white";
    default:
      return "bg-gray-300 text-gray-800";
  }
};

const confidenceColor = (score: number) => {
  if (score >= 85) return "text-[#4F8A8B]";
  if (score >= 70) return "text-yellow-600";
  return "text-[#B35A44]";
};

export default function IntelligenceCard({ signal, asset_id, onLoadDebate }: Props) {
  // Hooks must be declared unconditionally before any early return to satisfy
  // React's Rules of Hooks. We guard reads against `signal` being undefined.
  const [expanded, setExpanded] = useState(false);
  const [debateLog, setDebateLog] = useState<DebateStep[]>(signal?.debate_log || []);
  const [loading, setLoading] = useState(false);
  const [drift, setDrift] = useState<number | null>(null);

  const anchorPrice = signal?.anchor_price;
  const handleQuote = useCallback(
    (q: LiveQuote) => {
      if (!anchorPrice || !q.price) {
        setDrift(null);
        return;
      }
      const pct = ((q.price - anchorPrice) / anchorPrice) * 100;
      setDrift(pct);
    },
    [anchorPrice]
  );

  // Placeholder render when only an asset_id is supplied (no signal yet).
  // Keeps callers like `app/assets/[ticker]/page.tsx` type-clean without
  // forcing them to fabricate a fake signal. Declared AFTER all hooks to
  // comply with React's Rules of Hooks.
  if (!signal) {
    return (
      <div className="text-sm text-gray-500 italic">
        {asset_id
          ? `No AI analysis available yet for ${asset_id}.`
          : "No signal available."}
      </div>
    );
  }

  // PRD v8.6 Phase 8: prefer explicit ticker_symbol; otherwise derive from
  // asset_id only when it actually looks like a Yahoo ticker. Avoids spamming
  // the proxy with nightly-sweep ids like "sig_1731453200".
  const candidateTicker = signal.ticker_symbol || signal.asset_id || "";
  const liveTicker = TICKER_REGEX.test(candidateTicker) ? candidateTicker : null;

  const driftAlert =
    drift !== null && Math.abs(drift) >= DRIFT_THRESHOLD_PCT
      ? {
          color: drift < 0 ? "bg-[#B35A44] text-white" : "bg-[#C9A24E] text-white",
          label: `Drift Alert ${drift > 0 ? "+" : ""}${drift.toFixed(1)}%`,
        }
      : null;

  const handleToggle = async () => {
    const next = !expanded;
    setExpanded(next);
    if (next && debateLog.length === 0 && onLoadDebate) {
      try {
        setLoading(true);
        const log = await onLoadDebate(signal.asset_id);
        setDebateLog(log || []);
      } catch (e) {
        console.error("Failed to load debate log", e);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-5 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${signalColor(signal.signal_type)}`}>
              {signal.signal_type}
            </span>
            {signal.pydantic_passed ? (
              <span className="text-xs text-[#4F8A8B]">Pydantic OK</span>
            ) : (
              <span className="text-xs text-[#B35A44]">Pydantic FAIL</span>
            )}
            {driftAlert && (
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${driftAlert.color}`}
                title="Signal may be stale - price drifted significantly since analysis."
              >
                {driftAlert.label}
              </span>
            )}
          </div>
          <h3 className="text-lg font-semibold text-[#2F2F2F] flex items-center gap-2">
            {signal.asset_id}
            {liveTicker && (
              <LiveTicker
                ticker={liveTicker}
                compact
                anchorPrice={signal.anchor_price}
                onQuote={handleQuote}
              />
            )}
          </h3>
          <p className="text-xs text-gray-500">
            {signal.source}
            {signal.created_at && ` • ${new Date(signal.created_at).toLocaleString()}`}
          </p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-bold ${confidenceColor(signal.confidence_score)}`}>
            {signal.confidence_score}
          </div>
          <div className="text-xs text-gray-500">Confidence</div>
        </div>
      </div>

      {/* AI Insight */}
      <div className="bg-[#F4F1EE] rounded-md p-3 mb-3">
        <div className="text-xs uppercase font-semibold text-gray-500 mb-1">AI Insight</div>
        <p className="text-sm text-[#2F2F2F]">{signal.recommendation}</p>
      </div>

      {/* Consensus bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>SLM Consensus</span>
          <span>{Math.round(signal.consensus_score * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#4F8A8B] transition-all"
            style={{ width: `${Math.round(signal.consensus_score * 100)}%` }}
          />
        </div>
      </div>

      {/* Debate log toggle */}
      <button
        onClick={handleToggle}
        className="w-full text-sm text-[#4F8A8B] font-medium hover:underline flex items-center justify-center gap-1"
      >
        {expanded ? "Hide" : "Show"} Debate Log
        <span className={`transition-transform ${expanded ? "rotate-180" : ""}`}>▼</span>
      </button>

      {expanded && (
        <div className="mt-3 space-y-2 border-t pt-3">
          {loading && <p className="text-sm text-gray-500">Loading debate log...</p>}
          {!loading && debateLog.length === 0 && (
            <p className="text-sm text-gray-500">No debate log available.</p>
          )}
          {debateLog.map((step, i) => (
            <div key={i} className="bg-gray-50 rounded p-3 text-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold text-[#2F2F2F]">{step.slm.toUpperCase()}</span>
                <span className={`font-bold ${confidenceColor(step.confidence)}`}>
                  {step.confidence}
                </span>
              </div>
              <p className="text-gray-700 text-xs">{step.reasoning}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
