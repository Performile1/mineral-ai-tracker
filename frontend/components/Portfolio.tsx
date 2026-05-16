"use client";

import { useState, useEffect, useCallback } from "react";
import PortfolioCard from "./PortfolioCard";
import { apiFetch } from "@/lib/apiClient";

interface Asset {
  id: string;
  ticker: string;
  name: string;
  current_price?: number;
  buffett_score?: number;
  confidence_score?: number;
  target_price?: number;
  stop_loss?: number;
  kelly_position_size?: number;
  logo_url?: string;
  avanza_url?: string;
  nordnet_url?: string;
  unrealized_pnl_percentage?: number;
}

export default function Portfolio() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Debounce search query (300ms delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch assets on mount
  useEffect(() => {
    fetchAssets();
  }, []);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      // In production, fetch from API
      // const response = await fetch("/api/assets");
      // const data = await response.json();
      // setAssets(data.assets);
      
      // Placeholder data for now
      setAssets([]);
    } catch (err) {
      console.error("Failed to fetch assets:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddAsset = async () => {
    if (!debouncedQuery.trim()) return;
    
    setIsAdding(true);
    setAddError(null);

    try {
      const response = await apiFetch(`/api/assets/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ticker: debouncedQuery,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setSearchQuery("");
        setDebouncedQuery("");
        await fetchAssets(); // Refresh asset list
      } else {
        setAddError(data.detail || "Failed to add asset");
      }
    } catch (err) {
      setAddError("Network error. Please try again.");
      console.error(err);
    } finally {
      setIsAdding(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleAddAsset();
    }
  };

  return (
    <div className="space-y-6">
      {/* Search Field with Debounce */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">
          Lägg till nytt bolag
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Sök efter ticker (t.ex. BOL, NEXA)..."
            className="flex-1 px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-positive focus:outline-none"
            disabled={isAdding}
          />
          <button
            onClick={handleAddAsset}
            disabled={isAdding || !debouncedQuery.trim()}
            className={`px-6 py-2 rounded-lg font-semibold transition-colors ${
              isAdding || !debouncedQuery.trim()
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-positive text-white hover:opacity-90"
            }`}
          >
            {isAdding ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Lägger till...
              </div>
            ) : (
              "Lägg till"
            )}
          </button>
        </div>
        
        {addError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-negative">{addError}</p>
          </div>
        )}
        
        <p className="mt-3 text-xs text-gray-500">
          Automatisk backfill av historisk data sker efter tillägg. Max 5 tillägg per minut.
        </p>
      </div>

      {/* Asset Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
          </div>
        ) : assets.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-500">
            <p className="text-lg mb-2">Inga tillgångar i portföljen</p>
            <p className="text-sm">Lägg till ett bolag ovanför för att börja</p>
          </div>
        ) : (
          assets.map((asset) => (
            <PortfolioCard key={asset.id} asset={asset} />
          ))
        )}
      </div>
    </div>
  );
}
