"use client";

import { useMemo, useState, useEffect } from "react";
import { calculateISK, kellyPosition, formatSEK, schablonRate } from "@/lib/iskTax";
import { apiFetch } from "@/lib/apiClient";

interface PaperTrade {
  id: string;
  asset_id: string;
  asset_ticker: string;
  asset_name: string;
  trade_type: "buy" | "sell";
  shares: number;
  price_per_share: number;
  total_value: number;
  ai_buffett_score: number;
  ai_recommendation: string;
  executed_at: string;
  is_closed: boolean;
  close_price_per_share?: number;
  realized_pnl?: number;
  realized_pnl_percentage?: number;
}

export default function ShadowPortfolio() {
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [balance, setBalance] = useState<number>(100000);
  const [initialBalance] = useState<number>(100000);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // PRD v8.6: ISK schablonskatt simulation
  const [iskEnabled, setIskEnabled] = useState<boolean>(false);

  // PRD v8.6: Kelly auto-sizing inputs (defaults match KellyCalculator)
  const [kellyWinProb, setKellyWinProb] = useState<number>(0.6);
  const [kellyRatio, setKellyRatio] = useState<number>(2.0);
  const [kellyFraction, setKellyFraction] = useState<number>(0.5);

  // PRD v8.6 Phase 8: Execution Engine (mock orders via /api/execution/trade)
  const [buyTicker, setBuyTicker] = useState<string>("");
  const [buyConfidence, setBuyConfidence] = useState<number>(75);
  const [buyLoading, setBuyLoading] = useState(false);
  const [buyError, setBuyError] = useState<string | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const submitBuy = async () => {
    const t = buyTicker.trim().toUpperCase();
    if (!t) return;
    setBuyLoading(true);
    setBuyError(null);
    try {
      const res = await apiFetch(`/api/execution/trade`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: t,
          action: "buy",
          confidence: buyConfidence,
          bankroll: balance,
          risk_reward_ratio: kellyRatio,
          stop_loss_pct: 0.1,
          use_half_kelly: kellyFraction <= 0.5,
        }),
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
      }
      const order = await res.json();
      const newTrade: PaperTrade = {
        id: order.order_id,
        asset_id: order.ticker,
        asset_ticker: order.ticker,
        asset_name: order.ticker,
        trade_type: "buy",
        shares: order.suggested_shares,
        price_per_share: order.entry_price,
        total_value: order.suggested_size_sek,
        ai_buffett_score: order.confidence / 100,
        ai_recommendation: `${order.kelly_interpretation} • SL @${order.stop_loss_price} • TP @${order.take_profit_price}`,
        executed_at: order.executed_at,
        is_closed: false,
      };
      setTrades((prev) => [newTrade, ...prev]);
      setBalance((b) => Math.max(0, b - order.suggested_size_sek));
      setBuyTicker("");
    } catch (e: any) {
      setBuyError(e.message || "Order failed");
    } finally {
      setBuyLoading(false);
    }
  };

  useEffect(() => {
    fetchPaperTrades();
  }, []);

  const fetchPaperTrades = async () => {
    try {
      setLoading(true);
      // In production, fetch from API
      // const response = await fetch("/api/paper-trades");
      // const data = await response.json();
      
      // Placeholder data for now
      setTrades([]);
      setBalance(100000);
    } catch (err) {
      setError("Failed to load paper trades");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("sv-SE", {
      style: "currency",
      currency: "SEK",
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("sv-SE", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const totalPnl = trades.reduce((sum, trade) => {
    if (trade.is_closed && trade.realized_pnl !== undefined) {
      return sum + trade.realized_pnl;
    }
    return sum;
  }, 0);

  const pnlPercentage = ((balance - initialBalance) / initialBalance) * 100;

  // PRD v8.6: ISK True Net Yield projection
  const iskResult = useMemo(
    () =>
      calculateISK({
        startBalance: initialBalance,
        endBalance: balance,
      }),
    [initialBalance, balance]
  );

  // PRD v8.6: Kelly auto-sized buy suggestion based on remaining cash
  const kelly = useMemo(
    () =>
      kellyPosition({
        winProb: kellyWinProb,
        winLossRatio: kellyRatio,
        bankroll: balance,
        fraction: kellyFraction,
      }),
    [kellyWinProb, kellyRatio, kellyFraction, balance]
  );

  const displayedPnlSek = iskEnabled ? iskResult.netYieldSek : iskResult.grossYieldSek;
  const displayedYieldPct = iskEnabled ? iskResult.netYieldPct : iskResult.grossYieldPct;

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Shadow Portfolio (Pappershandel)</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Shadow Portfolio (Pappershandel)</h2>
        <div className="text-negative text-center py-8">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-primary">Shadow Portfolio (Pappershandel)</h2>
        <button
          onClick={fetchPaperTrades}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Uppdatera
        </button>
      </div>

      {/* ISK Toggle (PRD v8.6) */}
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIskEnabled((v) => !v)}
            aria-pressed={iskEnabled}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              iskEnabled ? "bg-positive" : "bg-gray-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                iskEnabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
          <span className="text-sm text-primary">
            Simulate ISK Tax
            <span className="text-xs text-gray-500 ml-2">
              (schablon {schablonRate().toFixed(2)}% × 30%)
            </span>
          </span>
        </div>
        {iskEnabled && (
          <span className="text-xs text-gray-600">
            Tax due: {formatSEK(iskResult.taxDue)}
          </span>
        )}
      </div>

      {/* Balance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-600">Nuvarande Balans</p>
          <p className="text-2xl font-bold text-primary">{formatCurrency(balance)}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-600">Total P&L</p>
          <p className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-positive' : 'text-negative'}`}>
            {totalPnl >= 0 ? '+' : ''}{formatCurrency(totalPnl)}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-600">Gross Yield</p>
          <p className={`text-2xl font-bold ${iskResult.grossYieldPct >= 0 ? 'text-positive' : 'text-negative'}`}>
            {iskResult.grossYieldPct >= 0 ? '+' : ''}{iskResult.grossYieldPct.toFixed(2)}%
          </p>
        </div>
        <div className={`rounded-lg p-4 ${iskEnabled ? "bg-positive/10 border border-positive" : "bg-gray-50"}`}>
          <p className="text-sm text-gray-600">
            {iskEnabled ? "True Net Yield (ISK)" : "Avkastning"}
          </p>
          <p className={`text-2xl font-bold ${displayedYieldPct >= 0 ? 'text-positive' : 'text-negative'}`}>
            {displayedYieldPct >= 0 ? '+' : ''}{displayedYieldPct.toFixed(2)}%
          </p>
          <p className="text-[10px] text-gray-500 mt-1">
            {iskEnabled ? formatSEK(displayedPnlSek) : `${pnlPercentage.toFixed(2)}% (no tax)`}
          </p>
        </div>
      </div>

      {/* Execute Buy - Mock Order via Kelly + 10% Stop-Loss (PRD v8.6 §1) */}
      <div className="bg-positive/5 border border-positive rounded-lg p-4 mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1 min-w-[140px]">
            <label className="text-[11px] text-gray-600 mb-1 block">Ticker</label>
            <input
              value={buyTicker}
              onChange={(e) => setBuyTicker(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submitBuy()}
              placeholder="BOL.ST"
              className="w-full border border-gray-300 rounded px-2 py-1 text-sm uppercase tracking-wider"
            />
          </div>
          <div className="w-32">
            <label className="text-[11px] text-gray-600 mb-1 block">
              AI Confidence {buyConfidence}
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={buyConfidence}
              onChange={(e) => setBuyConfidence(Number(e.target.value))}
              className="w-full accent-positive"
            />
          </div>
          <button
            type="button"
            onClick={submitBuy}
            disabled={!buyTicker.trim() || buyLoading}
            className="bg-positive text-white px-4 py-1.5 rounded text-sm font-semibold hover:opacity-90 disabled:opacity-40"
          >
            {buyLoading ? "Executing..." : "Köp"}
          </button>
        </div>
        {buyError && (
          <p className="text-xs text-negative mt-2">{buyError}</p>
        )}
        <p className="text-[10px] text-gray-500 mt-2">
          Kelly-sized position with auto 10% stop-loss • Take-profit at {kellyRatio.toFixed(1)}R
        </p>
      </div>

      {/* Kelly auto-sizer (PRD v8.6) */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-semibold text-primary uppercase tracking-wider">
            Kelly-Sized Position
          </h3>
          <span className="text-xs text-gray-500">
            Suggested next buy: <strong className="text-positive">{formatSEK(kelly.positionSize)}</strong>
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <KellyField
            label={`Win Probability ${(kellyWinProb * 100).toFixed(0)}%`}
            value={kellyWinProb}
            min={0}
            max={1}
            step={0.01}
            onChange={setKellyWinProb}
          />
          <KellyField
            label={`W/L Ratio ${kellyRatio.toFixed(1)}x`}
            value={kellyRatio}
            min={0.1}
            max={10}
            step={0.1}
            onChange={setKellyRatio}
          />
          <KellyField
            label={`Fractional Kelly ${(kellyFraction * 100).toFixed(0)}%`}
            value={kellyFraction}
            min={0.1}
            max={1}
            step={0.05}
            onChange={setKellyFraction}
          />
        </div>
        <p className="text-[10px] text-gray-500 mt-2">
          Full Kelly: {(kelly.fullKelly * 100).toFixed(1)}% • Adjusted: {(kelly.adjusted * 100).toFixed(1)}% of bankroll.
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border-l-4 border-primary p-4 mb-6">
        <p className="text-sm text-primary">
          <strong>Riskfri simulering:</strong> Du har 100 000 fiktiva SEK för att testa AI:ns signaler.
          Inga riktiga pengar riskeras. Bygg förtroende innan du investerar på riktigt.
        </p>
      </div>

      {/* Trades Table */}
      {trades.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">Inga pappershandelstransaktioner</p>
          <p className="text-sm">Lägg till tillgångar och börja handla för att bygga förtroende för AI:ns signaler</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-semibold text-primary">Tid</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-primary">Bolag</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-primary">Typ</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-primary">Pris</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-primary">Antal</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-primary">Värde</th>
                <th className="text-center py-3 px-4 text-sm font-semibold text-primary">AI Score</th>
                <th className="text-center py-3 px-4 text-sm font-semibold text-primary">Status</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-primary">P&L</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 text-sm text-gray-600">{formatDate(trade.executed_at)}</td>
                  <td className="py-3 px-4 text-sm font-semibold text-primary">{trade.asset_ticker}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 text-xs font-semibold rounded ${
                      trade.trade_type === 'buy' ? 'bg-positive text-white' : 'bg-negative text-white'
                    }`}>
                      {trade.trade_type.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-sm text-right text-gray-600">{formatCurrency(trade.price_per_share)}</td>
                  <td className="py-3 px-4 text-sm text-right text-gray-600">{trade.shares}</td>
                  <td className="py-3 px-4 text-sm text-right text-gray-600">{formatCurrency(trade.total_value)}</td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex flex-col items-center">
                      <span className={`text-sm font-bold ${
                        trade.ai_buffett_score >= 0.6 ? 'text-positive' : 
                        trade.ai_buffett_score >= 0.4 ? 'text-primary' : 'text-negative'
                      }`}>
                        {(trade.ai_buffett_score * 100).toFixed(0)}
                      </span>
                      <span className="text-xs text-gray-500">{trade.ai_recommendation}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    {trade.is_closed ? (
                      <span className="px-2 py-1 text-xs font-semibold rounded bg-gray-200 text-gray-600">
                        STÄNGD
                      </span>
                    ) : (
                      <span className="px-2 py-1 text-xs font-semibold rounded bg-green-100 text-positive">
                        ÖPPEN
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {trade.is_closed && trade.realized_pnl !== undefined ? (
                      <span className={`text-sm font-semibold ${trade.realized_pnl >= 0 ? 'text-positive' : 'text-negative'}`}>
                        {trade.realized_pnl >= 0 ? '+' : ''}{formatCurrency(trade.realized_pnl)}
                      </span>
                    ) : (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function KellyField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col">
      <label className="text-[11px] text-gray-600 mb-1">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-positive"
      />
    </div>
  );
}
