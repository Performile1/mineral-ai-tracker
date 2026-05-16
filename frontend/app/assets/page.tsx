"use client";

import { useState, useEffect } from "react";
import AssetDetail from "@/components/AssetDetail";

interface Asset {
  id: string;
  ticker: string;
  name: string;
  asset_type: "stock" | "fund" | "etf";
  commodity_type: string;
  country_code: string;
  exchange: string;
  buffett_score: number;
  confidence_score: number;
  current_price: number;
  price_change_30d: number;
  trading_url: string;
  avanza_verified: boolean;
  avanza_url?: string;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "stock" | "fund" | "etf">("all");
  const [verificationFilter, setVerificationFilter] = useState<"all" | "verified" | "unverified">("all");
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

  useEffect(() => {
    fetchAssets();
  }, []);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      // In production, fetch from API
      // const response = await fetch("/api/assets");
      // const data = await response.json();
      
      // Placeholder data for now
      setAssets([
        {
          id: "1",
          ticker: "BOLID",
          name: "Boliden AB",
          asset_type: "stock",
          commodity_type: "copper",
          country_code: "SE",
          exchange: "OMXSTO",
          buffett_score: 0.75,
          confidence_score: 0.82,
          current_price: 245.50,
          price_change_30d: 8.2,
          trading_url: "https://www.avanza.se/aktier/om-aktien.html/5436/boliden",
          avanza_verified: true,
          avanza_url: "https://www.avanza.se/aktier/om-aktien.html/5436/boliden",
        },
        {
          id: "2",
          ticker: "LKAB",
          name: "LKAB (Luleå)",
          asset_type: "stock",
          commodity_type: "iron_ore",
          country_code: "SE",
          exchange: "OMXSTO",
          buffett_score: 0.82,
          confidence_score: 0.78,
          current_price: 180.25,
          price_change_30d: 12.5,
          trading_url: "https://www.avanza.se/aktier/om-aktien.html/1234/lkab",
          avanza_verified: false, // Not publicly traded
          avanza_url: undefined,
        },
        {
          id: "3",
          ticker: "NKG",
          name: "Nordic Gold",
          asset_type: "stock",
          commodity_type: "gold",
          country_code: "SE",
          exchange: "NGM",
          buffett_score: 0.68,
          confidence_score: 0.65,
          current_price: 45.80,
          price_change_30d: -2.3,
          trading_url: "https://www.avanza.se/aktier/om-aktien.html/5678/nordic-gold",
          avanza_verified: true,
          avanza_url: "https://www.avanza.se/aktier/om-aktien.html/5678/nordic-gold",
        },
        {
          id: "4",
          ticker: "SUSTAIN",
          name: "Sustainability Fund",
          asset_type: "fund",
          commodity_type: "mixed",
          country_code: "SE",
          exchange: "Nordnet",
          buffett_score: 0.72,
          confidence_score: 0.70,
          current_price: 125.30,
          price_change_30d: 5.1,
          trading_url: "https://www.nordnet.se/fond.html/1234/sustainability-fund",
          avanza_verified: false, // Fund not on Avanza
          avanza_url: undefined,
        },
        {
          id: "5",
          ticker: "BATTERY",
          name: "Battery Materials ETF",
          asset_type: "etf",
          commodity_type: "lithium",
          country_code: "US",
          exchange: "NYSE",
          buffett_score: 0.85,
          confidence_score: 0.88,
          current_price: 89.40,
          price_change_30d: 15.3,
          trading_url: "https://www.avanza.se/etf/om-etf.html/9012/battery-materials",
          avanza_verified: true,
          avanza_url: "https://www.avanza.se/etf/om-etf.html/9012/battery-materials",
        },
        {
          id: "6",
          ticker: "EURONEXT",
          name: "Euronext Mining",
          asset_type: "stock",
          commodity_type: "copper",
          country_code: "FR",
          exchange: "EURONEXT",
          buffett_score: 0.70,
          confidence_score: 0.72,
          current_price: 32.15,
          price_change_30d: 3.8,
          trading_url: "https://www.avanza.se/aktier/om-aktien.html/3456/euronext-mining",
          avanza_verified: false, // Hallucinated company
          avanza_url: undefined,
        },
      ]);
    } catch (err) {
      console.error("Failed to load assets:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredAssets = assets.filter(
    (asset) => filter === "all" || asset.asset_type === filter
  ).filter(
    (asset) => 
      verificationFilter === "all" || 
      (verificationFilter === "verified" && asset.avanza_verified) ||
      (verificationFilter === "unverified" && !asset.avanza_verified)
  );

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-positive";
    if (score >= 0.6) return "text-[#4F8A8B]";
    if (score >= 0.4) return "text-gray-600";
    return "text-negative";
  };

  const getTypeBadge = (type: string) => {
    const colors = {
      stock: "bg-blue-100 text-blue-800",
      fund: "bg-green-100 text-green-800",
      etf: "bg-purple-100 text-purple-800",
    };
    return colors[type as keyof typeof colors] || "bg-gray-100 text-gray-800";
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Assets</h1>
        <p className="text-gray-600">Stocks, funds, and ETFs with mineral exposure</p>
      </div>

      {/* Filter Buttons */}
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="flex gap-2">
          {(["all", "stock", "fund", "etf"] as const).map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
                filter === type
                  ? "bg-primary text-white"
                  : "bg-white text-primary border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-2 ml-4">
          {(["all", "verified", "unverified"] as const).map((status) => (
            <button
              key={status}
              onClick={() => setVerificationFilter(status)}
              className={`px-4 py-2 rounded-lg font-semibold transition-colors ${
                verificationFilter === status
                  ? status === "verified" ? "bg-green-600 text-white" : status === "unverified" ? "bg-red-600 text-white" : "bg-primary text-white"
                  : "bg-white text-primary border border-gray-300 hover:bg-gray-50"
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Assets Table */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left p-4 font-semibold text-primary">Ticker</th>
              <th className="text-left p-4 font-semibold text-primary">Name</th>
              <th className="text-left p-4 font-semibold text-primary">Type</th>
              <th className="text-left p-4 font-semibold text-primary">Commodity</th>
              <th className="text-left p-4 font-semibold text-primary">Exchange</th>
              <th className="text-right p-4 font-semibold text-primary">Buffett Score</th>
              <th className="text-right p-4 font-semibold text-primary">Price</th>
              <th className="text-right p-4 font-semibold text-primary">30d Change</th>
              <th className="text-center p-4 font-semibold text-primary">Trade</th>
            </tr>
          </thead>
          <tbody>
            {filteredAssets.map((asset) => (
              <tr
                key={asset.id}
                className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                onClick={() => setSelectedAsset(asset)}
              >
                <td className="p-4 font-semibold text-primary">{asset.ticker}</td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    {asset.name}
                    {asset.avanza_verified ? (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">
                        ✓ Avanza
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded" title="Not verified on Avanza">
                        ⚠ Unverified
                      </span>
                    )}
                  </div>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getTypeBadge(asset.asset_type)}`}>
                    {asset.asset_type.toUpperCase()}
                  </span>
                </td>
                <td className="p-4 capitalize">{asset.commodity_type.replace(/_/g, " ")}</td>
                <td className="p-4 text-gray-600">{asset.exchange}</td>
                <td className="p-4 text-right">
                  <span className={`font-bold ${getScoreColor(asset.buffett_score)}`}>
                    {(asset.buffett_score * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="p-4 text-right font-semibold">
                  {asset.current_price.toFixed(2)} {asset.country_code === "SE" ? "SEK" : "USD"}
                </td>
                <td className={`p-4 text-right font-semibold ${asset.price_change_30d >= 0 ? "text-positive" : "text-negative"}`}>
                  {asset.price_change_30d >= 0 ? "+" : ""}{asset.price_change_30d.toFixed(1)}%
                </td>
                <td className="p-4 text-center">
                  <a
                    href={asset.trading_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="inline-block px-4 py-2 bg-positive text-white rounded-lg hover:opacity-90 transition-opacity font-semibold text-sm"
                  >
                    Trade
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Summary Stats */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-md p-4">
          <p className="text-sm text-gray-500">Total Assets</p>
          <p className="text-2xl font-bold text-primary">{filteredAssets.length}</p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-4">
          <p className="text-sm text-gray-500">Avg Buffett Score</p>
          <p className="text-2xl font-bold text-primary">
            {filteredAssets.length > 0
              ? ((filteredAssets.reduce((sum, a) => sum + a.buffett_score, 0) / filteredAssets.length) * 100).toFixed(0)
              : 0}%
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-4">
          <p className="text-sm text-gray-500">Best Performer</p>
          <p className="text-2xl font-bold text-positive">
            {filteredAssets.length > 0
              ? Math.max(...filteredAssets.map((a) => a.price_change_30d)).toFixed(1) + "%"
              : "N/A"}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow-md p-4">
          <p className="text-sm text-gray-500">Worst Performer</p>
          <p className="text-2xl font-bold text-negative">
            {filteredAssets.length > 0
              ? Math.min(...filteredAssets.map((a) => a.price_change_30d)).toFixed(1) + "%"
              : "N/A"}
          </p>
        </div>
      </div>

      {/* Asset Detail Modal */}
      {selectedAsset && (
        <AssetDetail
          asset={selectedAsset}
          onClose={() => setSelectedAsset(null)}
        />
      )}
    </div>
  );
}
