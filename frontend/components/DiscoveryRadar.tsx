"use client";

import { useState, useEffect } from "react";

interface DiscoveredAsset {
  id: string;
  ticker: string | null;
  name: string;
  status: string;
  discovery_source: string;
  created_at: string;
  tags: Array<{
    tag_name: string;
    tag_category: string;
    confidence: number;
  }>;
}

export default function DiscoveryRadar() {
  const [assets, setAssets] = useState<DiscoveredAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDiscoveredAssets();
  }, []);

  const fetchDiscoveredAssets = async () => {
    try {
      setLoading(true);
      // In production, fetch from API
      // const response = await fetch("/api/assets/scouted");
      // const data = await response.json();
      // setAssets(data.assets || []);
      
      // Placeholder data for now
      setAssets([
        {
          id: "1",
          ticker: "NOMI",
          name: "Nordic Mining AB",
          status: "verified",
          discovery_source: "AI Scout - Geology Pattern",
          created_at: "2025-05-10T10:30:00Z",
          tags: [
            { tag_name: "Copper", tag_category: "commodity", confidence: 0.85 },
            { tag_name: "Sweden", tag_category: "region", confidence: 0.92 },
            { tag_name: "Exploration", tag_category: "stage", confidence: 0.78 },
          ],
        },
        {
          id: "2",
          ticker: null,
          name: "Luleå Lithium Project",
          status: "user_added",
          discovery_source: "User Input",
          created_at: "2025-05-08T14:20:00Z",
          tags: [
            { tag_name: "Lithium", tag_category: "commodity", confidence: 0.72 },
            { tag_name: "Sweden", tag_category: "region", confidence: 0.88 },
            { tag_name: "Prospecting", tag_category: "stage", confidence: 0.65 },
          ],
        },
        {
          id: "3",
          ticker: "GOLDX",
          name: "Gold Exploration Nordic",
          status: "scouted",
          discovery_source: "AI Scout - News Analysis",
          created_at: "2025-05-05T09:15:00Z",
          tags: [
            { tag_name: "Gold", tag_category: "commodity", confidence: 0.81 },
            { tag_name: "Finland", tag_category: "region", confidence: 0.75 },
            { tag_name: "Development", tag_category: "stage", confidence: 0.70 },
          ],
        },
      ]);
    } catch (err) {
      setError("Failed to load discovered assets");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("sv-SE", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      commodity: "bg-positive text-white",
      region: "bg-primary text-white",
      stage: "bg-gray-600 text-white",
      technology: "bg-purple-600 text-white",
      other: "bg-gray-500 text-white",
    };
    return colors[category] || colors.other;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Radar / Upptäckter</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Radar / Upptäckter</h2>
        <div className="text-negative text-center py-8">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-primary">Radar / Upptäckter</h2>
        <button
          onClick={fetchDiscoveredAssets}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Uppdatera
        </button>
      </div>

      {assets.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg mb-2">Inga nya upptäckter</p>
          <p className="text-sm">AI Scout hittar automatiskt nya bolag</p>
        </div>
      ) : (
        <div className="space-y-4">
          {assets.map((asset) => (
            <div
              key={asset.id}
              className="border border-gray-200 rounded-lg p-4 hover:border-positive transition-colors"
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="inline-block px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
                      Ny Datapunkt
                    </span>
                    {asset.ticker && (
                      <span className="font-bold text-primary">
                        {asset.ticker}
                      </span>
                    )}
                  </div>
                  <h3 className="font-semibold text-primary">{asset.name}</h3>
                </div>
                <div className="text-right text-sm text-gray-500">
                  {formatDate(asset.created_at)}
                </div>
              </div>

              <div className="mb-3">
                <p className="text-sm text-gray-600">
                  <span className="font-semibold">Källa:</span> {asset.discovery_source}
                </p>
              </div>

              {asset.tags && asset.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {asset.tags.map((tag, index) => (
                    <span
                      key={index}
                      className={`px-2 py-1 text-xs font-medium rounded ${getCategoryColor(tag.tag_category)}`}
                    >
                      {tag.tag_name}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 pt-3 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  Inget Target Price än - inväntar bekräftelse
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
