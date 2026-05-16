"use client";

import { useState, useEffect } from "react";
import { apiFetch } from "@/lib/apiClient";

interface SystemSettings {
  max_pe_ratio: number;
  min_market_cap_m: number;
  min_daily_volume_k: number;
  min_confidence_score: number;
  max_geological_grade_copper: number;
  database_type: string;
  ollama_url: string;
  fmp_api_key_set: boolean;
}

interface VaultStatus {
  fmp_api_key_set: boolean;
  encryption_available: boolean;
  source: "vault" | "env_var" | "none";
}

interface LocalSettings {
  notifications: {
    email: boolean;
    sms: boolean;
    stopLoss: boolean;
    blackSwan: boolean;
    targetHit: boolean;
  };
  display: {
    darkMode: boolean;
    compactView: boolean;
    showConfidence: boolean;
  };
  trading: {
    defaultBroker: string;
    autoRebalance: boolean;
    maxPositionSize: number;
  };
}

export default function SettingsPage() {
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [systemSettings, setSystemSettings] = useState<SystemSettings>({
    max_pe_ratio: 25.0,
    min_market_cap_m: 10.0,
    min_daily_volume_k: 500.0,
    min_confidence_score: 85,
    max_geological_grade_copper: 15.0,
    database_type: "local",
    ollama_url: "http://localhost:11434",
    fmp_api_key_set: false,
  });

  const [vaultStatus, setVaultStatus] = useState<VaultStatus>({
    fmp_api_key_set: false,
    encryption_available: false,
    source: "none",
  });
  const [vaultSaving, setVaultSaving] = useState(false);
  const [fmpApiKeyInput, setFmpApiKeyInput] = useState("");
  
  const [localSettings, setLocalSettings] = useState<LocalSettings>({
    notifications: {
      email: true,
      sms: false,
      stopLoss: true,
      blackSwan: true,
      targetHit: false,
    },
    display: {
      darkMode: false,
      compactView: false,
      showConfidence: true,
    },
    trading: {
      defaultBroker: "avanza",
      autoRebalance: false,
      maxPositionSize: 20,
    },
  });

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    setMounted(true);
    loadSettings();
    loadVaultStatus();
    // Load local settings from localStorage
    const saved = localStorage.getItem("localSettings");
    if (saved) {
      setLocalSettings(JSON.parse(saved));
    }
  }, []);

  const loadVaultStatus = async () => {
    try {
      const response = await apiFetch(`/api/settings/vault`);
      if (!response.ok) return;
      const data = await response.json();
      setVaultStatus(data);
    } catch (err) {
      console.error("Error loading vault status:", err);
    }
  };

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiFetch(`/api/settings`);
      if (!response.ok) {
        throw new Error("Failed to load settings");
      }
      const data = await response.json();
      setSystemSettings(data);
    } catch (err) {
      console.error("Error loading settings:", err);
      setError("Failed to load system settings from backend");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSystemSettings = async () => {
    try {
      setSaving(true);
      setError(null);
      const response = await apiFetch(`/api/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          max_pe_ratio: systemSettings.max_pe_ratio,
          min_market_cap_m: systemSettings.min_market_cap_m,
          min_daily_volume_k: systemSettings.min_daily_volume_k,
          min_confidence_score: systemSettings.min_confidence_score,
          max_geological_grade_copper: systemSettings.max_geological_grade_copper,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to save settings");
      }
      alert("System settings saved successfully!");
    } catch (err) {
      console.error("Error saving settings:", err);
      setError("Failed to save system settings");
    } finally {
      setSaving(false);
    }
  };

  const handleResetSystemSettings = async () => {
    if (!confirm("Reset system settings to default values?")) return;
    
    try {
      setSaving(true);
      setError(null);
      const response = await apiFetch(`/api/settings/reset`, {
        method: "POST",
      });
      if (!response.ok) {
        throw new Error("Failed to reset settings");
      }
      const data = await response.json();
      setSystemSettings(data);
      alert("System settings reset to default!");
    } catch (err) {
      console.error("Error resetting settings:", err);
      setError("Failed to reset system settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveLocalSettings = () => {
    localStorage.setItem("localSettings", JSON.stringify(localSettings));
    alert("Local settings saved!");
  };

  const handleUpdateVault = async () => {
    try {
      setVaultSaving(true);
      setError(null);
      const response = await apiFetch(`/api/settings/vault`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fmp_api_key: fmpApiKeyInput,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to update vault");
      }
      const data = await response.json();
      setVaultStatus(data);
      setFmpApiKeyInput("");
      alert("Vault updated successfully!");
    } catch (err) {
      console.error("Error updating vault:", err);
      setError("Failed to update vault");
    } finally {
      setVaultSaving(false);
    }
  };

  if (!mounted) return null;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Settings</h1>
        <p className="text-gray-600">Configure your preferences and system thresholds</p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* System Settings (PRD v8.0) */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-primary">System Thresholds (PRD v8.0)</h2>
            <button
              onClick={handleResetSystemSettings}
              disabled={saving}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 disabled:opacity-50"
            >
              Reset to Default
            </button>
          </div>
          
          {loading ? (
            <div className="text-center py-4">Loading system settings...</div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-gray-700 mb-2">
                  Max P/E (Forward)
                  <span className="text-sm text-gray-500 ml-2">
                    - Filters extremely overvalued companies
                  </span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="5"
                  max="200"
                  value={systemSettings.max_pe_ratio}
                  onChange={(e) =>
                    setSystemSettings({
                      ...systemSettings,
                      max_pe_ratio: parseFloat(e.target.value),
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-gray-700 mb-2">
                  Min Market Cap (M USD)
                  <span className="text-sm text-gray-500 ml-2">
                    - Barrier against penny stocks
                  </span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="1"
                  max="10000"
                  value={systemSettings.min_market_cap_m}
                  onChange={(e) =>
                    setSystemSettings({
                      ...systemSettings,
                      min_market_cap_m: parseFloat(e.target.value),
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-gray-700 mb-2">
                  Min Daily Volume (K USD)
                  <span className="text-sm text-gray-500 ml-2">
                    - Minimum liquidity threshold
                  </span>
                </label>
                <input
                  type="number"
                  step="1"
                  min="10"
                  max="100000"
                  value={systemSettings.min_daily_volume_k}
                  onChange={(e) =>
                    setSystemSettings({
                      ...systemSettings,
                      min_daily_volume_k: parseFloat(e.target.value),
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-gray-700 mb-2">
                  Max Geological Grade (Copper %)
                  <span className="text-sm text-gray-500 ml-2">
                    - Physical barrier against AI hallucinations
                  </span>
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={systemSettings.max_geological_grade_copper}
                  onChange={(e) =>
                    setSystemSettings({
                      ...systemSettings,
                      max_geological_grade_copper: parseFloat(e.target.value),
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div>
                <label className="block text-gray-700 mb-2">
                  AI Confidence Threshold (0-100)
                  <span className="text-sm text-gray-500 ml-2">
                    - Minimum confidence for AI alerts
                  </span>
                </label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  max="100"
                  value={systemSettings.min_confidence_score}
                  onChange={(e) =>
                    setSystemSettings({
                      ...systemSettings,
                      min_confidence_score: parseInt(e.target.value),
                    })
                  }
                  className="w-full p-2 border border-gray-300 rounded-lg"
                />
              </div>

              <div className="pt-4 border-t">
                <div className="text-sm text-gray-600 mb-2">
                  <strong>Database:</strong> {systemSettings.database_type} | 
                  <strong> Ollama:</strong> {systemSettings.ollama_url}
                </div>
                <button
                  onClick={handleSaveSystemSettings}
                  disabled={saving}
                  className="w-full py-3 px-6 bg-positive text-white rounded-lg font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save System Settings"}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* API Credential Vault (PRD v8.7 Phase 9) */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">
            API Credential Vault (PRD v8.7 Phase 9)
          </h2>
          <div className="space-y-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-700">Vault Status</span>
                <span className={`px-2 py-1 rounded text-xs ${
                  vaultStatus.encryption_available
                    ? "bg-green-100 text-green-700"
                    : "bg-yellow-100 text-yellow-700"
                }`}>
                  {vaultStatus.encryption_available ? "AES-256-GCM" : "Base64 (insecure)"}
                </span>
              </div>
              <div className="text-sm text-gray-600">
                <strong>FMP API Key:</strong>{" "}
                {vaultStatus.fmp_api_key_set ? (
                  <span className="text-green-600">Configured ({vaultStatus.source})</span>
                ) : (
                  <span className="text-gray-500">Not set</span>
                )}
              </div>
              {vaultStatus.source === "env_var" && (
                <div className="text-xs text-gray-500 mt-1">
                  Key loaded from FMP_API_KEY environment variable. Vault can override it.
                </div>
              )}
            </div>

            <div>
              <label className="block text-gray-700 mb-2">
                FMP API Key
                <span className="text-sm text-gray-500 ml-2">
                  - Financial Modeling Prep for Llama-3 Data Sovereignty
                </span>
              </label>
              <input
                type="password"
                placeholder="Enter new key to store in vault, or leave empty to remove"
                value={fmpApiKeyInput}
                onChange={(e) => setFmpApiKeyInput(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-lg"
              />
            </div>

            <button
              onClick={handleUpdateVault}
              disabled={vaultSaving}
              className="w-full py-2 px-4 bg-primary text-white rounded-lg font-semibold hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {vaultSaving ? "Updating Vault..." : "Update Vault"}
            </button>
          </div>
        </div>

        {/* Notifications */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">Notifications</h2>
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Email Alerts</span>
              <input
                type="checkbox"
                checked={localSettings.notifications.email}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    notifications: { ...localSettings.notifications, email: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">SMS Alerts (Twilio)</span>
              <input
                type="checkbox"
                checked={localSettings.notifications.sms}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    notifications: { ...localSettings.notifications, sms: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Stop-Loss Triggers</span>
              <input
                type="checkbox"
                checked={localSettings.notifications.stopLoss}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    notifications: { ...localSettings.notifications, stopLoss: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Black Swan Events</span>
              <input
                type="checkbox"
                checked={localSettings.notifications.blackSwan}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    notifications: { ...localSettings.notifications, blackSwan: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Target Price Hits</span>
              <input
                type="checkbox"
                checked={localSettings.notifications.targetHit}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    notifications: { ...localSettings.notifications, targetHit: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
          </div>
        </div>

        {/* Display */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">Display</h2>
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Dark Mode</span>
              <input
                type="checkbox"
                checked={localSettings.display.darkMode}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    display: { ...localSettings.display, darkMode: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Compact View</span>
              <input
                type="checkbox"
                checked={localSettings.display.compactView}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    display: { ...localSettings.display, compactView: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Show Confidence Scores</span>
              <input
                type="checkbox"
                checked={localSettings.display.showConfidence}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    display: { ...localSettings.display, showConfidence: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
          </div>
        </div>

        {/* Trading */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-primary mb-4">Trading</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-gray-700 mb-2">Default Broker</label>
              <select
                value={localSettings.trading.defaultBroker}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    trading: { ...localSettings.trading, defaultBroker: e.target.value },
                  })
                }
                className="w-full p-2 border border-gray-300 rounded-lg"
              >
                <option value="avanza">Avanza</option>
                <option value="nordnet">Nordnet</option>
                <option value="degiro">DEGIRO</option>
                <option value="interactive">Interactive Brokers</option>
              </select>
            </div>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-gray-700">Auto Rebalance</span>
              <input
                type="checkbox"
                checked={localSettings.trading.autoRebalance}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    trading: { ...localSettings.trading, autoRebalance: e.target.checked },
                  })
                }
                className="w-5 h-5 text-primary rounded"
              />
            </label>
            <div>
              <label className="block text-gray-700 mb-2">
                Max Position Size (%)
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={localSettings.trading.maxPositionSize}
                onChange={(e) =>
                  setLocalSettings({
                    ...localSettings,
                    trading: { ...localSettings.trading, maxPositionSize: parseInt(e.target.value) },
                  })
                }
                className="w-full p-2 border border-gray-300 rounded-lg"
              />
            </div>
          </div>
        </div>

        {/* Save Local Settings Button */}
        <button
          onClick={handleSaveLocalSettings}
          className="w-full py-3 px-6 bg-positive text-white rounded-lg font-semibold hover:opacity-90 transition-opacity"
        >
          Save Local Settings
        </button>
      </div>
    </div>
  );
}
