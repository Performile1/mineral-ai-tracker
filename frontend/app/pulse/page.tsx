"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/apiClient";

interface ConvictionSignal {
  id: string;
  asset_id: string;
  ticker: string;
  signal_type: string;
  confidence_score: number;
  recommendation: string;
  consensus_score: number;
  created_at: string;
}

interface CreditsInfo {
  credits_remaining: number;
  credits_used: number;
  as_of: string;
}

export default function PulsePage() {
  const [convictions, setConvictions] = useState<ConvictionSignal[]>([]);
  const [credits, setCredits] = useState<CreditsInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        // Fetch convictions
        const convictionsRes = await apiFetch(`${apiUrl}/api/pulse/convictions`);
        if (!convictionsRes.ok) throw new Error(`HTTP ${convictionsRes.status}`);
        const convictionsJson = await convictionsRes.json();
        if (mounted) setConvictions(convictionsJson.signals || []);

        // Fetch credits
        const creditsRes = await apiFetch(`${apiUrl}/api/pulse/credits`);
        if (!creditsRes.ok) throw new Error(`HTTP ${creditsRes.status}`);
        const creditsJson = await creditsRes.json();
        if (mounted) setCredits(creditsJson);
      } catch (e) {
        console.error("Failed to load pulse data", e);
        if (mounted) setError("Failed to load data");
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [apiUrl]);

  const getConfidenceColor = (score: number) => {
    if (score >= 90) return "text-green-500";
    if (score >= 80) return "text-yellow-500";
    return "text-gray-500";
  };

  const getConfidenceBg = (score: number) => {
    if (score >= 90) return "bg-green-500";
    if (score >= 80) return "bg-yellow-500";
    return "bg-gray-500";
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMins = Math.floor(diffMs / (1000 * 60));

    if (diffHrs > 24) {
      return `${Math.floor(diffHrs / 24)} days ago`;
    } else if (diffHrs > 0) {
      return `${diffHrs}h ago`;
    } else if (diffMins > 0) {
      return `${diffMins}m ago`;
    } else {
      return "Just now";
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    setError(null);
    // Reload the page to refresh data
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-4xl font-bold mb-8">Hive Mind Global Pulse</h1>
          <div className="text-gray-400">Loading...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-4xl font-bold mb-8">Hive Mind Global Pulse</h1>
          <div className="text-red-500 mb-4">{error}</div>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-4xl font-bold">Hive Mind Global Pulse</h1>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>

        {/* Credits Display */}
        {credits && (
          <div className="bg-gray-800 rounded-lg p-6 mb-8 border border-gray-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold mb-2">Your Credits</h2>
                <div className="flex items-baseline gap-2">
                  <span className="text-5xl font-bold text-blue-400">
                    {credits.credits_remaining}
                  </span>
                  <span className="text-gray-400 text-xl">credits remaining</span>
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  {credits.credits_used} credits used total
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-500">Last updated</div>
                <div className="text-gray-400">{formatTimeAgo(credits.as_of)}</div>
              </div>
            </div>
          </div>
        )}

        {/* Convictions Ranking */}
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <h2 className="text-2xl font-semibold mb-6">Top 5 High-Conviction Signals (Last 24h)</h2>
          
          {convictions.length === 0 ? (
            <div className="text-gray-400 text-center py-8">
              No high-conviction signals available in the last 24 hours.
            </div>
          ) : (
            <div className="space-y-4">
              {convictions.map((signal, index) => (
                <div
                  key={signal.id}
                  className="bg-gray-700 rounded-lg p-4 flex items-center justify-between hover:bg-gray-600 transition-colors"
                >
                  <div className="flex items-center gap-6">
                    {/* Rank */}
                    <div className="text-3xl font-bold text-gray-500 w-12 text-center">
                      #{index + 1}
                    </div>

                    {/* Ticker */}
                    <div className="flex flex-col">
                      <span className="text-2xl font-bold">{signal.ticker}</span>
                      <span className="text-sm text-gray-400">{signal.signal_type}</span>
                    </div>

                    {/* Confidence Score */}
                    <div className="flex flex-col items-center">
                      <span className={`text-3xl font-bold ${getConfidenceColor(signal.confidence_score)}`}>
                        {signal.confidence_score}
                      </span>
                      <span className="text-xs text-gray-400">Confidence</span>
                    </div>

                    {/* Recommendation */}
                    <div className="flex flex-col">
                      <span className="text-xl font-semibold text-green-400">
                        {signal.recommendation}
                      </span>
                      <span className="text-sm text-gray-400">
                        Consensus: {signal.consensus_score.toFixed(2)}
                      </span>
                    </div>

                    {/* Time */}
                    <div className="text-sm text-gray-400">
                      {formatTimeAgo(signal.created_at)}
                    </div>
                  </div>

                  {/* Confidence Bar */}
                  <div className="flex flex-col items-end gap-2">
                    <div className="w-32 h-2 bg-gray-600 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${getConfidenceBg(signal.confidence_score)}`}
                        style={{ width: `${signal.confidence_score}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Signals are aggregated from public investment signals marked as is_public=TRUE</p>
          <p>Only high-conviction BUY/STRONG BUY signals from the last 24 hours are shown</p>
        </div>
      </div>
    </div>
  );
}
