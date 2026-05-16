"use client";

import { useState, useEffect } from "react";

interface Discovery {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  commodity: string;
  discovery_date: string;
  status: "prospecting" | "exploration" | "development" | "production";
}

interface NearbyCompany {
  id: string;
  name: string;
  ticker: string;
  distance_km: number;
  asset_type: "stock" | "fund";
  buffett_score: number;
  trading_url: string;
}

export default function DiscoveryHeatmap() {
  const [discoveries, setDiscoveries] = useState<Discovery[]>([]);
  const [selectedDiscovery, setSelectedDiscovery] = useState<Discovery | null>(null);
  const [nearbyCompanies, setNearbyCompanies] = useState<NearbyCompany[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDiscoveries();
  }, []);

  const fetchDiscoveries = async () => {
    try {
      setLoading(true);
      // Placeholder data for now
      setDiscoveries([
        {
          id: "1",
          name: "Bergslagen Copper Zone",
          latitude: 59.5,
          longitude: 15.0,
          commodity: "copper",
          discovery_date: "2025-04-15",
          status: "exploration",
        },
        {
          id: "2",
          name: "Norrbotten Lithium",
          latitude: 67.5,
          longitude: 20.5,
          commodity: "lithium",
          discovery_date: "2025-03-20",
          status: "prospecting",
        },
        {
          id: "3",
          name: "Skåne Rare Earth",
          latitude: 56.0,
          longitude: 14.0,
          commodity: "rare_earth",
          discovery_date: "2025-02-10",
          status: "development",
        },
        {
          id: "4",
          name: "Dalarna Gold Belt",
          latitude: 60.5,
          longitude: 14.5,
          commodity: "gold",
          discovery_date: "2025-01-25",
          status: "exploration",
        },
        {
          id: "5",
          name: "Värmland Nickel",
          latitude: 59.8,
          longitude: 13.5,
          commodity: "nickel",
          discovery_date: "2024-12-30",
          status: "production",
        },
      ]);
    } catch (err) {
      console.error("Failed to load discoveries:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchNearbyCompanies = async (discovery: Discovery) => {
    try {
      // Placeholder data for now
      setNearbyCompanies([
        {
          id: "1",
          name: "Boliden AB",
          ticker: "BOLID",
          distance_km: 45,
          asset_type: "stock",
          buffett_score: 0.75,
          trading_url: "https://www.avanza.se/aktier/om-aktien.html/5436/boliden",
        },
        {
          id: "2",
          name: "Nordic Mining",
          ticker: "NOMI",
          distance_km: 120,
          asset_type: "stock",
          buffett_score: 0.68,
          trading_url: "https://www.avanza.se/aktier/om-aktien.html/7890/nordic-mining",
        },
        {
          id: "3",
          name: "Mineral Fund",
          ticker: "MINF",
          distance_km: 85,
          asset_type: "fund",
          buffett_score: 0.72,
          trading_url: "https://www.nordnet.se/fond.html/2345/mineral-fund",
        },
      ]);
    } catch (err) {
      console.error("Failed to load nearby companies:", err);
    }
  };

  const handleDiscoveryClick = (discovery: Discovery) => {
    setSelectedDiscovery(discovery);
    fetchNearbyCompanies(discovery);
  };

  const getStatusColor = (status: string) => {
    const colors = {
      prospecting: "bg-yellow-100 text-yellow-800",
      exploration: "bg-blue-100 text-blue-800",
      development: "bg-purple-100 text-purple-800",
      production: "bg-green-100 text-green-800",
    };
    return colors[status as keyof typeof colors] || "bg-gray-100 text-gray-800";
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-positive";
    if (score >= 0.6) return "text-[#4F8A8B]";
    return "text-gray-600";
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Discovery Heatmap</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold text-primary mb-4">Discovery Heatmap & Nearby Companies</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Discovery Map */}
        <div className="bg-gray-50 rounded-lg p-4 min-h-[400px]">
          <h3 className="font-semibold text-primary mb-4">Discoveries</h3>
          <div className="space-y-3">
            {discoveries.map((discovery) => (
              <div
                key={discovery.id}
                onClick={() => handleDiscoveryClick(discovery)}
                className={`p-4 rounded-lg cursor-pointer transition-colors ${
                  selectedDiscovery?.id === discovery.id
                    ? "bg-primary text-white"
                    : "bg-white hover:bg-gray-100"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold">{discovery.name}</h4>
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    selectedDiscovery?.id === discovery.id
                      ? "bg-white text-primary"
                      : getStatusColor(discovery.status)
                  }`}>
                    {discovery.status}
                  </span>
                </div>
                <div className="text-sm opacity-80">
                  <p>Commodity: {discovery.commodity}</p>
                  <p>Discovered: {discovery.discovery_date}</p>
                  <p>Coords: {discovery.latitude.toFixed(2)}°N, {discovery.longitude.toFixed(2)}°E</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Nearby Companies */}
        <div className="bg-gray-50 rounded-lg p-4 min-h-[400px]">
          <h3 className="font-semibold text-primary mb-4">
            {selectedDiscovery ? `Nearby Companies (${selectedDiscovery.name})` : "Select a discovery"}
          </h3>
          {selectedDiscovery ? (
            <div className="space-y-3">
              {nearbyCompanies.length > 0 ? (
                nearbyCompanies.map((company) => (
                  <div key={company.id} className="bg-white p-4 rounded-lg">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="font-semibold text-primary">{company.name}</h4>
                        <p className="text-sm text-gray-600">{company.ticker}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        company.asset_type === "stock" ? "bg-blue-100 text-blue-800" : "bg-green-100 text-green-800"
                      }`}>
                        {company.asset_type.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-sm text-gray-600">Distance: {company.distance_km} km</span>
                      <span className={`font-bold ${getScoreColor(company.buffett_score)}`}>
                        {(company.buffett_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <a
                      href={company.trading_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block w-full text-center px-4 py-2 bg-positive text-white rounded-lg hover:opacity-90 transition-opacity font-semibold text-sm"
                    >
                      Trade {company.ticker}
                    </a>
                  </div>
                ))
              ) : (
                <p className="text-gray-500 text-center py-8">No nearby companies found</p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <p>Click on a discovery to see nearby companies</p>
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-100 rounded"></div>
            <span className="text-gray-600">Prospecting</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-blue-100 rounded"></div>
            <span className="text-gray-600">Exploration</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-purple-100 rounded"></div>
            <span className="text-gray-600">Development</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-100 rounded"></div>
            <span className="text-gray-600">Production</span>
          </div>
        </div>
      </div>
    </div>
  );
}
