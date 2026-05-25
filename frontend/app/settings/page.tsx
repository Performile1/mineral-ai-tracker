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

interface ChannelPrefs {
  email: boolean;
  in_app: boolean;
  webhook: boolean;
}

interface NotificationPreferences {
  dilution_risk: ChannelPrefs;
  black_swan: ChannelPrefs;
  take_or_pay_new: ChannelPrefs;
  ma_radar: ChannelPrefs;
  chokepoint: ChannelPrefs;
  early_sentiment: ChannelPrefs;
}

interface AlertSubscription {
  id: string;
  ticker: string;
  risk_threshold: number;
  created_at: string;
}

const DEFAULT_NOTIF_PREFS: NotificationPreferences = {
  dilution_risk:   { email: true,  in_app: true,  webhook: false },
  black_swan:      { email: false, in_app: true,  webhook: false },
  take_or_pay_new: { email: false, in_app: true,  webhook: false },
  ma_radar:        { email: false, in_app: true,  webhook: false },
  chokepoint:      { email: true,  in_app: true,  webhook: false },
  early_sentiment: { email: false, in_app: true,  webhook: false },
};

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
  
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences>(DEFAULT_NOTIF_PREFS);
  const [notifSaving, setNotifSaving] = useState(false);
  const [notifError, setNotifError] = useState<string | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [subscriptions, setSubscriptions] = useState<AlertSubscription[]>([]);
  const [subsLoading, setSubsLoading] = useState(false);

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
    loadNotifPrefs();
    loadSubscriptions();
    // Load local settings from localStorage
    const saved = localStorage.getItem("localSettings");
    if (saved) {
      setLocalSettings(JSON.parse(saved));
    }
  }, []);

  const loadNotifPrefs = async () => {
    try {
      const res = await apiFetch("/api/settings/notifications");
      if (!res.ok) return;
      const data = await res.json();
      setNotifPrefs({ ...DEFAULT_NOTIF_PREFS, ...data });
      if (data.webhook_url) setWebhookUrl(data.webhook_url);
    } catch (err) {
      console.error("Failed to load notification preferences:", err);
    }
  };

  const loadSubscriptions = async () => {
    try {
      setSubsLoading(true);
      const res = await apiFetch("/api/settings/alerts/subscriptions");
      if (!res.ok) return;
      setSubscriptions(await res.json());
    } catch (err) {
      console.error("Failed to load subscriptions:", err);
    } finally {
      setSubsLoading(false);
    }
  };

  const handleDeleteSubscription = async (ticker: string) => {
    try {
      const res = await apiFetch(`/api/settings/alerts/subscriptions/${ticker}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed");
      setSubscriptions((prev) => prev.filter((s) => s.ticker !== ticker));
    } catch (err) {
      console.error("Failed to delete subscription:", err);
    }
  };

  const handleSaveNotifPrefs = async () => {
    try {
      setNotifSaving(true);
      setNotifError(null);
      const payload = { ...notifPrefs, webhook_url: webhookUrl || undefined };
      const res = await apiFetch("/api/settings/notifications", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.status === 401 || res.status === 403) {
        setNotifError(
          "Nekad åtkomst: Du saknar behörighet att uppdatera notifikationsinställningar (" +
            res.status +
            ")"
        );
        return;
      }
      if (!res.ok) throw new Error("Failed to save");
      const data = await res.json();
      setNotifPrefs({ ...DEFAULT_NOTIF_PREFS, ...data });
      if (data.webhook_url !== undefined) setWebhookUrl(data.webhook_url ?? "");
    } catch (err) {
      console.error("Error saving notification preferences:", err);
      setNotifError("Misslyckades med att spara notifikationsinställningar.");
    } finally {
      setNotifSaving(false);
    }
  };

  const toggleNotif = (
    category: keyof NotificationPreferences,
    channel: keyof ChannelPrefs,
  ) => {
    setNotifPrefs((prev) => ({
      ...prev,
      [category]: { ...prev[category], [channel]: !prev[category][channel] },
    }));
  };

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

        {/* Notification Routing — Sprint 10.10 + Sprint 15 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-semibold text-primary">Notifikationsinställningar</h2>
              <p className="text-xs text-gray-500 mt-0.5">Styr per kategori vilka kanaler som används</p>
            </div>
            <button
              onClick={handleSaveNotifPrefs}
              disabled={notifSaving}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
            >
              {notifSaving ? "Sparar..." : "Spara"}
            </button>
          </div>

          {/* Skuld J — inline error banner for 401/403 */}
          {notifError && (
            <div className="mb-4 flex items-start gap-2 p-3 bg-red-50 border border-red-300 text-red-700 rounded-lg text-sm">
              <span className="mt-0.5">🚫</span>
              <span>{notifError}</span>
              <button
                onClick={() => setNotifError(null)}
                className="ml-auto text-red-400 hover:text-red-600 font-bold leading-none"
              >
                ×
              </button>
            </div>
          )}

          {/* Column headers */}
          <div className="grid grid-cols-4 gap-2 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">
            <div>Kategori</div>
            <div className="text-center">E-post</div>
            <div className="text-center">In-app</div>
            <div className="text-center">Webhook</div>
          </div>

          {([
            { key: "dilution_risk"   as const, label: "⚠️ Dilution Risk (>75%)",         color: "text-red-600"    },
            { key: "black_swan"      as const, label: "🌊 Black Swan-händelse",           color: "text-purple-600" },
            { key: "take_or_pay_new" as const, label: "🔒 Nytt Take-or-Pay-kontrakt",    color: "text-green-600"  },
            { key: "ma_radar"        as const, label: "💰 M&A Radar (uppköpsrisk)",       color: "text-amber-600"  },
            { key: "chokepoint"      as const, label: "🚢 Logistik / Chokepoint",         color: "text-orange-600" },
            { key: "early_sentiment" as const, label: "📡 Tidig Sentiment-varning",      color: "text-cyan-600"   },
          ]).map(({ key, label, color }) => (
            <div key={key} className="grid grid-cols-4 gap-2 items-center py-2 border-b border-gray-100 last:border-0">
              <span className={`text-sm font-medium ${color}`}>{label}</span>
              {(["email", "in_app", "webhook"] as const).map((ch) => (
                <div key={ch} className="flex justify-center">
                  <button
                    type="button"
                    onClick={() => toggleNotif(key, ch)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                      notifPrefs[key][ch] ? "bg-blue-600" : "bg-gray-300"
                    }`}
                    aria-pressed={notifPrefs[key][ch]}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                        notifPrefs[key][ch] ? "translate-x-6" : "translate-x-1"
                      }`}
                    />
                  </button>
                </div>
              ))}
            </div>
          ))}

          {/* Sprint 15 — Global Webhook URL (Q6) */}
          <div className="mt-5 pt-4 border-t border-gray-100">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Global Webhook URL{" "}
              <span className="text-xs text-gray-400 font-normal">(Discord / Slack / Custom)</span>
            </label>
            <input
              type="url"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="w-full p-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <p className="text-xs text-gray-400 mt-1">
              Sparas i notification_preferences.webhook_url — används av alla kategorier med webhook aktiverat.
            </p>
          </div>
        </div>

        {/* Sprint 15 — Alert Subscriptions CRUD */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-semibold text-primary">Aktiva Ticker-prenumerationer</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Larm du har satt via Nexus-grafen · Klicka på en nod i grafen för att lägga till fler
              </p>
            </div>
            <button
              onClick={loadSubscriptions}
              disabled={subsLoading}
              className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-50 text-sm"
            >
              {subsLoading ? "Laddar..." : "↻ Uppdatera"}
            </button>
          </div>

          {subscriptions.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">
              <div className="text-2xl mb-2">🔕</div>
              Inga aktiva larm — klicka på en nod i Nexus-grafen för att prenumerera.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-100">
                    <th className="text-left pb-2">Ticker</th>
                    <th className="text-center pb-2">Risktrösklar</th>
                    <th className="text-left pb-2">Skapad</th>
                    <th className="text-right pb-2">Ta bort</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((sub) => (
                    <tr key={sub.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                      <td className="py-2.5 font-semibold text-gray-800">{sub.ticker}</td>
                      <td className="py-2.5 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-xs font-bold ${
                            sub.risk_threshold > 75
                              ? "bg-red-100 text-red-700"
                              : sub.risk_threshold > 40
                              ? "bg-amber-100 text-amber-700"
                              : "bg-green-100 text-green-700"
                          }`}
                        >
                          ≥{sub.risk_threshold}%
                        </span>
                      </td>
                      <td className="py-2.5 text-gray-400 text-xs">
                        {new Date(sub.created_at).toLocaleDateString("sv-SE")}
                      </td>
                      <td className="py-2.5 text-right">
                        <button
                          onClick={() => handleDeleteSubscription(sub.ticker)}
                          className="text-gray-400 hover:text-red-500 transition-colors text-base"
                          title={`Ta bort larm för ${sub.ticker}`}
                        >
                          🗑
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
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
