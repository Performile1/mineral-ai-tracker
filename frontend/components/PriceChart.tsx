"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from "recharts";
import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";

interface AssetEvent {
  id: string;
  ticker: string;
  published_at: string;
  title: string;
  url?: string;
  source_authority_score: number;
  ai_summary?: string;
  price_impact_4h?: number;
}

interface PriceChartProps {
  historicalData: Array<{
    date: string;
    price: number;
  }>;
  ticker?: string;
  targetPrice?: number;
  stopLoss?: number;
  currentPrice?: number;
}

export default function PriceChart({
  historicalData,
  ticker,
  targetPrice,
  stopLoss,
  currentPrice,
}: PriceChartProps) {
  const [events, setEvents] = useState<AssetEvent[]>([]);
  const [hoveredEvent, setHoveredEvent] = useState<AssetEvent | null>(null);
  const [loading, setLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch events for this ticker
  useEffect(() => {
    if (!ticker) return;

    const fetchEvents = async () => {
      setLoading(true);
      try {
        const res = await apiFetch(`${apiUrl}/api/events/${ticker}?limit=50`);
        const data = await res.json();
        setEvents(data.events || []);
      } catch (err) {
        console.error("Failed to fetch events:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchEvents();
  }, [ticker, apiUrl]);

  // Merge events with historical data for rendering
  const dataWithEvents = historicalData.map((point) => {
    const eventAtDate = events.find(
      (e) => new Date(e.published_at).toISOString().split('T')[0] === point.date.split('T')[0]
    );
    return {
      ...point,
      event: eventAtDate || null,
    };
  });

  return (
    <div className="w-full h-96 bg-white rounded-lg shadow-md p-4">
      <h3 className="text-lg font-semibold text-primary mb-4">
        Price Chart with Event Correlation
      </h3>

      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dataWithEvents} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />

          <XAxis
            dataKey="date"
            stroke="#2F2F2F"
            fontSize={12}
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleDateString("sv-SE", { month: "short", day: "numeric" });
            }}
          />

          <YAxis
            stroke="#2F2F2F"
            fontSize={12}
            domain={["auto", "auto"]}
            tickFormatter={(value) => `${value.toFixed(0)}`}
          />

          <Tooltip
            content={<CustomTooltip hoveredEvent={hoveredEvent} />}
            cursor={{ stroke: "#2F2F2F", strokeWidth: 1, strokeDasharray: "3 3" }}
          />

          <Legend />

          {/* Historical Price Line */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#2F2F2F"
            strokeWidth={2}
            dot={false}
            name="Price"
            connectNulls={false}
          />

          {/* Event Markers - Render based on authority score */}
          {dataWithEvents.map((point, index) => {
            if (!point.event) return null;

            const authority = point.event.source_authority_score;
            const size = authority >= 1.0 ? 8 : authority >= 0.8 ? 6 : 4;
            const opacity = authority >= 1.0 ? 1.0 : authority >= 0.8 ? 0.8 : 0.5;
            const color = point.event.price_impact_4h && point.event.price_impact_4h > 0 
              ? "#4F8A8B" // Green for positive impact
              : point.event.price_impact_4h && point.event.price_impact_4h < 0
              ? "#B35A44" // Red for negative impact
              : "#2F2F2F"; // Gray for unknown

            return (
              <ReferenceDot
                key={point.event.id}
                x={index}
                y={point.price}
                r={size}
                fill={color}
                stroke={color}
                opacity={opacity}
                onMouseEnter={() => setHoveredEvent(point.event)}
                onMouseLeave={() => setHoveredEvent(null)}
              />
            );
          })}

          {/* Target Price Line */}
          {targetPrice && (
            <ReferenceLine
              y={targetPrice}
              stroke="#4F8A8B"
              strokeWidth={2}
              strokeDasharray="6 6"
              label={{
                value: "Target",
                position: "right",
                fill: "#4F8A8B",
                fontSize: 12,
              }}
            />
          )}

          {/* Stop Loss Line */}
          {stopLoss && (
            <ReferenceLine
              y={stopLoss}
              stroke="#B35A44"
              strokeWidth={2}
              strokeDasharray="6 6"
              label={{
                value: "Stop Loss",
                position: "right",
                fill: "#B35A44",
                fontSize: 12,
              }}
            />
          )}

          {/* Current Price Line */}
          {currentPrice && (
            <ReferenceLine
              y={currentPrice}
              stroke="#2F2F2F"
              strokeWidth={1}
              strokeDasharray="4 4"
              label={{
                value: "Current",
                position: "right",
                fill: "#2F2F2F",
                fontSize: 12,
              }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>

      {/* Event Legend */}
      <div className="mt-4 flex items-center gap-4 text-xs text-gray-600">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-[#2F2F2F]" />
          <span>Category C (News Articles)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-4 h-4 rounded-full bg-[#2F2F2F]" />
          <span>Category B (Press Releases)</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-5 h-5 rounded-full bg-[#2F2F2F]" />
          <span>Category A (Financial Reports)</span>
        </div>
      </div>
    </div>
  );
}

// Custom Tooltip Component
function CustomTooltip({ hoveredEvent }: { hoveredEvent: AssetEvent | null }) {
  if (!hoveredEvent) {
    return (
      <div
        style={{
          backgroundColor: "#F4F1EE",
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "8px",
        }}
      >
        <p style={{ color: "#2F2F2F", margin: 0 }}>Price</p>
      </div>
    );
  }

  const impactColor = hoveredEvent.price_impact_4h && hoveredEvent.price_impact_4h > 0
    ? "#4F8A8B"
    : hoveredEvent.price_impact_4h && hoveredEvent.price_impact_4h < 0
    ? "#B35A44"
    : "#2F2F2F";

  return (
    <div
      style={{
        backgroundColor: "#F4F1EE",
        border: "1px solid #ccc",
        borderRadius: "8px",
        padding: "12px",
        minWidth: "250px",
      }}
    >
      <h4 style={{ color: "#2F2F2F", margin: "0 0 8px 0", fontWeight: "bold" }}>
        {hoveredEvent.title}
      </h4>
      
      {hoveredEvent.ai_summary && (
        <p style={{ color: "#2F2F2F", margin: "0 0 8px 0", fontSize: "12px" }}>
          {hoveredEvent.ai_summary}
        </p>
      )}

      {hoveredEvent.price_impact_4h !== null && hoveredEvent.price_impact_4h !== undefined && (
        <div style={{ marginTop: "8px" }}>
          <span style={{ color: "#2F2F2F", fontSize: "11px" }}>Price Impact (4h): </span>
          <span style={{ color: impactColor, fontSize: "11px", fontWeight: "bold" }}>
            {hoveredEvent.price_impact_4h > 0 ? "+" : ""}{hoveredEvent.price_impact_4h.toFixed(2)}%
          </span>
        </div>
      )}

      {hoveredEvent.url && (
        <div style={{ marginTop: "8px" }}>
          <a
            href={hoveredEvent.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: "#4F8A8B", fontSize: "11px", textDecoration: "underline" }}
          >
            Read more →
          </a>
        </div>
      )}

      <div style={{ marginTop: "8px", fontSize: "10px", color: "#666" }}>
        Authority: {hoveredEvent.source_authority_score.toFixed(2)}
      </div>
    </div>
  );
}
