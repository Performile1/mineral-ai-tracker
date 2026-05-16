"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import useScreenerStore, { ScreenerItem } from "@/lib/store/screenerStore";
import { apiFetch } from "@/lib/apiClient";

export default function ScreenerPage() {
  const router = useRouter();
  const {
    items,
    loading,
    error,
    lastUpdated,
    filters,
    sortBy,
    setItems,
    setLoading,
    setError,
    setLastUpdated,
    setSignalFilter,
    setMinConfidence,
    setSearchQuery,
    setTaStatusFilter,
    setSortBy,
    resetFilters,
    getSortedItems,
  } = useScreenerStore();

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    loadScreener();
  }, []);

  const loadScreener = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`/api/intelligence/screener?limit=100`);
      if (!response.ok) {
        throw new Error("Failed to load screener data");
      }
      const data = await response.json();
      setItems(data.items);
      setLastUpdated(data.updated_at);
    } catch (err) {
      console.error("Error loading screener:", err);
      setError("Failed to load screener data");
    } finally {
      setLoading(false);
    }
  };

  const handleDeepDive = (ticker: string) => {
    router.push(`/assets/${ticker}`);
  };

  const handleExecute = (ticker: string) => {
    router.push(`/dashboard?ticker=${ticker}`);
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case "STRONG BUY":
        return "bg-green-600 text-white";
      case "BUY":
        return "bg-green-500 text-white";
      case "PASS":
        return "bg-gray-500 text-white";
      case "SELL":
        return "bg-red-500 text-white";
      case "STRONG SELL":
        return "bg-red-600 text-white";
      default:
        return "bg-gray-400 text-white";
    }
  };

  const getTaStatusColor = (status: string) => {
    switch (status) {
      case "BULLISH":
        return "text-green-600";
      case "BEARISH":
        return "text-red-600";
      case "NEUTRAL":
        return "text-gray-600";
      default:
        return "text-gray-400";
    }
  };

  const sortedItems = getSortedItems();

  return (
    <div className="min-h-screen bg-[#F4F1EE] text-[#2F2F2F]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-2">Alpha Screener</h1>
          <p className="text-gray-600 text-sm">
            AI-driven stock screener combining fundamentals, technical analysis, and confidence scores
            {lastUpdated && ` • Last updated: ${new Date(lastUpdated).toLocaleString()}`}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="bg-white rounded-lg shadow-md p-4 mb-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <input
                type="text"
                placeholder="Ticker or name..."
                value={filters.searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg"
              />
            </div>

            {/* Signal Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">AI Signal</label>
              <select
                value={filters.signal}
                onChange={(e) => setSignalFilter(e.target.value as any)}
                className="w-full p-2 border border-gray-300 rounded-lg"
              >
                <option value="ALL">All Signals</option>
                <option value="STRONG BUY">Strong Buy</option>
                <option value="BUY">Buy</option>
                <option value="PASS">Pass</option>
                <option value="SELL">Sell</option>
                <option value="STRONG SELL">Strong Sell</option>
              </select>
            </div>

            {/* Confidence Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Confidence</label>
              <input
                type="range"
                min="0"
                max="100"
                value={filters.minConfidence}
                onChange={(e) => setMinConfidence(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="text-sm text-gray-600">{filters.minConfidence}%+</div>
            </div>

            {/* TA Status Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">TA Status</label>
              <select
                value={filters.taStatus}
                onChange={(e) => setTaStatusFilter(e.target.value as any)}
                className="w-full p-2 border border-gray-300 rounded-lg"
              >
                <option value="ALL">All</option>
                <option value="BULLISH">Bullish</option>
                <option value="BEARISH">Bearish</option>
                <option value="NEUTRAL">Neutral</option>
              </select>
            </div>
          </div>

          {/* Sort & Reset */}
          <div className="flex justify-between items-center mt-4 pt-4 border-t">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">Sort by:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="p-2 border border-gray-300 rounded-lg text-sm"
              >
                <option value="confidence_desc">Confidence (High to Low)</option>
                <option value="confidence_asc">Confidence (Low to High)</option>
                <option value="pe_asc">P/E (Low to High)</option>
                <option value="pe_desc">P/E (High to Low)</option>
                <option value="created_desc">Most Recent</option>
              </select>
            </div>
            <button
              onClick={resetFilters}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm"
            >
              Reset Filters
            </button>
          </div>
        </div>

        {/* Results Count */}
        <div className="mb-2 text-sm text-gray-600">
          Showing {sortedItems.length} of {items.length} assets
        </div>
      </div>

      {/* Table */}
      <div className="max-w-7xl mx-auto px-6 pb-6">
        {loading ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <div className="text-gray-600">Loading screener data...</div>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-400 text-red-700 rounded-lg p-4">
            {error}
          </div>
        ) : sortedItems.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <div className="text-gray-600">No assets match your filters</div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Asset</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Sector</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">P/E</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">TA Status</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">RSI</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Confidence</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">AI Signal</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sortedItems.map((item) => (
                  <tr key={item.ticker} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div>
                        <div className="font-semibold text-[#2F2F2F]">{item.ticker}</div>
                        <div className="text-sm text-gray-600">{item.name || 'N/A'}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.sector || 'N/A'}</td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">
                      {item.pe_ratio ? item.pe_ratio.toFixed(2) : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-sm font-medium ${getTaStatusColor(item.ta_status)}`}>
                        {item.ta_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-600">
                      {item.rsi ? item.rsi.toFixed(1) : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${item.confidence_score}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium">{item.confidence_score}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`px-2 py-1 rounded text-xs font-semibold ${getSignalColor(item.ai_signal)}`}>
                        {item.ai_signal}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => handleDeepDive(item.ticker)}
                          className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs"
                        >
                          Deep Dive
                        </button>
                        <button
                          onClick={() => handleExecute(item.ticker)}
                          className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-xs"
                        >
                          Execute
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
