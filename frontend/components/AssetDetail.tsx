"use client";

import { useState } from "react";

interface PricePoint {
  date: string;
  price: number;
  prediction?: number;
}

interface AssetDetailProps {
  asset: {
    id: string;
    ticker: string;
    name: string;
    current_price: number;
    buffett_score: number;
    confidence_score: number;
    commodity_type: string;
  };
  onClose: () => void;
}

export default function AssetDetail({ asset, onClose }: AssetDetailProps) {
  const [timeRange, setTimeRange] = useState<"1y" | "6m" | "3m">("1y");

  // Placeholder price history data
  const generatePriceHistory = (months: number): PricePoint[] => {
    const points: PricePoint[] = [];
    const now = new Date();
    const startPrice = asset.current_price * 0.85;
    
    for (let i = months * 30; i >= 0; i -= 7) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      const trend = Math.sin(i / 30) * 0.1 + (Math.random() - 0.5) * 0.05;
      const price = startPrice * (1 + trend);
      
      points.push({
        date: date.toISOString().split("T")[0],
        price,
        prediction: price * (1 + (asset.buffett_score - 0.5) * 0.3), // AI prediction based on Buffett score
      });
    }
    
    return points;
  };

  const priceHistory = generatePriceHistory(timeRange === "1y" ? 12 : timeRange === "6m" ? 6 : 3);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-positive";
    if (score >= 0.6) return "text-[#4F8A8B]";
    if (score >= 0.4) return "text-primary";
    return "text-negative";
  };

  const getRecommendation = (score: number) => {
    if (score >= 0.8) return "STRONG BUY";
    if (score >= 0.6) return "BUY";
    if (score >= 0.4) return "HOLD";
    if (score >= 0.2) return "SELL";
    return "STRONG SELL";
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold text-primary">{asset.ticker}</h2>
              <p className="text-gray-600">{asset.name}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>
        </div>

        <div className="p-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">Current Price</p>
              <p className="text-xl font-bold text-primary">
                {asset.current_price.toFixed(2)} SEK
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">Buffett Score</p>
              <p className={`text-xl font-bold ${getScoreColor(asset.buffett_score)}`}>
                {(asset.buffett_score * 100).toFixed(0)}%
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">Recommendation</p>
              <p className={`text-lg font-bold ${getScoreColor(asset.buffett_score)}`}>
                {getRecommendation(asset.buffett_score)}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-500">Confidence</p>
              <p className="text-xl font-bold text-primary">
                {(asset.confidence_score * 100).toFixed(0)}%
              </p>
            </div>
          </div>

          {/* Time Range Selector */}
          <div className="mb-4 flex gap-2">
            {(["1y", "6m", "3m"] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
                  timeRange === range
                    ? "bg-primary text-white"
                    : "bg-gray-100 text-primary hover:bg-gray-200"
                }`}
              >
                {range.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Price Chart */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-primary mb-4">Price History & Predictions</h3>
            <div className="h-64 flex items-end gap-1">
              {priceHistory.map((point, index) => {
                const maxPrice = Math.max(...priceHistory.map((p) => p.price));
                const heightPercent = (point.price / maxPrice) * 100;
                return (
                  <div key={index} className="flex-1 flex flex-col items-center">
                    <div className="w-full bg-gray-200 rounded-t" style={{ height: "100%" }}>
                      <div
                        className="w-full bg-primary rounded-t transition-all"
                        style={{ height: `${heightPercent}%` }}
                      />
                    </div>
                    {point.prediction && (
                      <div
                        className="w-1 bg-positive mt-1"
                        style={{ height: `${(point.prediction / maxPrice) * 20}%` }}
                      />
                    )}
                    <span className="text-xs text-gray-500 mt-2 rotate-45 origin-left">
                      {index % 5 === 0 ? point.date.slice(5) : ""}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-4 mt-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-primary rounded" />
                <span className="text-gray-600">Actual Price</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-1 bg-positive" />
                <span className="text-gray-600">AI Prediction</span>
              </div>
            </div>
          </div>

          {/* AI Analysis */}
          <div className="bg-blue-50 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-primary mb-2">AI Analysis</h3>
            <div className="space-y-2 text-sm text-gray-700">
              <p>
                <strong>Commodity:</strong> {asset.commodity_type.replace(/_/g, " ")}
              </p>
              <p>
                <strong>Prediction:</strong> Based on Buffett Score analysis, the AI predicts a{" "}
                {asset.buffett_score > 0.5 ? "positive" : "negative"} trend over the next{" "}
                {timeRange}.
              </p>
              <p>
                <strong>Key Factors:</strong>
              </p>
              <ul className="list-disc list-inside ml-4">
                <li>Macro demand indicators: {asset.buffett_score > 0.6 ? "Positive" : "Neutral"}</li>
                <li>Supply deficit: {asset.buffett_score > 0.7 ? "Significant" : "Moderate"}</li>
                <li>Geopolitical risk: {asset.buffett_score < 0.5 ? "Elevated" : "Low"}</li>
              </ul>
            </div>
          </div>

          {/* Data Sources */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-primary mb-2">Data Sources</h3>
            <div className="space-y-2 text-sm text-gray-700">
              <p>✅ Avanza (verified match)</p>
              <p>✅ LME price data</p>
              <p>✅ SGU geology reports</p>
              <p>✅ Industry macro indicators</p>
              <p>⚠️ Company contact data: Limited availability</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
