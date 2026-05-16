"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useDisclaimerStore } from "@/lib/store/disclaimer";

export default function OnboardingPage() {
  const router = useRouter();
  const { setAccepted, setTimestamp } = useDisclaimerStore();
  const [accepted, setAcceptedState] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleAccept = async () => {
    if (!accepted) return;

    setLoading(true);
    
    // Store acceptance in Zustand and localStorage
    setAccepted(true);
    setTimestamp(new Date().toISOString());
    localStorage.setItem("disclaimer_accepted", "true");
    localStorage.setItem("disclaimer_timestamp", new Date().toISOString());

    // Set cookie for middleware to check (expires in 1 year)
    document.cookie = "disclaimer_accepted=true; path=/; max-age=31536000; SameSite=Lax";

    // Use window.location for hard redirect to avoid Next.js routing issues
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen bg-background text-primary flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <h1 className="text-3xl font-bold mb-6 text-center">
            Welcome to Mineral AI Tracker
          </h1>
          
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4 text-negative">
              ⚠️ IMPORTANT FINANCIAL DISCLAIMER
            </h2>
            
            <div className="bg-red-50 border-l-4 border-negative p-4 mb-4">
              <p className="text-sm text-primary mb-4">
                <strong>PLEASE READ CAREFULLY BEFORE PROCEEDING</strong>
              </p>
              
              <div className="space-y-3 text-sm text-primary">
                <p>
                  <strong>Classification:</strong> This application is strictly classified as a 
                  <em> "data analysis and visualization tool"</em>. It is NOT a financial advisory service.
                </p>
                
                <p>
                  <strong>No Investment Advice:</strong> The Buffett Score, Kelly Criterion, 
                  and all other calculations provided by this system are for informational purposes only. 
                  They do not constitute personalized investment advice, recommendations, or solicitations.
                </p>
                
                <p>
                  <strong>Risk Acknowledgment:</strong> Investing in mineral assets, commodities, 
                  and related securities involves significant risk, including the potential loss of 
                  your entire investment. Past performance does not guarantee future results.
                </p>
                
                <p>
                  <strong>Data Limitations:</strong> While we strive for accuracy, data from external 
                  sources (SGU, NGU, GTK, EGDI, BRGM, IEA, Eurostat, LME, Benchmark, Avanza, Nordnet, etc.) 
                  may be delayed, incomplete, or contain errors. We are not responsible for any decisions 
                  made based on this data.
                </p>
                
                <p>
                  <strong>Your Responsibility:</strong> You acknowledge that you are solely responsible 
                  for your investment decisions. You should conduct your own research, consult with 
                  qualified financial advisors, and carefully consider your financial situation, risk 
                  tolerance, and investment objectives before making any investment decisions.
                </p>
                
                <p>
                  <strong>No Warranty:</strong> This software is provided "as is" without any warranty, 
                  express or implied, including but not limited to warranties of merchantability, 
                  fitness for a particular purpose, or non-infringement.
                </p>
                
                <p>
                  <strong>Limitation of Liability:</strong> In no event shall the developers, 
                  contributors, or any affiliated parties be liable for any direct, indirect, 
                  incidental, special, or consequential damages arising from the use of this software.
                </p>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3">
              By proceeding, you acknowledge and agree that:
            </h3>
            
            <ul className="list-disc list-inside space-y-2 text-sm text-primary">
              <li>You understand this is a data visualization tool, not financial advice</li>
              <li>You have read and understand the risks involved in mineral asset investing</li>
              <li>You will make your own independent investment decisions</li>
              <li>You will not hold the developers liable for any investment losses</li>
              <li>You are using this tool at your own risk</li>
            </ul>
          </div>

          <div className="flex items-start mb-6">
            <input
              type="checkbox"
              id="accept-disclaimer"
              checked={accepted}
              onChange={(e) => setAcceptedState(e.target.checked)}
              className="mt-1 mr-3 w-5 h-5 cursor-pointer"
            />
            <label 
              htmlFor="accept-disclaimer" 
              className="text-sm text-primary cursor-pointer"
            >
              I have read, understood, and agree to the terms above. I accept full responsibility 
              for my investment decisions.
            </label>
          </div>

          <button
            onClick={handleAccept}
            disabled={!accepted || loading}
            className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
              accepted && !loading
                ? "bg-positive text-white hover:opacity-90"
                : "bg-gray-300 text-gray-500 cursor-not-allowed"
            }`}
          >
            {loading ? "Processing..." : "I Agree & Continue"}
          </button>

          <p className="text-center text-xs text-primary mt-4">
            Your acceptance will be stored locally for future sessions.
          </p>
        </div>
      </div>
    </div>
  );
}
