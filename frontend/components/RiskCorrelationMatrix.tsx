"use client";

interface Props {
  assets?: string[];
  matrix?: number[][]; // square, values in [-1, 1]
  title?: string;
}

const DEFAULT_ASSETS = ["Cu", "Au", "Li", "U", "Ni", "Co", "REE"];

const DEFAULT_MATRIX: number[][] = [
  [1.0, 0.42, 0.58, 0.31, 0.66, 0.55, 0.39],
  [0.42, 1.0, 0.18, -0.05, 0.22, 0.27, 0.11],
  [0.58, 0.18, 1.0, 0.45, 0.71, 0.69, 0.48],
  [0.31, -0.05, 0.45, 1.0, 0.39, 0.42, 0.33],
  [0.66, 0.22, 0.71, 0.39, 1.0, 0.82, 0.58],
  [0.55, 0.27, 0.69, 0.42, 0.82, 1.0, 0.61],
  [0.39, 0.11, 0.48, 0.33, 0.58, 0.61, 1.0],
];

/**
 * Risk Correlation Matrix (PRD v8.3 §5.4)
 * Color-coded heatmap: petroleum for low/negative, terracotta for high.
 */
export default function RiskCorrelationMatrix({
  assets = DEFAULT_ASSETS,
  matrix = DEFAULT_MATRIX,
  title = "Risk Correlation Matrix",
}: Props) {
  const colorFor = (v: number) => {
    // -1 (positive/safe) → +1 (terracotta/risk)
    const t = (v + 1) / 2; // 0..1
    const r = Math.round(79 + (179 - 79) * t); // 4F→B3
    const g = Math.round(138 + (90 - 138) * t); // 8A→5A
    const b = Math.round(139 + (68 - 139) * t); // 8B→44
    const alpha = 0.18 + Math.abs(v) * 0.55;
    return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(2)})`;
  };

  return (
    <div className="bg-surface border border-gray-200 rounded-lg p-5 h-full">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-text uppercase tracking-wider">{title}</h3>
        <div className="flex items-center gap-2 text-[10px] text-muted">
          <span className="inline-block w-3 h-3 rounded" style={{ background: colorFor(-1) }} />
          low
          <span className="inline-block w-3 h-3 rounded" style={{ background: colorFor(1) }} />
          high
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="text-xs border-collapse">
          <thead>
            <tr>
              <th className="w-8" />
              {assets.map((a) => (
                <th key={a} className="px-2 py-1 text-text font-semibold">
                  {a}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={i}>
                <th className="px-2 py-1 text-right text-text font-semibold">{assets[i]}</th>
                {row.map((v, j) => (
                  <td
                    key={j}
                    className="px-2 py-1 text-center tabular-nums border border-white"
                    style={{ background: colorFor(v) }}
                    title={`${assets[i]} ↔ ${assets[j]} = ${v.toFixed(2)}`}
                  >
                    <span className={Math.abs(v) > 0.6 ? "font-semibold" : ""}>{v.toFixed(2)}</span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
