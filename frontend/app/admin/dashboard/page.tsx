"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/apiClient";

interface DashboardData {
  analysis_stats: {
    total_today: number;
    total_week: number;
    total_month: number;
    success_rate_today: number;
    success_rate_week: number;
    success_rate_month: number;
  };
  system_health: {
    status: string;
    database: string;
    ollama: string;
    celery: string;
    redis: string;
  };
  recent_activity: Array<{
    ticker: string;
    signal_type: string;
    confidence_score: number;
    created_at: string;
    is_public: boolean;
  }>;
}

interface CeleryStatus {
  status: string;
  active_tasks: number;
  scheduled_tasks: number;
  reserved_tasks: number;
  workers: number;
  error?: string;
}

interface PrometheusMetrics {
  status: string;
  key_metrics: {
    http_requests_total: number;
    http_request_duration_seconds: number;
    celery_tasks_total: number;
    celery_worker_tasks: number;
    db_connections_active: number;
  };
  error?: string;
}

export default function AdminDashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [celeryStatus, setCeleryStatus] = useState<CeleryStatus | null>(null);
  const [prometheusMetrics, setPrometheusMetrics] = useState<PrometheusMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    fetchCeleryStatus();
    fetchPrometheusMetrics();
    const interval = setInterval(() => {
      fetchDashboardData();
      fetchCeleryStatus();
      fetchPrometheusMetrics();
    }, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await apiFetch("/api/admin/dashboard");
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCeleryStatus = async () => {
    try {
      const response = await apiFetch("/api/admin/celery-status");
      if (response.ok) {
        const data = await response.json();
        setCeleryStatus(data);
      }
    } catch (error) {
      console.error("Failed to fetch Celery status:", error);
    }
  };

  const fetchPrometheusMetrics = async () => {
    try {
      const response = await apiFetch("/api/admin/prometheus-metrics");
      if (response.ok) {
        const data = await response.json();
        setPrometheusMetrics(data);
      }
    } catch (error) {
      console.error("Failed to fetch Prometheus metrics:", error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>
          <div className="text-gray-400">Loading...</div>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-8">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>
          <div className="text-red-400">Failed to load dashboard data</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Admin Dashboard</h1>
        
        {/* Analysis Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h2 className="text-white text-lg font-semibold mb-2">Today</h2>
            <p className="text-gray-400 text-sm mb-4">Analyses today</p>
            <div className="text-4xl font-bold text-blue-400">{dashboardData.analysis_stats.total_today}</div>
            <div className="text-sm text-gray-400 mt-2">
              Success Rate: {dashboardData.analysis_stats.success_rate_today.toFixed(1)}%
            </div>
          </div>
          
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h2 className="text-white text-lg font-semibold mb-2">This Week</h2>
            <p className="text-gray-400 text-sm mb-4">Analyses this week</p>
            <div className="text-4xl font-bold text-green-400">{dashboardData.analysis_stats.total_week}</div>
            <div className="text-sm text-gray-400 mt-2">
              Success Rate: {dashboardData.analysis_stats.success_rate_week.toFixed(1)}%
            </div>
          </div>
          
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h2 className="text-white text-lg font-semibold mb-2">This Month</h2>
            <p className="text-gray-400 text-sm mb-4">Analyses this month</p>
            <div className="text-4xl font-bold text-purple-400">{dashboardData.analysis_stats.total_month}</div>
            <div className="text-sm text-gray-400 mt-2">
              Success Rate: {dashboardData.analysis_stats.success_rate_month.toFixed(1)}%
            </div>
          </div>
        </div>

        {/* System Health */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-8">
          <h2 className="text-white text-lg font-semibold mb-2">System Health</h2>
          <p className="text-gray-400 text-sm mb-4">Real-time system status</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${dashboardData.system_health.database === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-gray-300">Database</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${dashboardData.system_health.ollama === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-gray-300">Ollama</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${dashboardData.system_health.celery === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-gray-300">Celery</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${dashboardData.system_health.redis === 'ok' ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-gray-300">Redis</span>
            </div>
          </div>
          
          {/* Celery Queue Status */}
          {celeryStatus && (
            <div className="border-t border-gray-700 pt-4 mt-4">
              <h3 className="text-white font-semibold mb-3">Celery Queue Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <div className="text-gray-400 text-sm">Active Tasks</div>
                  <div className="text-2xl font-bold text-blue-400">{celeryStatus.active_tasks}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Scheduled Tasks</div>
                  <div className="text-2xl font-bold text-yellow-400">{celeryStatus.scheduled_tasks}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Reserved Tasks</div>
                  <div className="text-2xl font-bold text-purple-400">{celeryStatus.reserved_tasks}</div>
                </div>
                <div>
                  <div className="text-gray-400 text-sm">Workers</div>
                  <div className="text-2xl font-bold text-green-400">{celeryStatus.workers}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 mb-8">
          <h2 className="text-white text-lg font-semibold mb-2">Recent Activity</h2>
          <p className="text-gray-400 text-sm mb-4">Latest analysis signals</p>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-2">Ticker</th>
                  <th className="pb-2">Signal</th>
                  <th className="pb-2">Confidence</th>
                  <th className="pb-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {dashboardData.recent_activity.map((activity, index) => (
                  <tr key={index} className="border-b border-gray-700">
                    <td className="py-2 text-white">{activity.ticker}</td>
                    <td className={`py-2 ${
                      activity.signal_type === 'BUY' || activity.signal_type === 'STRONG_BUY' ? 'text-green-400' :
                      activity.signal_type === 'SELL' || activity.signal_type === 'STRONG_SELL' ? 'text-red-400' :
                      'text-yellow-400'
                    }`}>
                      {activity.signal_type}
                    </td>
                    <td className="py-2 text-gray-300">{activity.confidence_score.toFixed(1)}%</td>
                    <td className="py-2 text-gray-400">
                      {activity.created_at ? new Date(activity.created_at).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Prometheus Metrics */}
        {prometheusMetrics && (
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <h2 className="text-white text-lg font-semibold mb-2">Performance Metrics</h2>
            <p className="text-gray-400 text-sm mb-4">Real-time system metrics from Prometheus</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <div className="text-gray-400 text-sm">HTTP Requests Total</div>
                <div className="text-2xl font-bold text-blue-400">
                  {typeof prometheusMetrics.key_metrics.http_requests_total === 'number' 
                    ? prometheusMetrics.key_metrics.http_requests_total.toLocaleString() 
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Avg Request Duration (s)</div>
                <div className="text-2xl font-bold text-green-400">
                  {typeof prometheusMetrics.key_metrics.http_request_duration_seconds === 'number'
                    ? prometheusMetrics.key_metrics.http_request_duration_seconds.toFixed(3)
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Celery Tasks Total</div>
                <div className="text-2xl font-bold text-purple-400">
                  {typeof prometheusMetrics.key_metrics.celery_tasks_total === 'number'
                    ? prometheusMetrics.key_metrics.celery_tasks_total.toLocaleString()
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Celery Worker Tasks</div>
                <div className="text-2xl font-bold text-yellow-400">
                  {typeof prometheusMetrics.key_metrics.celery_worker_tasks === 'number'
                    ? prometheusMetrics.key_metrics.celery_worker_tasks.toLocaleString()
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">DB Connections Active</div>
                <div className="text-2xl font-bold text-red-400">
                  {typeof prometheusMetrics.key_metrics.db_connections_active === 'number'
                    ? prometheusMetrics.key_metrics.db_connections_active.toLocaleString()
                    : 'N/A'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
