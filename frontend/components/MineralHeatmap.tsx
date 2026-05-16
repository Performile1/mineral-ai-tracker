"use client";

import { useState, useEffect } from "react";

interface MineralData {
  commodity: string;
  trend: number; // -100 to 100
  supply_deficit: number; // -100 to 100 (positive = deficit)
  capital_inflow: number; // -100 to 100 (positive = inflow)
  price_change_30d: number;
  data_sources: string[];
}

export default function MineralHeatmap() {
  const [minerals, setMinerals] = useState<MineralData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredMineral, setHoveredMineral] = useState<string | null>(null);

  useEffect(() => {
    fetchMineralData();
  }, []);

  const fetchMineralData = async () => {
    try {
      setLoading(true);
      // In production, fetch from API
      // const response = await fetch("/api/minerals/heatmap");
      // const data = await response.json();
      
      // Placeholder data for now
      setMinerals([
        { 
          commodity: "Lithium", 
          trend: 75, 
          supply_deficit: 85, 
          capital_inflow: 90, 
          price_change_30d: 12.5,
          data_sources: ["LME", "Benchmark Mineral Intelligence", "IEA", "SGU"]
        },
        { 
          commodity: "Cobalt", 
          trend: 60, 
          supply_deficit: 70, 
          capital_inflow: 65, 
          price_change_30d: 8.2,
          data_sources: ["LME", "Benchmark Mineral Intelligence", "Eurostat"]
        },
        { 
          commodity: "Nickel", 
          trend: 45, 
          supply_deficit: 55, 
          capital_inflow: 50, 
          price_change_30d: 5.1,
          data_sources: ["LME", "SGU", "GTK"]
        },
        { 
          commodity: "Copper", 
          trend: 80, 
          supply_deficit: 75, 
          capital_inflow: 85, 
          price_change_30d: 15.3,
          data_sources: ["LME", "SGU", "NGU", "IEA", "Benchmark Mineral Intelligence"]
        },
        { 
          commodity: "Rare Earth", 
          trend: 70, 
          supply_deficit: 90, 
          capital_inflow: 75, 
          price_change_30d: 10.8,
          data_sources: ["Benchmark Mineral Intelligence", "EGDI", "IEA"]
        },
        { 
          commodity: "Uranium", 
          trend: 85, 
          supply_deficit: 80, 
          capital_inflow: 95, 
          price_change_30d: 18.7,
          data_sources: ["UxC", "World Nuclear Association", "SGU"]
        },
        { 
          commodity: "Gold", 
          trend: 30, 
          supply_deficit: 20, 
          capital_inflow: 40, 
          price_change_30d: 2.1,
          data_sources: ["LME", "World Gold Council"]
        },
      ]);
    } catch (err) {
      setError("Failed to load mineral data");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getTrendColor = (value: number) => {
    if (value >= 70) return "bg-positive";
    if (value >= 40) return "bg-[#4F8A8B]";
    if (value >= 0) return "bg-gray-400";
    return "bg-negative";
  };

  const getDeficitColor = (value: number) => {
    if (value >= 70) return "text-negative";
    if (value >= 40) return "text-orange-500";
    if (value >= 0) return "text-gray-500";
    return "text-positive";
  };

  const getInflowColor = (value: number) => {
    if (value >= 70) return "text-positive";
    if (value >= 40) return "text-[#4F8A8B]";
    if (value >= 0) return "text-gray-500";
    return "text-negative";
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Mineral Trend & Deficit Radar</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Mineral Trend & Deficit Radar</h2>
        <div className="text-negative text-center py-8">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-primary">Mineral Trend & Deficit Radar</h2>
        <button
          onClick={fetchMineralData}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Uppdatera
        </button>
      </div>

      {/* Legend */}
      <div className="flex gap-6 mb-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-positive rounded"></div>
          <span className="text-gray-600">Hög Trend</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-negative rounded"></div>
          <span className="text-gray-600">Låg Trend</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-negative font-semibold">●</span>
          <span className="text-gray-600">Stor Brist</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-positive font-semibold">●</span>
          <span className="text-gray-600">Kapitalinflöde</span>
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {minerals.map((mineral) => (
          <div
            key={mineral.commodity}
            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow relative"
            onMouseEnter={() => setHoveredMineral(mineral.commodity)}
            onMouseLeave={() => setHoveredMineral(null)}
          >
            {/* Header with trend bar */}
            <div className="mb-3">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-primary">{mineral.commodity}</h3>
                <span className={`text-sm font-semibold ${mineral.price_change_30d >= 0 ? 'text-positive' : 'text-negative'}`}>
                  {mineral.price_change_30d >= 0 ? '+' : ''}{mineral.price_change_30d.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className={`${getTrendColor(mineral.trend)} h-3 rounded-full transition-all`}
                  style={{ width: `${Math.abs(mineral.trend)}%` }}
                />
              </div>
              <div className="flex justify-between mt-1 text-xs text-gray-500">
                <span>Trend</span>
                <span>{mineral.trend}%</span>
              </div>
            </div>

            {/* Supply Deficit */}
            <div className="mb-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Supply Deficit</span>
                <span className={`text-sm font-semibold ${getDeficitColor(mineral.supply_deficit)}`}>
                  {mineral.supply_deficit > 0 ? '+' : ''}{mineral.supply_deficit}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div
                  className={`h-2 rounded-full transition-all ${mineral.supply_deficit > 0 ? 'bg-negative' : 'bg-positive'}`}
                  style={{ width: `${Math.abs(mineral.supply_deficit)}%` }}
                />
              </div>
            </div>

            {/* Capital Inflow */}
            <div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Capital Inflow</span>
                <span className={`text-sm font-semibold ${getInflowColor(mineral.capital_inflow)}`}>
                  {mineral.capital_inflow > 0 ? '+' : ''}{mineral.capital_inflow}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div
                  className={`h-2 rounded-full transition-all ${mineral.capital_inflow > 0 ? 'bg-positive' : 'bg-negative'}`}
                  style={{ width: `${Math.abs(mineral.capital_inflow)}%` }}
                />
              </div>
            </div>

            {/* Data Sources Tooltip */}
            {hoveredMineral === mineral.commodity && (
              <div className="absolute bottom-full left-0 right-0 mb-2 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-lg z-10">
                <p className="font-semibold mb-2">Data Sources:</p>
                <ul className="list-disc list-inside space-y-1">
                  {mineral.data_sources.map((source, index) => (
                    <li key={index}>{source}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-gray-500">Högst Trend</p>
            <p className="font-semibold text-primary">{minerals.reduce((max, m) => m.trend > max.trend ? m : max).commodity}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Störst Brist</p>
            <p className="font-semibold text-negative">{minerals.reduce((max, m) => m.supply_deficit > max.supply_deficit ? m : max).commodity}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Högst Inflöde</p>
            <p className="font-semibold text-positive">{minerals.reduce((max, m) => m.capital_inflow > max.capital_inflow ? m : max).commodity}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
