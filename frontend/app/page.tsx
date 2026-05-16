"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import PortfolioCard from "@/components/PortfolioCard";
import PredictionGraph from "@/components/PredictionGraph";
import MineralHeatmap from "@/components/MineralHeatmap";
import ScenarioSimulator from "@/components/ScenarioSimulator";
import ShadowPortfolio from "@/components/ShadowPortfolio";
import Portfolio from "@/components/Portfolio";
import DiscoveryRadar from "@/components/DiscoveryRadar";
import FeedbackPanel from "@/components/FeedbackPanel";
import DiscoveryHeatmap from "@/components/DiscoveryHeatmap";
import ManufacturingInsider from "@/components/ManufacturingInsider";
import ManufacturingContacts from "@/components/ManufacturingContacts";

export default function Home() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    // Check cookie for disclaimer acceptance
    const hasCookie = document.cookie.includes("disclaimer_accepted=true");
    const hasLocalStorage = localStorage.getItem("disclaimer_accepted") === "true";

    if (!hasCookie && !hasLocalStorage) {
      router.push("/onboarding");
    }
  }, [mounted, router]);

  if (!mounted) {
    return null; // Prevent hydration mismatch
  }

  return (
    <main className="min-h-screen bg-background text-primary">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Mineral AI Tracker</h1>
          <p className="text-gray-600">Buffett-Radar: Deterministic, self-learning investment tool for mineral assets</p>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Portfolio Overview */}
          <div className="lg:col-span-2">
            <Portfolio />
          </div>

          {/* Shadow Portfolio */}
          <div>
            <ShadowPortfolio />
          </div>

          {/* Mineral Heatmap */}
          <div>
            <MineralHeatmap />
          </div>

          {/* Scenario Simulator */}
          <div className="lg:col-span-2">
            <ScenarioSimulator />
          </div>

          {/* Discovery Radar */}
          <div>
            <DiscoveryRadar />
          </div>

          {/* Discovery Heatmap */}
          <div className="lg:col-span-2">
            <DiscoveryHeatmap />
          </div>

          {/* Manufacturing Insider Investments */}
          <div className="lg:col-span-2">
            <ManufacturingInsider />
          </div>

          {/* Manufacturing Contact Network */}
          <div className="lg:col-span-2">
            <ManufacturingContacts />
          </div>

          {/* Feedback Panel */}
          <div className="lg:col-span-2">
            <FeedbackPanel
              aiRecommendation="buy"
              aiBuffettScore={0.75}
              aiConfidence={0.82}
              onDecision={(decision, reasoning) => console.log("Decision:", decision, reasoning)}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
