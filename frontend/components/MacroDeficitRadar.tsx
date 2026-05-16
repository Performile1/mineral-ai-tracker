"use client";

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";

export interface DeficitDatum {
  axis: string;        // commodity / theme
  deficit: number;     // 0-100 (severity)
  demand: number;      // 0-100 (demand pressure)
}

interface Props {
  data?: DeficitDatum[];
  title?: string;
}

/**
 * Macro Deficit Radar (PRD v8.3 §5.6)
 *
 * Plots BOTH supply deficit severity and end-demand pressure across the
 * key strategic sectors driving mineral demand:
 *   - Solar / PV (Cu, Ag, Si)
 *   - Aerospace (Ti, REE, Ni)
 *   - Robotics & EV (Cu, Li, Co, Ni, REE)
 *   - Water grid / infra (Cu, Steel)
 *   - Defense (W, REE, Cu)
 *   - Nuclear (U, Zr)
 */
const DEFAULT_DATA: DeficitDatum[] = [
  { axis: "Solar PV",       deficit: 62, demand: 82 },
  { axis: "Aerospace",      deficit: 48, demand: 70 },
  { axis: "Robotics/EV",    deficit: 78, demand: 92 },
  { axis: "Water Grid",     deficit: 55, demand: 65 },
  { axis: "Defense",        deficit: 81, demand: 88 },
  { axis: "Nuclear (U/Zr)", deficit: 74, demand: 76 },
];

export default function MacroDeficitRadar({
  data = DEFAULT_DATA,
  title = "Macro Deficit Radar",
}: Props) {
  return (
    <div className="bg-surface border border-gray-200 rounded-lg p-5 h-full flex flex-col">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-sm font-semibold text-text uppercase tracking-wider">{title}</h3>
        <span className="text-[10px] text-muted">0-100 severity</span>
      </div>
      <div className="flex-1 min-h-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="75%">
            <PolarGrid stroke="#E5E0DA" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: "#2F2F2F", fontSize: 11 }} />
            <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: "#6B6B6B", fontSize: 10 }} />
            <Radar
              name="Supply Deficit"
              dataKey="deficit"
              stroke="#B35A44"
              fill="#B35A44"
              fillOpacity={0.35}
            />
            <Radar
              name="Demand Pressure"
              dataKey="demand"
              stroke="#4F8A8B"
              fill="#4F8A8B"
              fillOpacity={0.25}
            />
            <Legend wrapperStyle={{ fontSize: 11, color: "#2F2F2F" }} />
            <Tooltip
              contentStyle={{
                background: "#FFFFFF",
                border: "1px solid #E5E0DA",
                fontSize: 12,
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
