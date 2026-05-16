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
} from "recharts";

interface PredictionGraphProps {
  historicalData: Array<{
    date: string;
    price: number;
  }>;
  predictedData?: Array<{
    date: string;
    price: number;
    lowerBound?: number;
    upperBound?: number;
  }>;
  targetPrice?: number;
  stopLoss?: number;
  currentPrice?: number;
}

export default function PredictionGraph({
  historicalData,
  predictedData,
  targetPrice,
  stopLoss,
  currentPrice,
}: PredictionGraphProps) {
  // Combine historical and predicted data
  const allData = [
    ...historicalData,
    ...(predictedData || []),
  ];

  return (
    <div className="w-full h-96 bg-white rounded-lg shadow-md p-4">
      <h3 className="text-lg font-semibold text-primary mb-4">
        Price Prediction & Risk Management
      </h3>
      
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={allData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
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
            contentStyle={{
              backgroundColor: "#F4F1EE",
              border: "1px solid #ccc",
              borderRadius: "8px",
            }}
            labelStyle={{ color: "#2F2F2F" }}
            formatter={(value: number) => [`${value.toFixed(2)} SEK`, "Price"]}
          />
          
          <Legend />
          
          {/* Historical Price Line */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#2F2F2F"
            strokeWidth={2}
            dot={false}
            name="Historical Price"
            connectNulls={false}
          />
          
          {/* Predicted Price Line (dashed) */}
          {predictedData && predictedData.length > 0 && (
            <Line
              type="monotone"
              dataKey="price"
              stroke="#4F8A8B"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              name="Predicted Price"
              connectNulls={false}
            />
          )}
          
          {/* Confidence Interval Bounds */}
          {predictedData && predictedData.some(d => d.lowerBound) && (
            <>
              <Line
                type="monotone"
                dataKey="lowerBound"
                stroke="#4F8A8B"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
                name="Lower Bound (95% CI)"
                opacity={0.5}
              />
              <Line
                type="monotone"
                dataKey="upperBound"
                stroke="#4F8A8B"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={false}
                name="Upper Bound (95% CI)"
                opacity={0.5}
              />
            </>
          )}
          
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
    </div>
  );
}
