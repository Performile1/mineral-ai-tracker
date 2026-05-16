"use client";

import { useState, useEffect } from "react";

interface Contact {
  id: string;
  manufacturing_company: string;
  manufacturing_ticker: string;
  manufacturing_sector: string;
  target_company: string;
  target_ticker: string;
  target_type: "stock" | "fund" | "etf";
  contact_type: "partnership" | "supply_agreement" | "joint_venture" | "investment" | "licensing";
  relationship_strength: "high" | "medium" | "low";
  last_contact_date: string;
  notes: string;
}

export default function ManufacturingContacts() {
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchContacts();
  }, []);

  const fetchContacts = async () => {
    try {
      setLoading(true);
      // Placeholder data for now
      setContacts([
        {
          id: "1",
          manufacturing_company: "Volvo AB",
          manufacturing_ticker: "VOLV B",
          manufacturing_sector: "Automotive",
          target_company: "Boliden AB",
          target_ticker: "BOLID",
          target_type: "stock",
          contact_type: "supply_agreement",
          relationship_strength: "high",
          last_contact_date: "2025-05-08",
          notes: "Long-term copper supply agreement for EV production",
        },
        {
          id: "2",
          manufacturing_company: "Scania AB",
          manufacturing_ticker: "SCV B",
          manufacturing_sector: "Automotive",
          target_company: "Nordic Gold",
          target_ticker: "NKG",
          target_type: "stock",
          contact_type: "partnership",
          relationship_strength: "medium",
          last_contact_date: "2025-04-20",
          notes: "Exploring gold sourcing for premium vehicle components",
        },
        {
          id: "3",
          manufacturing_company: "ABB Ltd",
          manufacturing_ticker: "ABB",
          manufacturing_sector: "Industrial Automation",
          target_company: "Rare Earth Fund",
          target_ticker: "RARE",
          target_type: "fund",
          contact_type: "investment",
          relationship_strength: "high",
          last_contact_date: "2025-05-10",
          notes: "Strategic investment in rare earth supply chain",
        },
        {
          id: "4",
          manufacturing_company: "Sandvik AB",
          manufacturing_ticker: "SAND",
          manufacturing_sector: "Mining Equipment",
          target_company: "Battery Materials ETF",
          target_ticker: "BATTERY",
          target_type: "etf",
          contact_type: "joint_venture",
          relationship_strength: "high",
          last_contact_date: "2025-03-15",
          notes: "Joint R&D initiative for battery technology",
        },
        {
          id: "5",
          manufacturing_company: "Electrolux AB",
          manufacturing_ticker: "ELUX B",
          manufacturing_sector: "Home Appliances",
          target_company: "Battery Materials ETF",
          target_ticker: "BATTERY",
          target_type: "etf",
          contact_type: "supply_agreement",
          relationship_strength: "medium",
          last_contact_date: "2025-02-28",
          notes: "Battery sourcing for appliance energy efficiency",
        },
        {
          id: "6",
          manufacturing_company: "Atlas Copco AB",
          manufacturing_ticker: "ATCO A",
          manufacturing_sector: "Industrial Equipment",
          target_company: "Copper Fund",
          target_ticker: "COPPER",
          target_type: "fund",
          contact_type: "licensing",
          relationship_strength: "low",
          last_contact_date: "2025-01-10",
          notes: "Technology licensing discussions",
        },
      ]);
    } catch (err) {
      console.error("Failed to load contacts:", err);
    } finally {
      setLoading(false);
    }
  };

  const getContactTypeColor = (type: string) => {
    const colors = {
      partnership: "bg-blue-100 text-blue-800",
      supply_agreement: "bg-green-100 text-green-800",
      joint_venture: "bg-purple-100 text-purple-800",
      investment: "bg-orange-100 text-orange-800",
      licensing: "bg-gray-100 text-gray-800",
    };
    return colors[type as keyof typeof colors] || "bg-gray-100 text-gray-800";
  };

  const getStrengthColor = (strength: string) => {
    const colors = {
      high: "text-positive",
      medium: "text-[#4F8A8B]",
      low: "text-gray-500",
    };
    return colors[strength as keyof typeof colors] || "text-gray-500";
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-primary mb-4">Manufacturing Contact Network</h2>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-positive"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-primary">Manufacturing Contact Network</h2>
        <button
          onClick={fetchContacts}
          className="px-4 py-2 bg-primary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          Uppdatera
        </button>
      </div>

      <p className="text-sm text-gray-600 mb-4">
        Manufacturing companies with contacts to mineral asset companies
      </p>

      <div className="space-y-4">
        {contacts.map((contact) => (
          <div
            key={contact.id}
            className="border border-gray-200 rounded-lg p-4 hover:border-positive transition-colors"
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <div>
                    <h3 className="font-semibold text-primary">{contact.manufacturing_company}</h3>
                    <p className="text-sm text-gray-500">{contact.manufacturing_ticker} • {contact.manufacturing_sector}</p>
                  </div>
                  <div className="text-2xl text-gray-300">→</div>
                  <div>
                    <h3 className="font-semibold text-primary">{contact.target_company}</h3>
                    <p className="text-sm text-gray-500">{contact.target_ticker} • {contact.target_type.toUpperCase()}</p>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">{contact.last_contact_date}</p>
                <span className={`text-sm font-semibold ${getStrengthColor(contact.relationship_strength)}`}>
                  {contact.relationship_strength.charAt(0).toUpperCase() + contact.relationship_strength.slice(1)} Strength
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 mb-3">
              <span className={`px-2 py-1 text-xs font-semibold rounded ${getContactTypeColor(contact.contact_type)}`}>
                {contact.contact_type.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>

            <p className="text-sm text-gray-600 italic">{contact.notes}</p>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-sm text-gray-500">Total Contacts</p>
            <p className="text-2xl font-bold text-primary">{contacts.length}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">High Strength</p>
            <p className="text-2xl font-bold text-positive">
              {contacts.filter((c) => c.relationship_strength === "high").length}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Most Active Sector</p>
            <p className="text-2xl font-bold text-primary">Automotive</p>
          </div>
        </div>
      </div>
    </div>
  );
}
