"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";

interface BacktestRun {
  id: string;
  strategy_name: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number | null;
  total_return_pct: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number | null;
  win_rate: number | null;
  trade_count: number | null;
  kelly_effectiveness: any;
  created_at: string;
}

export default function BacktestingPage() {
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    strategy_name: "",
    start_date: "",
    end_date: "",
    initial_capital: 100000,
  });
  const [running, setRunning] = useState(false);
  
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    loadBacktestRuns();
  }, []);

  const loadBacktestRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`/api/backtesting/runs`);
      if (!response.ok) {
        throw new Error("Failed to load backtest runs");
      }
      const data = await response.json();
      setRuns(data.runs);
    } catch (err) {
      console.error("Error loading backtest runs:", err);
      setError("Failed to load backtest runs");
    } finally {
      setLoading(false);
    }
  };

  const handleRunBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setRunning(true);
      setError(null);
      
      const response = await apiFetch(`/api/backtesting/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          weight_macro: 0.2,
          weight_commodity: 0.2,
          weight_geo: 0.2,
          weight_insider: 0.2,
          weight_sentiment: 0.2,
          use_half_kelly: true,
          max_position_size: 0.25,
        }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to run backtest");
      }
      
      setShowForm(false);
      setFormData({
        strategy_name: "",
        start_date: "",
        end_date: "",
        initial_capital: 100000,
      });
      
      await loadBacktestRuns();
    } catch (err) {
      console.error("Error running backtest:", err);
      setError("Failed to run backtest");
    } finally {
      setRunning(false);
    }
  };

  const getReturnColor = (returnPct: number | null) => {
    if (!returnPct) return "text-gray-500";
    return returnPct >= 0 ? "text-green-600" : "text-red-600";
  };

  return (
    <div className="min-h-screen bg-[#F4F1EE] text-[#2F2F2F]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold">The Time Machine</h1>
          <p className="text-gray-600 text-sm">Historical backtesting and AI simulation</p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 rounded-lg p-4 mb-4">
            {error}
          </div>
        )}

        {/* New Backtest Button */}
        <div className="mb-6">
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-[#2F2F2F] text-white rounded hover:opacity-90"
          >
            {showForm ? "Cancel" : "Run New Backtest"}
          </button>
        </div>

        {/* Backtest Form */}
        {showForm && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-lg font-semibold mb-4">Configure Backtest</h2>
            <form onSubmit={handleRunBacktest} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Strategy Name</label>
                <input
                  type="text"
                  value={formData.strategy_name}
                  onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded-lg"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Initial Capital ($)</label>
                <input
                  type="number"
                  value={formData.initial_capital}
                  onChange={(e) => setFormData({ ...formData, initial_capital: parseFloat(e.target.value) })}
                  className="w-full p-2 border border-gray-300 rounded-lg"
                  required
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={running}
                  className="px-4 py-2 bg-[#2F2F2F] text-white rounded hover:opacity-90 disabled:opacity-50"
                >
                  {running ? "Running..." : "Run Backtest"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Backtest Runs Table */}
        {loading ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <div className="text-gray-600">Loading backtest runs...</div>
          </div>
        ) : runs.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center">
            <div className="text-gray-600">No backtest runs yet. Run your first backtest to get started.</div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow-md overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Strategy</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">Period</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Initial</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Final</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Return</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Sharpe</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Max DD</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Win Rate</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-gray-700">Trades</th>
                  <th className="px-4 py-3 text-center text-sm font-semibold text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {runs.map((run) => (
                  <tr key={run.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{run.strategy_name}</div>
                      <div className="text-xs text-gray-500">{new Date(run.created_at).toLocaleString()}</div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {run.start_date} → {run.end_date}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      ${run.initial_capital.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      {run.final_capital ? `$${run.final_capital.toLocaleString()}` : "N/A"}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium">
                      {run.total_return_pct !== null ? (
                        <span className={getReturnColor(run.total_return_pct)}>
                          {run.total_return_pct.toFixed(2)}%
                        </span>
                      ) : (
                        "N/A"
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      {run.sharpe_ratio ? run.sharpe_ratio.toFixed(2) : "N/A"}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      {run.max_drawdown_pct ? `${run.max_drawdown_pct.toFixed(2)}%` : "N/A"}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      {run.win_rate ? `${(run.win_rate * 100).toFixed(1)}%` : "N/A"}
                    </td>
                    <td className="px-4 py-3 text-right text-sm">
                      {run.trade_count ?? "N/A"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs">
                        View
                      </button>
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
