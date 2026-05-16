"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/apiClient";

interface AlertConfig {
  id: string;
  user_id: string;
  confidence_threshold: number;
  price_drift_threshold: number;
  alert_on_buy: boolean;
  alert_on_sell: boolean;
  alert_on_pass: boolean;
  telegram_enabled: boolean;
  telegram_chat_id: string | null;
  discord_enabled: boolean;
  discord_webhook_url: string | null;
  email_enabled: boolean;
  email_address: string | null;
  created_at: string;
  updated_at: string;
}

export default function AlertsSettingsPage() {
  const router = useRouter();
  const [config, setConfig] = useState<AlertConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`/api/alerts/config`);
      if (!response.ok) {
        throw new Error("Failed to load alert configuration");
      }
      const configs = await response.json();
      if (configs.length > 0) {
        setConfig(configs[0]);
      } else {
        // Create default config
        createDefaultConfig();
      }
    } catch (err) {
      console.error("Error loading config:", err);
    } finally {
      setLoading(false);
    }
  };

  const createDefaultConfig = async () => {
    try {
      const response = await apiFetch(`/api/alerts/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confidence_threshold: 90,
          price_drift_threshold: 8.0,
          alert_on_buy: true,
          alert_on_sell: true,
          alert_on_pass: false,
          telegram_enabled: false,
          discord_enabled: false,
          email_enabled: false,
        }),
      });
      if (!response.ok) {
        throw new Error("Failed to create default config");
      }
      const newConfig = await response.json();
      setConfig(newConfig);
    } catch (err) {
      console.error("Error creating default config:", err);
    }
  };

  const handleSave = async () => {
    if (!config) return;

    try {
      setSaving(true);
      const response = await apiFetch(`/api/alerts/config/${config.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        throw new Error("Failed to save alert configuration");
      }
      const updatedConfig = await response.json();
      setConfig(updatedConfig);
      setTestMessage("Configuration saved successfully!");
      setTimeout(() => setTestMessage(null), 3000);
    } catch (err) {
      console.error("Error saving config:", err);
      setTestMessage("Failed to save configuration");
      setTimeout(() => setTestMessage(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleTestAlert = async (channel: "telegram" | "discord") => {
    if (!config) return;

    try {
      setTestLoading(true);
      setTestMessage(null);
      const response = await apiFetch(`/api/alerts/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ channel }),
      });
      if (!response.ok) {
        throw new Error("Failed to send test alert");
      }
      const result = await response.json();
      setTestMessage(result.message);
      setTimeout(() => setTestMessage(null), 5000);
    } catch (err) {
      console.error("Error sending test alert:", err);
      setTestMessage("Failed to send test alert");
      setTimeout(() => setTestMessage(null), 5000);
    } finally {
      setTestLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#F4F1EE] flex items-center justify-center">
        <div className="text-gray-600">Loading alert configuration...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="min-h-screen bg-[#F4F1EE] flex items-center justify-center">
        <div className="text-red-600">Failed to load alert configuration</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#F4F1EE] text-[#2F2F2F]">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold">Alert Configuration</h1>
          <p className="text-gray-600 text-sm">Configure notification settings for The Sentinel</p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-6">
        {testMessage && (
          <div className={`mb-4 p-4 rounded-lg ${testMessage.includes("success") ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
            {testMessage}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md p-6">
          {/* Signal Thresholds */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-4">Signal Thresholds</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Confidence Threshold: {config.confidence_threshold}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={config.confidence_threshold}
                onChange={(e) =>
                  setConfig({ ...config, confidence_threshold: parseInt(e.target.value) })
                }
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Only send alerts when AI confidence is above this threshold
              </p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Price Drift Threshold: {config.price_drift_threshold}%
              </label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={config.price_drift_threshold}
                onChange={(e) =>
                  setConfig({ ...config, price_drift_threshold: parseFloat(e.target.value) })
                }
                className="w-full p-2 border border-gray-300 rounded-lg"
              />
              <p className="text-xs text-gray-500 mt-1">
                Alert when price drifts by this percentage from entry
              </p>
            </div>
          </div>

          {/* Signal Types */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-4">Signal Types</h2>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.alert_on_buy}
                  onChange={(e) => setConfig({ ...config, alert_on_buy: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm">Alert on BUY signals</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.alert_on_sell}
                  onChange={(e) => setConfig({ ...config, alert_on_sell: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm">Alert on SELL signals</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.alert_on_pass}
                  onChange={(e) => setConfig({ ...config, alert_on_pass: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm">Alert on PASS signals</span>
              </label>
            </div>
          </div>

          {/* Notification Channels */}
          <div className="mb-6">
            <h2 className="text-lg font-semibold mb-4">Notification Channels</h2>
            
            {/* Telegram */}
            <div className="mb-4 p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.telegram_enabled}
                    onChange={(e) => setConfig({ ...config, telegram_enabled: e.target.checked })}
                    className="mr-2"
                  />
                  <span className="font-medium">Telegram</span>
                </label>
                {config.telegram_enabled && (
                  <button
                    onClick={() => handleTestAlert("telegram")}
                    disabled={testLoading}
                    className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs disabled:opacity-50"
                  >
                    {testLoading ? "Sending..." : "Test"}
                  </button>
                )}
              </div>
              {config.telegram_enabled && (
                <input
                  type="text"
                  placeholder="Telegram Chat ID"
                  value={config.telegram_chat_id || ""}
                  onChange={(e) => setConfig({ ...config, telegram_chat_id: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                />
              )}
            </div>

            {/* Discord */}
            <div className="mb-4 p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.discord_enabled}
                    onChange={(e) => setConfig({ ...config, discord_enabled: e.target.checked })}
                    className="mr-2"
                  />
                  <span className="font-medium">Discord</span>
                </label>
                {config.discord_enabled && (
                  <button
                    onClick={() => handleTestAlert("discord")}
                    disabled={testLoading}
                    className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs disabled:opacity-50"
                  >
                    {testLoading ? "Sending..." : "Test"}
                  </button>
                )}
              </div>
              {config.discord_enabled && (
                <input
                  type="text"
                  placeholder="Discord Webhook URL"
                  value={config.discord_webhook_url || ""}
                  onChange={(e) => setConfig({ ...config, discord_webhook_url: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                />
              )}
            </div>

            {/* Email */}
            <div className="mb-4 p-4 border border-gray-200 rounded-lg">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.email_enabled}
                  onChange={(e) => setConfig({ ...config, email_enabled: e.target.checked })}
                  className="mr-2"
                />
                <span className="font-medium">Email</span>
              </label>
              {config.email_enabled && (
                <input
                  type="email"
                  placeholder="Email Address"
                  value={config.email_address || ""}
                  onChange={(e) => setConfig({ ...config, email_address: e.target.value })}
                  className="w-full p-2 border border-gray-300 rounded-lg text-sm mt-2"
                />
              )}
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 bg-[#2F2F2F] text-white rounded-lg hover:opacity-90 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Configuration"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
