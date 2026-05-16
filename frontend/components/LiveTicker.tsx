"use client";

import { useEffect, useRef, useState } from "react";

export interface LiveQuote {
  symbol: string;
  price: number | null;
  previousClose?: number | null;
  currency?: string | null;
  marketState?: string | null;
  fetchedAt: number;
}

interface Props {
  /** Yahoo-style ticker, e.g. "BOL.ST", "AAPL" */
  ticker: string;
  /** Polling interval in ms. Default 30s during market hours. */
  intervalMs?: number;
  /** Compact inline rendering (used by IntelligenceCard). Set false for full block. */
  compact?: boolean;
  /** Called whenever a new quote is fetched. Lets parents detect price drift. */
  onQuote?: (quote: LiveQuote) => void;
  /** Optional anchor price (e.g. analysis-time close). When provided, the drift % is shown inline. */
  anchorPrice?: number;
  /** Optional API base. Defaults to NEXT_PUBLIC_API_URL or the Yahoo public endpoint. */
  apiUrl?: string;
}

/**
 * LiveTicker - lightweight client-side poller for live quote data.
 *
 * Hits the backend proxy `/api/market/quote/{ticker}` (PRD v8.6 Phase 8)
 * to avoid CORS / rate-limit issues against Yahoo Finance.
 *
 * Use the `onQuote` callback in parent components (IntelligenceCard) to
 * compute drift alerts against the analysis-time close.
 */
export default function LiveTicker({
  ticker,
  intervalMs = 30_000,
  compact = false,
  onQuote,
  anchorPrice,
  apiUrl,
}: Props) {
  const [quote, setQuote] = useState<LiveQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let stopped = false;

    const fetchQuote = async () => {
      try {
        const q = await loadQuote(ticker, apiUrl);
        if (stopped) return;
        setQuote(q);
        setError(null);
        onQuote?.(q);
      } catch (e: any) {
        if (stopped) return;
        setError(e?.message || "quote error");
      }
    };

    fetchQuote();
    timerRef.current = setInterval(fetchQuote, intervalMs);

    return () => {
      stopped = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [ticker, intervalMs, apiUrl, onQuote]);

  if (error && !quote) {
    return (
      <span className={compact ? "text-[10px] text-muted" : "text-xs text-muted"}>
        {ticker} live: —
      </span>
    );
  }
  if (!quote || quote.price == null) {
    return (
      <span className={compact ? "text-[10px] text-muted" : "text-xs text-muted"}>
        {ticker} loading…
      </span>
    );
  }

  const drift =
    anchorPrice && anchorPrice > 0
      ? ((quote.price - anchorPrice) / anchorPrice) * 100
      : null;
  const driftColor =
    drift === null
      ? "text-muted"
      : drift > 0
      ? "text-buy"
      : drift < 0
      ? "text-warning"
      : "text-muted";

  if (compact) {
    return (
      <span className="inline-flex items-baseline gap-1 text-[11px] tabular-nums">
        <span className="text-text font-semibold">{quote.price.toFixed(2)}</span>
        {drift !== null && (
          <span className={driftColor}>
            {drift > 0 ? "+" : ""}
            {drift.toFixed(1)}%
          </span>
        )}
      </span>
    );
  }

  return (
    <div className="inline-flex items-baseline gap-2">
      <span className="text-base font-semibold text-text tabular-nums">
        {quote.price.toFixed(2)} {quote.currency || ""}
      </span>
      {drift !== null && (
        <span className={`text-xs ${driftColor}`}>
          {drift > 0 ? "+" : ""}
          {drift.toFixed(2)}% vs anchor
        </span>
      )}
      <span className="text-[10px] text-muted uppercase">{quote.marketState || ""}</span>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Helpers
// ----------------------------------------------------------------------------

async function loadQuote(ticker: string, apiUrl?: string): Promise<LiveQuote> {
  const base = apiUrl || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const r = await fetch(`${base}/api/market/quote/${encodeURIComponent(ticker)}`);
  if (!r.ok) throw new Error(`Quote proxy HTTP ${r.status}`);
  const j = await r.json();
  return {
    symbol: j.symbol || ticker,
    price: typeof j.price === "number" ? j.price : null,
    previousClose: j.previous_close ?? null,
    currency: j.currency,
    marketState: j.market_state ?? null,
    fetchedAt: Date.now(),
  };
}
