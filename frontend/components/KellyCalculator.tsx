"use client";

import { useMemo, useState } from "react";

interface Props {
  defaultWinProb?: number; // 0-1
  defaultWinLossRatio?: number; // R-multiple
  defaultBankroll?: number;
  fractionalKelly?: number; // default 0.5 (Half-Kelly)
}

/**
 * Kelly Calculator (PRD v8.3 §5.3)
 *
 *   f* = (p * b - q) / b
 *   p = win prob, q = 1-p, b = win/loss payoff ratio
 *
 * We default to **Half-Kelly** which is industry-standard for real money to
 * reduce variance.
 */
export default function KellyCalculator({
  defaultWinProb = 0.6,
  defaultWinLossRatio = 2.0,
  defaultBankroll = 100_000,
  fractionalKelly = 0.5,
}: Props) {
  const [p, setP] = useState(defaultWinProb);
  const [b, setB] = useState(defaultWinLossRatio);
  const [bankroll, setBankroll] = useState(defaultBankroll);
  const [fraction, setFraction] = useState(fractionalKelly);

  const result = useMemo(() => {
    const q = 1 - p;
    const fullKelly = b > 0 ? (p * b - q) / b : 0;
    const adjusted = Math.max(0, fullKelly * fraction);
    const positionSize = bankroll * adjusted;
    return { fullKelly, adjusted, positionSize };
  }, [p, b, bankroll, fraction]);

  return (
    <div className="bg-surface border border-gray-200 rounded-lg p-5 h-full flex flex-col">
      <h3 className="text-sm font-semibold text-text uppercase tracking-wider mb-3">
        Kelly Calculator
      </h3>

      <div className="space-y-3 flex-1">
        <Field
          label="Win Probability"
          value={p}
          onChange={setP}
          min={0}
          max={1}
          step={0.01}
          suffix={`${(p * 100).toFixed(0)}%`}
        />
        <Field
          label="Win / Loss Ratio (R)"
          value={b}
          onChange={setB}
          min={0.1}
          max={10}
          step={0.1}
          suffix={`${b.toFixed(1)}x`}
        />
        <Field
          label="Fractional Kelly"
          value={fraction}
          onChange={setFraction}
          min={0.1}
          max={1}
          step={0.05}
          suffix={`${(fraction * 100).toFixed(0)}%`}
        />
        <div className="flex flex-col">
          <label className="text-[11px] uppercase text-muted mb-1">Bankroll (USD)</label>
          <input
            type="number"
            value={bankroll}
            onChange={(e) => setBankroll(Number(e.target.value) || 0)}
            className="border border-gray-300 rounded px-2 py-1 text-sm text-text"
          />
        </div>
      </div>

      <div className="border-t border-gray-200 mt-4 pt-3 space-y-1">
        <Row label="Full Kelly" value={`${(result.fullKelly * 100).toFixed(1)}%`} />
        <Row
          label={`Kelly × ${(fraction * 100).toFixed(0)}%`}
          value={`${(result.adjusted * 100).toFixed(1)}%`}
          highlight
        />
        <Row
          label="Position Size"
          value={`$${result.positionSize.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          highlight
        />
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  min,
  max,
  step,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  suffix: string;
}) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <label className="text-[11px] uppercase text-muted">{label}</label>
        <span className="text-xs font-semibold text-text tabular-nums">{suffix}</span>
      </div>
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

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-xs text-muted">{label}</span>
      <span
        className={`tabular-nums ${
          highlight ? "text-base font-bold text-positive" : "text-sm text-text"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
