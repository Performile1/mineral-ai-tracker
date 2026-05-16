"use client";

import { useState, useEffect } from "react";

interface InsiderInvestment {
  id: string;
  manufacturing_company: string;
  manufacturing_ticker: string;
  manufacturing_sector: string;
  invested_asset: string;
  invested_ticker: string;
  investment_type: "stock" | "fund" | "etf";
  investment_amount: number;
  investment_date: string;
  percentage_owned: number;
}

export default function ManufacturingInsider() {
  const [investments, setInvestments] = useState<InsiderInvestment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInsiderInvestments();
  }, []);

  const fetchInsiderInvestments = async () => {
    try {
      setLoading(true);
      // Placeholder data for now
      setInvestments([
        {
          id: "1",
          manufacturing_company: "Volvo AB",
          manufacturing_ticker: "VOLV B",
          manufacturing_sector: "Automotive",
          invested_asset: "Battery Materials ETF",
          invested_ticker: "BATTERY",
          investment_type: "etf",
          investment_amount: 50000000,
          investment_date: "2025-04-15",
          percentage_owned: 2.5,
        },
        {
          id: "2",
          manufacturing_company: "Scania AB",
          manufacturing_ticker: "SCV B",
          manufacturing_sector: "Automotive",
          invested_asset: "Boliden AB",
          invested_ticker: "BOLID",
          investment_type: "stock",
          investment_amount: 15000000,
          investment_date: "2025-03-20",
          percentage_owned: 0.8,
        },
        {
          id: "3",
          manufacturing_company: "ABB Ltd",
          manufacturing_ticker: "ABB",
          manufacturing_sector: "Industrial Automation",
          invested_asset: "Rare Earth Fund",
          invested_ticker: "RARE",
          investment_type: "fund",
          investment_amount: 30000000,
          investment_date: "2025-02-10",
          percentage_owned: 1.2,
        },
        {
          id: "4",
          manufacturing_company: "Sandvik AB",
          manufacturing_ticker: "SAND",
          manufacturing_sector: "Mining Equipment",
          invested_asset: "Nordic Gold",
          invested_ticker: "NKG",
          investment_type: "stock",
          investment_amount: 8000000,
          investment_date: "2025-01-25",
          percentage_owned: 0.5,
        },
        {
          id: "5",
          manufacturing_company: "Electrolux AB",
          manufacturing_ticker: "ELUX B",
          manufacturing_sector: "Home Appliances",
          invested_asset: "Battery Materials ETF",
          invested_ticker: "BATTERY",
          investment_type: "etf",
          investment_amount: 25000000,
          investment_date: "2024-12-30",
          percentage_owned: 1.1,
        },
        {
          id: "6",
          manufacturing_company: "Atlas Copco AB",
          manufacturing_ticker: "ATCO A",
          manufacturing_sector: "Industrial Equipment",
          invested_asset: "Copper Fund",
          invested_ticker: "COPPER",
          investment_type: "fund",
          investment_amount: 40000000,
          investment_date: "2025-05-01",
          percentage_owned: 1.8,
        },
      ]);
    } catch (err) {
      console.error("Failed to load insider investments:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatAmount = (amount: number) => {
    if (amount >= 1000000) {
      return `${(amount / 1000000).toFixed(1)}M SEK`;
    }
    return `${(amount / 1000).toFixed(0)}K SEK`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Manufacturing Insider Investments</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-primary">Manufacturing Insider Investments</h2>
        <button
          onClick={fetchInsiderInvestments}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Uppdatera
        </button>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        Manufacturing companies investing in mineral assets (stocks, funds, ETFs)
      </p>

      <div className="space-y-4">
        {investments.map((investment) => (
          <div
            key={investment.id}
            className="border border-gray-200 rounded-lg p-4 hover:border-positive transition-colors"
          >
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-semibold text-primary">{investment.manufacturing_company}</h3>
                  <span className="text-sm text-gray-500">({investment.manufacturing_ticker})</span>
                </div>
                <p className="text-sm text-gray-600">{investment.manufacturing_sector}</p>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold text-primary">{formatAmount(investment.investment_amount)}</p>
                <p className="text-sm text-gray-500">{investment.investment_date}</p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
              <span className="font-semibold">Invested in:</span>
              <span className="text-primary font-semibold">{investment.invested_asset}</span>
              <span className="text-gray-400">({investment.invested_ticker})</span>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded">
                {investment.investment_type.toUpperCase()}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Ownership:</span>
              <span className="text-sm font-semibold text-primary">{investment.percentage_owned}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-gray-500">Total Investments</p>
            <p className="text-2xl font-bold text-primary">
              {investments.length}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Total Value</p>
            <p className="text-2xl font-bold text-primary">
              {formatAmount(investments.reduce((sum, inv) => sum + inv.investment_amount, 0))}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Top Sector</p>
            <p className="text-2xl font-bold text-primary">Automotive</p>
          </div>
        </div>
      </div>
    </div>
  );
}
