"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import LiveTicker from "@/components/LiveTicker";
import IntelligenceCard from "@/components/IntelligenceCard";
import { apiFetch } from "@/lib/apiClient";

interface AssetProfile {
  ticker: string;
  name: string | null;
  description: string | null;
  ceo: string | null;
  industry: string | null;
  sector: string | null;
  market_cap: number | null;
  price: number | null;
  pe_ratio: number | null;
  ev_ebit: number | null;
  roe: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  eps: number | null;
  next_earnings_date: string | null;
  upcoming_earnings: Array<{ date: string; eps_estimate: number; reported_eps: number | null }>;
  currency: string | null;
  exchange: string | null;
  country: string | null;
  website: string | null;
  employees: number | null;
}

export default function AssetDetailPage() {
  const params = useParams();
  const ticker = (params.ticker as string).toUpperCase();
  
  const [profile, setProfile] = useState<AssetProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hiveConsensus, setHiveConsensus] = useState<any>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    loadProfile();
    loadHiveConsensus();
  }, [ticker]);

  const loadHiveConsensus = async () => {
    try {
      // Public endpoint: hive consensus is anonymous and does not require auth.
      const response = await fetch(`${apiUrl}/api/hive/consensus/${ticker}`);
      if (response.ok) {
        const data = await response.json();
        setHiveConsensus(data);
      }
    } catch (err) {
      console.error("Error loading hive consensus:", err);
    }
  };

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`/api/assets/profile/${ticker}`);
      if (!response.ok) {
        throw new Error("Failed to load asset profile");
      }
      const data = await response.json();
      setProfile(data);
    } catch (err) {
      console.error("Error loading profile:", err);
      setError("Failed to load asset profile");
    } finally {
      setLoading(false);
    }
  };

  const handleStalk = async () => {
    try {
      const response = await apiFetch(`/api/watchlist/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
      });
      if (!response.ok) {
        throw new Error("Failed to trigger analysis");
      }
      alert("Analysis triggered successfully!");
    } catch (err) {
      console.error("Error triggering analysis:", err);
      alert("Failed to trigger analysis");
    }
  };

  const formatNumber = (value: number | null, decimals: number = 2) => {
    if (value === null) return "N/A";
    if (Math.abs(value) >= 1_000_000) {
      return `${(value / 1_000_000).toFixed(decimals)}M`;
    }
    if (Math.abs(value) >= 1_000) {
      return `${(value / 1_000).toFixed(decimals)}K`;
    }
    return value.toFixed(decimals);
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return "N/A";
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("sv-SE", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F4F1EE] flex items-center justify-center">
        <div className="text-gray-600">Loading asset profile...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-[#F4F1EE] flex items-center justify-center">
        <div className="text-red-600">{error || "Asset not found"}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F4F1EE] text-[#2F2F2F]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold">{profile.name || profile.ticker}</h1>
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span className="font-mono">{profile.ticker}</span>
                {profile.exchange && <span>• {profile.exchange}</span>}
                {profile.industry && <span>• {profile.industry}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* Hive Mind Consensus Badge */}
            {hiveConsensus && hiveConsensus.total_signals > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🐝</span>
                  <div>
                    <div className="text-xs text-gray-600">Hive Mind Consensus</div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-amber-700">{hiveConsensus.majority_signal}</span>
                      <span className="text-sm text-gray-600">
                        {hiveConsensus.average_confidence.toFixed(0)}% conf ({hiveConsensus.total_signals} signals)
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <LiveTicker ticker={ticker} />
            <button
              onClick={handleStalk}
              className="px-4 py-2 bg-[#2F2F2F] text-white rounded-lg font-semibold hover:opacity-90 transition-opacity"
            >
              STALK
            </button>
          </div>
        </div>
      </div>

      {/* Bento Box Layout */}
      <div className="max-w-7xl mx-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Fundamentals */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold mb-4 text-[#2F2F2F]">Fundamentals</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">P/E (TTM)</div>
                <div className="text-lg font-semibold">{profile.pe_ratio?.toFixed(2) || "N/A"}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">EV/EBIT</div>
                <div className="text-lg font-semibold">{profile.ev_ebit?.toFixed(2) || "N/A"}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">ROE</div>
                <div className="text-lg font-semibold">{formatPercent(profile.roe)}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">Gross Margin</div>
                <div className="text-lg font-semibold">{formatPercent(profile.gross_margin)}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">Operating Margin</div>
                <div className="text-lg font-semibold">{formatPercent(profile.operating_margin)}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">Net Margin</div>
                <div className="text-lg font-semibold">{formatPercent(profile.net_margin)}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">Debt/Equity</div>
                <div className="text-lg font-semibold">{profile.debt_to_equity?.toFixed(2) || "N/A"}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <div className="text-xs text-gray-500 mb-1">Current Ratio</div>
                <div className="text-lg font-semibold">{profile.current_ratio?.toFixed(2) || "N/A"}</div>
              </div>
              <div className="bg-gray-50 p-3 rounded col-span-2">
                <div className="text-xs text-gray-500 mb-1">Market Cap</div>
                <div className="text-lg font-semibold">{formatNumber(profile.market_cap, 0)}</div>
              </div>
            </div>
          </div>

          {/* Middle Column: SLM Verdict */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold mb-4 text-[#2F2F2F]">AI Analysis</h2>
            <div className="min-h-[400px]">
              <IntelligenceCard asset_id={ticker} />
            </div>
          </div>

          {/* Right Column: Company Profile */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold mb-4 text-[#2F2F2F]">Company Profile</h2>
            
            {profile.description && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Description</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{profile.description}</p>
              </div>
            )}

            {profile.ceo && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-1">CEO</h3>
                <p className="text-sm text-gray-600">{profile.ceo}</p>
              </div>
            )}

            {profile.employees && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-1">Employees</h3>
                <p className="text-sm text-gray-600">{profile.employees.toLocaleString()}</p>
              </div>
            )}

            {profile.website && (
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 mb-1">Website</h3>
                <a
                  href={profile.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline"
                >
                  {profile.website}
                </a>
              </div>
            )}

            <h3 className="text-sm font-semibold text-gray-700 mb-2">Upcoming Earnings</h3>
            {profile.upcoming_earnings.length > 0 ? (
              <div className="space-y-2">
                {profile.upcoming_earnings.map((earning, idx) => (
                  <div key={idx} className="bg-gray-50 p-3 rounded">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium">{formatDate(earning.date)}</span>
                      <span className="text-xs text-gray-500">
                        EPS Est: {earning.eps_estimate?.toFixed(2) || "N/A"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No upcoming earnings data</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
