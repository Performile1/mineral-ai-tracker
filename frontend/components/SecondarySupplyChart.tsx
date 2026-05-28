"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { apiFetch } from "@/lib/apiClient";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface SpreadPoint {
  date: string;
  material_name: string;
  price_spread_usd: number | null;
  is_critical_squeeze: boolean;
}

interface ApiResponse {
  items: SpreadPoint[];
  spread_floor_usd: number;
  source: "db" | "mock";
}

interface ChartRow {
  date: string;
  copper: number | null;
  blackMass: number | null;
  squeeze: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function pivot(items: SpreadPoint[]): ChartRow[] {
  const map = new Map<string, ChartRow>();
  for (const pt of items) {
    if (!map.has(pt.date)) {
      map.set(pt.date, { date: pt.date, copper: null, blackMass: null, squeeze: false });
    }
    const row = map.get(pt.date)!;
    if (pt.material_name === "Copper Scrap") {
      row.copper = pt.price_spread_usd;
      row.squeeze = pt.is_critical_squeeze;
    } else if (pt.material_name === "Black Mass Index") {
      row.blackMass = pt.price_spread_usd;
    }
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------
function CustomTooltip({ active, payload, label, floor }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs text-white shadow-xl">
      <p className="font-semibold mb-1 text-gray-300">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-bold">${p.value?.toFixed(3)}</span>
          {p.name === "Copper Scrap" && p.value !== null && p.value < floor && (
            <span className="ml-1 text-red-400 font-bold">⚠ SQUEEZE</span>
          )}
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function SecondarySupplyChart() {
  const [rows, setRows] = useState<ChartRow[]>([]);
  const [floor, setFloor] = useState(0.10);
  const [source, setSource] = useState<"db" | "mock" | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    apiFetch("/api/macro/secondary-supply")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<ApiResponse>;
      })
      .then((data) => {
        if (!mounted) return;
        setRows(pivot(data.items));
        setFloor(data.spread_floor_usd);
        setSource(data.source);
      })
      .catch((e) => {
        if (mounted) setError(String(e));
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const squeezeDays = rows.filter((r) => r.squeeze).length;

  return (
    <div className="bg-gray-900 border border-cyan-800/40 rounded-xl p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-base">♻️</span>
          <h3 className="text-xs font-bold text-cyan-400 uppercase tracking-widest">
            Secondary Supply Pressure
          </h3>
          {squeezeDays > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-900/60 border border-red-700 text-red-300">
              {squeezeDays}d SQUEEZE
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {source === "mock" && (
            <span className="text-[10px] text-amber-500 border border-amber-700/50 rounded px-1.5 py-0.5">
              demo data
            </span>
          )}
          {source === "db" && (
            <span className="text-[10px] text-green-500 border border-green-700/50 rounded px-1.5 py-0.5">
              live
            </span>
          )}
          <span className="text-[10px] text-gray-500">30d · $/unit</span>
        </div>
      </div>

      <p className="text-[10px] text-gray-500 mb-3 ml-6">
        When Copper Scrap spread falls below the red line, smelter economics break down.
      </p>

      {loading && (
        <div className="flex items-center justify-center h-52 text-sm text-gray-500">
          Loading spread data…
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-52 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="date"
              tickFormatter={fmtDate}
              tick={{ fill: "#6b7280", fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: "#374151" }}
              interval={4}
            />
            <YAxis
              tick={{ fill: "#6b7280", fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${v.toFixed(2)}`}
              width={48}
            />
            <Tooltip
              content={<CustomTooltip floor={floor} />}
              cursor={{ stroke: "#374151" }}
            />
            <Legend
              wrapperStyle={{ fontSize: "10px", color: "#9ca3af", paddingTop: "6px" }}
            />

            {/* Critical squeeze reference line */}
            <ReferenceLine
              y={floor}
              stroke="#ef4444"
              strokeDasharray="3 3"
              label={{
                value: `Critical Squeeze (< $${floor.toFixed(2)})`,
                fill: "#ef4444",
                fontSize: 9,
                position: "insideBottomRight",
              }}
            />

            <Line
              type="monotone"
              dataKey="copper"
              name="Copper Scrap"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#22d3ee" }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="blackMass"
              name="Black Mass Index"
              stroke="#a78bfa"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#a78bfa" }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
