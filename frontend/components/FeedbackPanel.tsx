"use client";

import { useState } from "react";

interface FeedbackPanelProps {
  aiRecommendation: string;
  aiBuffettScore: number;
  aiConfidence: number;
  onDecision: (decision: "buy" | "sell" | "hold" | "ignore", reasoning?: string) => void;
}

export default function FeedbackPanel({
  aiRecommendation,
  aiBuffettScore,
  aiConfidence,
  onDecision,
}: FeedbackPanelProps) {
  const [selectedDecision, setSelectedDecision] = useState<string | null>(null);
  const [reasoning, setReasoning] = useState("");

  const handleSubmit = () => {
    if (selectedDecision) {
      onDecision(selectedDecision as any, reasoning || undefined);
      setSelectedDecision(null);
      setReasoning("");
    }
  };

  const getRecommendationColor = (rec: string) => {
    if (rec === "strong_buy" || rec === "buy") return "text-positive";
    if (rec === "strong_sell" || rec === "sell") return "text-negative";
    return "text-primary";
  };

  const getButtonColor = (decision: string) => {
    if (selectedDecision === decision) {
      if (decision === "buy" || decision === "strong_buy") return "bg-positive text-white";
      if (decision === "sell" || decision === "strong_sell") return "bg-negative text-white";
      return "bg-gray-600 text-white";
    }
    return "bg-white text-primary border-2 border-gray-300 hover:border-gray-400";
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <h3 className="text-lg font-semibold text-primary mb-4">
        Your Decision vs AI Recommendation
      </h3>

      {/* AI Recommendation Display */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-semibold text-primary">AI Recommendation</span>
          <span className={`text-xl font-bold ${getRecommendationColor(aiRecommendation || "hold")}`}>
            {(aiRecommendation || "HOLD").toUpperCase().replace("_", " ")}
          </span>
        </div>
        <div className="flex justify-between text-sm text-gray-600">
          <span>Buffett Score: {((aiBuffettScore || 0) * 100).toFixed(0)}%</span>
          <span>Confidence: {((aiConfidence || 0) * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* User Decision Buttons */}
      <div className="mb-4">
        <label className="block text-sm font-semibold text-primary mb-2">
          What did you decide?
        </label>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setSelectedDecision("buy")}
            className={`py-3 px-4 rounded-lg font-semibold transition-all ${getButtonColor("buy")}`}
          >
            BUY
          </button>
          <button
            onClick={() => setSelectedDecision("sell")}
            className={`py-3 px-4 rounded-lg font-semibold transition-all ${getButtonColor("sell")}`}
          >
            SELL
          </button>
          <button
            onClick={() => setSelectedDecision("hold")}
            className={`py-3 px-4 rounded-lg font-semibold transition-all ${getButtonColor("hold")}`}
          >
            HOLD
          </button>
          <button
            onClick={() => setSelectedDecision("ignore")}
            className={`py-3 px-4 rounded-lg font-semibold transition-all ${getButtonColor("ignore")}`}
          >
            IGNORE
          </button>
        </div>
      </div>

      {/* Reasoning Input */}
      <div className="mb-4">
        <label className="block text-sm font-semibold text-primary mb-2">
          Your reasoning (optional)
        </label>
        <textarea
          value={reasoning}
          onChange={(e) => setReasoning(e.target.value)}
          placeholder="Why did you make this decision? What factors did the AI miss?"
          className="w-full p-3 border-2 border-gray-300 rounded-lg focus:border-positive focus:outline-none resize-none"
          rows={3}
        />
      </div>

      {/* Learning Info */}
      <div className="mb-4 p-3 bg-blue-50 rounded-lg">
        <p className="text-xs text-primary">
          <strong>Learning Mode:</strong> Your decision will be recorded and compared 
          with the actual outcome after 3 months. If you consistently beat the AI on 
          specific signals, the system will adjust its weights accordingly.
        </p>
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!selectedDecision}
        className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
          selectedDecision
            ? "bg-positive text-white hover:opacity-90"
            : "bg-gray-300 text-gray-500 cursor-not-allowed"
        }`}
      >
        Record Decision
      </button>

      {/* Decision History Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          This helps the AI learn from your intuition and improve future recommendations.
        </p>
      </div>
    </div>
  );
}
