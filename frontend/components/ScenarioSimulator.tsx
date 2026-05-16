"use client";

import { useState, useEffect } from "react";

interface Scenario {
  id: string;
  name: string;
  description: string;
  scenario_type: string;
  affected_commodity: string;
  price_impact_percentage: number;
  duration_days: number;
  historical_correlation: number;
  similar_historical_event: string;
}

interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  portfolio_value_before: number;
  portfolio_value_after: number;
  portfolio_impact_percentage: number;
  asset_impacts: Array<{
    asset_ticker: string;
    price_impact_percentage: number;
    value_impact_percentage: number;
  }>;
}

export default function ScenarioSimulator() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      setLoading(true);
      // In production, fetch from API
      // const response = await fetch("/api/scenarios");
      // const data = await response.json();
      
      // Placeholder scenarios from database
      setScenarios([
        {
          id: "1",
          name: "China Graphite Export Ban",
          description: "China blocks graphite export to EU/US, causing supply crisis",
          scenario_type: "supply_disruption",
          affected_commodity: "graphite",
          price_impact_percentage: -50,
          duration_days: 180,
          historical_correlation: 0.85,
          similar_historical_event: "China rare earth export restrictions 2010"
        },
        {
          id: "2",
          name: "Copper Price Collapse",
          description: "Global economic slowdown causes copper to drop 30%",
          scenario_type: "commodity_shock",
          affected_commodity: "copper",
          price_impact_percentage: -30,
          duration_days: 90,
          historical_correlation: 0.70,
          similar_historical_event: "2008 Financial Crisis"
        },
        {
          id: "3",
          name: "Lithium Glut",
          description: "Oversupply causes lithium prices to crash",
          scenario_type: "commodity_shock",
          affected_commodity: "lithium",
          price_impact_percentage: -40,
          duration_days: 365,
          historical_correlation: 0.60,
          similar_historical_event: "Lithium price crash 2018"
        },
        {
          id: "4",
          name: "EU CRMA Implementation",
          description: "EU Critical Raw Materials Act imposes strict regulations",
          scenario_type: "regulatory",
          affected_commodity: "multiple",
          price_impact_percentage: 10,
          duration_days: 365,
          historical_correlation: 0.45,
          similar_historical_event: "EU GDPR implementation"
        },
        {
          id: "5",
          name: "Mining Strike in Chile",
          description: "Major copper mines in Chile go on strike",
          scenario_type: "supply_disruption",
          affected_commodity: "copper",
          price_impact_percentage: 25,
          duration_days: 60,
          historical_correlation: 0.55,
          similar_historical_event: "Chile mining strike 2011"
        }
      ]);
    } catch (err) {
      setError("Failed to load scenarios");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const runScenario = async (scenario: Scenario) => {
    try {
      setLoading(true);
      setSelectedScenario(scenario);
      
      // In production, fetch from API
      // const response = await fetch("/api/scenarios/run", {
      //   method: "POST",
      //   body: JSON.stringify({ scenario_id: scenario.id })
      // });
      // const data = await response.json();
      
      // Placeholder result
      setResult({
        scenario_id: scenario.id,
        scenario_name: scenario.name,
        portfolio_value_before: 1000000,
        portfolio_value_after: 850000,
        portfolio_impact_percentage: -15,
        asset_impacts: [
          { asset_ticker: "BOL", price_impact_percentage: -20, value_impact_percentage: -20 },
          { asset_ticker: "NEXA", price_impact_percentage: -15, value_impact_percentage: -15 }
        ]
      });
      
    } catch (err) {
      setError("Failed to run scenario");
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

  const getImpactColor = (value: number) => {
    if (value >= 0) return "text-positive";
    return "text-negative";
  };

  if (loading && !scenarios.length) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Black Swan Scenario Engine</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Black Swan Scenario Engine</h2>
        <div className="text-negative text-center py-8">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-primary">Black Swan Scenario Engine</h2>
        <button
          onClick={fetchScenarios}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Uppdatera
        </button>
      </div>

      {/* Info Banner */}
      <div className="bg-orange-50 border-l-4 border-negative p-4 mb-6">
        <p className="text-sm text-primary">
          <strong>Stresstest:</strong> Simulera extrema händelser för att testa din portföljs motståndskraft.
          Resultat baseras på historisk korrelation vid liknande kriser.
        </p>
      </div>

      {/* Scenario Selection */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-primary mb-4">Välj Scenario</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {scenarios.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => runScenario(scenario)}
              disabled={loading}
              className={`p-4 border rounded-lg text-left hover:shadow-md transition-shadow ${
                selectedScenario?.id === scenario.id
                  ? "border-primary bg-gray-50"
                  : "border-gray-200"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-primary">{scenario.name}</h4>
                <span className={`text-sm font-bold ${
                  scenario.price_impact_percentage >= 0 ? 'text-positive' : 'text-negative'
                }`}>
                  {scenario.price_impact_percentage >= 0 ? '+' : ''}{scenario.price_impact_percentage}%
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-2">{scenario.description}</p>
              <div className="flex justify-between text-xs text-gray-500">
                <span>Korrelation: {(scenario.historical_correlation * 100).toFixed(0)}%</span>
                <span>Varaktighet: {scenario.duration_days} dagar</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="border-t border-gray-200 pt-6">
          <h3 className="text-lg font-semibold text-primary mb-4">Resultat: {result.scenario_name}</h3>
          
          {/* Portfolio Impact */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">Portföljvärde Före</p>
              <p className="text-2xl font-bold text-primary">{formatCurrency(result.portfolio_value_before)}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">Portföljvärde Efter</p>
              <p className="text-2xl font-bold text-primary">{formatCurrency(result.portfolio_value_after)}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-sm text-gray-600">Påverkan</p>
              <p className={`text-2xl font-bold ${getImpactColor(result.portfolio_impact_percentage)}`}>
                {result.portfolio_impact_percentage >= 0 ? '+' : ''}{result.portfolio_impact_percentage.toFixed(2)}%
              </p>
            </div>
          </div>

          {/* Asset Breakdown */}
          <div className="mb-4">
            <h4 className="font-semibold text-primary mb-3">Tillgångspåverkan</h4>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 px-4 text-sm font-semibold text-primary">Tillgång</th>
                    <th className="text-right py-2 px-4 text-sm font-semibold text-primary">Prispåverkan</th>
                    <th className="text-right py-2 px-4 text-sm font-semibold text-primary">Värdepåverkan</th>
                  </tr>
                </thead>
                <tbody>
                  {result.asset_impacts.map((impact, index) => (
                    <tr key={index} className="border-b border-gray-100">
                      <td className="py-2 px-4 text-sm font-semibold text-primary">{impact.asset_ticker}</td>
                      <td className="py-2 px-4 text-right">
                        <span className={`text-sm font-bold ${getImpactColor(impact.price_impact_percentage)}`}>
                          {impact.price_impact_percentage >= 0 ? '+' : ''}{impact.price_impact_percentage.toFixed(2)}%
                        </span>
                      </td>
                      <td className="py-2 px-4 text-right">
                        <span className={`text-sm font-bold ${getImpactColor(impact.value_impact_percentage)}`}>
                          {impact.value_impact_percentage >= 0 ? '+' : ''}{impact.value_impact_percentage.toFixed(2)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Historical Context */}
          <div className="bg-blue-50 border-l-4 border-primary p-4">
            <p className="text-sm text-primary">
              <strong>Historisk kontext:</strong> Denna scenario baseras på "{selectedScenario?.similar_historical_event}" 
              med en historisk korrelation på {(selectedScenario?.historical_correlation || 0) * 100}%.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
