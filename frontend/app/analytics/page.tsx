"use client";

import { useState, useEffect } from "react";

export default function AnalyticsPage() {
  const [mounted, setMounted] = useState(false);
  const [timeRange, setTimeRange] = useState<"30d" | "90d" | "1y">("90d");

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Analytics</h1>
        <p className="text-gray-600">Performance metrics and portfolio analysis</p>
      </div>

      {/* Time Range Selector */}
      <div className="mb-6 flex gap-2">
        {(["30d", "90d", "1y"] as const).map((range) => (
          <button
            key={range}
            onClick={() => setTimeRange(range)}
            className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
              timeRange === range
                ? "bg-primary text-white"
                : "bg-white text-primary border border-gray-300 hover:bg-gray-50"
            }`}
          >
            {range.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Performance */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">Portfolio Performance</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Return</span>
              <span className="text-2xl font-bold text-positive">+12.5%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">vs S&P 500</span>
              <span className="text-xl font-bold text-[#4F8A8B]">+3.2%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Sharpe Ratio</span>
              <span className="text-xl font-bold text-primary">1.45</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Max Drawdown</span>
              <span className="text-xl font-bold text-negative">-8.3%</span>
            </div>
          </div>
        </div>

        {/* Buffett Score Distribution */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">Buffett Score Distribution</h2>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-gray-600">Strong Buy (80-100%)</span>
                <span className="text-sm font-semibold">23%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-positive h-2 rounded-full" style={{ width: "23%" }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-gray-600">Buy (60-80%)</span>
                <span className="text-sm font-semibold">34%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-[#4F8A8B] h-2 rounded-full" style={{ width: "34%" }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-gray-600">Hold (40-60%)</span>
                <span className="text-sm font-semibold">28%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-gray-400 h-2 rounded-full" style={{ width: "28%" }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-gray-600">Sell (0-40%)</span>
                <span className="text-sm font-semibold">15%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-negative h-2 rounded-full" style={{ width: "15%" }} />
              </div>
            </div>
          </div>
        </div>

        {/* AI vs Human Performance */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">AI vs Human Decisions</h2>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">AI Win Rate</span>
              <span className="text-2xl font-bold text-positive">67%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Human Win Rate</span>
              <span className="text-xl font-bold text-primary">58%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Agreement Rate</span>
              <span className="text-xl font-bold text-[#4F8A8B]">72%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Total Decisions</span>
              <span className="text-xl font-bold text-primary">156</span>
            </div>
          </div>
        </div>

        {/* Sector Performance */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">Sector Performance</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Copper</span>
              <span className="font-bold text-positive">+15.3%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Lithium</span>
              <span className="font-bold text-positive">+12.5%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Nickel</span>
              <span className="font-bold text-negative">-2.1%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Gold</span>
              <span className="font-bold text-[#4F8A8B]">+3.8%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Rare Earth</span>
              <span className="font-bold text-positive">+10.8%</span>
            </div>
          </div>
        </div>

        {/* Risk Metrics */}
        <div className="bg-white rounded-lg shadow-md p-6 lg:col-span-2">
          <h2 className="text-xl font-semibold text-primary mb-4">Risk Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Portfolio Beta</p>
              <p className="text-xl font-bold text-primary">1.12</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Volatility (Annual)</p>
              <p className="text-xl font-bold text-primary">18.5%</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Value at Risk (95%)</p>
              <p className="text-xl font-bold text-negative">-5.2%</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Correlation to Market</p>
              <p className="text-xl font-bold text-primary">0.78</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
