"use client";

import { useState, useEffect } from "react";
import RiskCorrelationMatrix from "@/components/RiskCorrelationMatrix";
import { apiFetch } from "@/lib/apiClient";

interface SectorExposure {
  sector: string;
  exposure_pct: number;
  risk_level: string;
}

interface MacroCorrelation {
  asset: string;
  macro_indicator: string;
  indicator_name: string;
  correlation: number;
  beta: number;
}

interface HedgeSuggestion {
  risk_type: string;
  risk_level: string;
  correlation: number;
  asset1: string;
  asset2: string;
  asset_to_hedge: string;
  position_weight_pct: number;
  hedge_instrument: string;
  hedge_ratio: number;
  hedge_size_pct: number;
  estimated_cost_pct: number;
  suggestion: string;
  rationale: string;
}

export default function RiskDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [systematicRisk, setSystematicRisk] = useState<number>(0);
  const [riskLevel, setRiskLevel] = useState<string>("low");
  const [sectorExposures, setSectorExposures] = useState<SectorExposure[]>([]);
  const [concentrationRisks, setConcentrationRisks] = useState<string[]>([]);
  const [macroCorrelations, setMacroCorrelations] = useState<MacroCorrelation[]>([]);
  const [systematicRisks, setSystematicRisks] = useState<string[]>([]);
  const [hedgeSuggestions, setHedgeSuggestions] = useState<HedgeSuggestion[]>([]);
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    loadRiskData();
  }, []);

  const loadRiskData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Load correlation analysis
      const [corrResp, sectorResp, macroResp] = await Promise.all([
        apiFetch(`/api/portfolio/correlation/analysis`),
        apiFetch(`/api/portfolio/correlation/sector-exposure`),
        apiFetch(`/api/portfolio/correlation/macro-correlation`),
      ]);

      if (corrResp.ok) {
        const corrData = await corrResp.json();
        setSystematicRisk(corrData.systematic_risk);
        setRiskLevel(corrData.risk_level);
        setHedgeSuggestions(corrData.hedge_suggestions);
      }

      if (sectorResp.ok) {
        const sectorData = await sectorResp.json();
        setSectorExposures(sectorData.exposures);
        setConcentrationRisks(sectorData.concentration_risks);
      }

      if (macroResp.ok) {
        const macroData = await macroResp.json();
        setMacroCorrelations(macroData.correlations);
        setSystematicRisks(macroData.systematic_risks);
      }
    } catch (err) {
      console.error("Error loading risk data:", err);
      setError("Failed to load risk analysis data");
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case "critical":
        return "text-red-600";
      case "high":
        return "text-orange-600";
      case "medium":
        return "text-yellow-600";
      default:
        return "text-green-600";
    }
  };

  const getRiskBg = (level: string) => {
    switch (level) {
      case "critical":
        return "bg-red-100";
      case "high":
        return "bg-orange-100";
      case "medium":
        return "bg-yellow-100";
      default:
        return "bg-green-100";
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F1EE] text-[#2F2F2F]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">Risk Dashboard</h1>
          <p className="text-gray-600 text-sm">Portfolio correlation analysis and hedge recommendations</p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {loading ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <div className="text-gray-600">Loading risk analysis...</div>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-400 text-red-700 rounded-lg p-4">
            {error}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Systematic Risk Score */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">Systematic Risk Score</h2>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600">Risk Level</span>
                    <span className={`text-lg font-bold ${getRiskColor(riskLevel)}`}>
                      {riskLevel.toUpperCase()}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full transition-all ${getRiskBg(riskLevel)}`}
                      style={{ width: `${systematicRisk * 100}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Score: {systematicRisk.toFixed(2)} / 1.00
                  </div>
                </div>
              </div>
            </div>

            {/* Sector Exposure */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">Sector Exposure</h2>
              {sectorExposures.length > 0 ? (
                <div className="space-y-3">
                  {sectorExposures.map((exposure, idx) => (
                    <div key={idx} className="flex items-center gap-4">
                      <div className="w-32 text-sm font-medium">{exposure.sector}</div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-gray-600">Exposure</span>
                          <span className={`text-xs font-semibold ${getRiskColor(exposure.risk_level)}`}>
                            {exposure.exposure_pct.toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${getRiskBg(exposure.risk_level)}`}
                            style={{ width: `${exposure.exposure_pct}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-sm">No sector data available</div>
              )}
              
              {concentrationRisks.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Concentration Warnings</h3>
                  <ul className="space-y-1">
                    {concentrationRisks.map((risk, idx) => (
                      <li key={idx} className="text-xs text-orange-600">⚠️ {risk}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Macro Correlation */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">Macro Correlation</h2>
              {macroCorrelations.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Asset</th>
                        <th className="text-left py-2">Indicator</th>
                        <th className="text-right py-2">Correlation</th>
                        <th className="text-right py-2">Beta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {macroCorrelations.map((corr, idx) => (
                        <tr key={idx} className="border-b">
                          <td className="py-2">{corr.asset}</td>
                          <td className="py-2">{corr.indicator_name}</td>
                          <td className="py-2 text-right">{corr.correlation.toFixed(3)}</td>
                          <td className="py-2 text-right">{corr.beta.toFixed(3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-gray-500 text-sm">No macro correlation data available</div>
              )}
              
              {systematicRisks.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">Systematic Risk Warnings</h3>
                  <ul className="space-y-1">
                    {systematicRisks.map((risk, idx) => (
                      <li key={idx} className="text-xs text-orange-600">⚠️ {risk}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Hedge Recommendations */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-lg font-semibold mb-4">Hedge Recommendations</h2>
              {hedgeSuggestions.length > 0 ? (
                <div className="space-y-4">
                  {hedgeSuggestions.map((suggestion, idx) => (
                    <div key={idx} className={`p-4 rounded-lg border ${getRiskBg(suggestion.risk_level)}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-semibold ${getRiskColor(suggestion.risk_level)}`}>
                          {suggestion.risk_level.toUpperCase()}: {suggestion.asset_to_hedge}
                        </span>
                        <span className="text-xs text-gray-500">
                          Correlation: {suggestion.correlation.toFixed(2)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 mb-2">{suggestion.suggestion}</p>
                      <p className="text-xs text-gray-600 mb-3">{suggestion.rationale}</p>
                      <div className="flex items-center gap-4 text-xs">
                        <div>
                          <span className="text-gray-500">Position:</span> {suggestion.position_weight_pct.toFixed(1)}%
                        </div>
                        <div>
                          <span className="text-gray-500">Hedge Size:</span> {suggestion.hedge_size_pct.toFixed(1)}%
                        </div>
                        <div>
                          <span className="text-gray-500">Cost:</span> {suggestion.estimated_cost_pct.toFixed(1)}%
                        </div>
                        <div>
                          <span className="text-gray-500">Instrument:</span> {suggestion.hedge_instrument}
                        </div>
                      </div>
                      <button className="mt-3 px-4 py-2 bg-[#2F2F2F] text-white rounded hover:opacity-90 text-xs">
                        Execute Hedge
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-gray-500 text-sm">No hedge recommendations available</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
