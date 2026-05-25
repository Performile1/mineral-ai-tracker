"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { apiFetch } from "@/lib/apiClient";

// react-force-graph-2d uses browser canvas API — must be loaded client-side only
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface GraphNode {
  id: string;
  ticker: string;
  company_type: "PRODUCER" | "CONSUMER" | "UNKNOWN";
  company_name: string;
  primary_sector: string | null;
  domicile_country: string | null;
  dilution_risk_score: number | null;
  buyout_probability_score: number | null;
  chokepoint_exposure?: number | null;
  group: string;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship_strength: string;
  raw_material_type: string | null;
  contract_type: "STANDARD" | "OFFTAKE" | "TAKE_OR_PAY";
  contract_volume_numeric: number | null;
  contract_expiry_date: string | null;
  is_expiry_estimated?: boolean;
  geopolitical_friction_cost?: number | null;
  is_binding: boolean;
  line_style: "solid" | "dashed";
  line_width: number;
  expected_materialization_date: string | null;
  source_document: string | null;
}

interface NexusGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
  binding_edges: number;
  intent_edges: number;
  available_materials: string[];
}

interface GeoEdge {
  id: string;
  source: string;
  target: string;
  raw_material_type: string | null;
  geopolitical_friction_cost: number | null;
  geo_policy_type: string | null;
  geo_status: string | null;
  geo_color: string;
  upstream_country: string | null;
  downstream_country: string | null;
}

interface GeoEdgesResponse {
  total_edges: number;
  status_counts: Record<string, number>;
  edges: GeoEdge[];
}

// ---------------------------------------------------------------------------
// Color maps
// ---------------------------------------------------------------------------
const GEO_STATUS_COLORS: Record<string, string> = {
  SUBSIDISED: "#4ade80",   // neon green – IRA / allied
  COMPLIANT:  "#4ade80",
  FRICTION:   "#f59e0b",   // amber – tariff / CBAM
  TOXIC:      "#dc2626",   // blood red – heavy tariff
  SANCTIONED: "#dc2626",
  UNKNOWN:    "#6b7280",   // gray
};

const NODE_COLORS: Record<string, string> = {
  PRODUCER: "#b45309",   // amber – upstream miners
  CONSUMER: "#1d4ed8",   // blue  – downstream manufacturers
  UNKNOWN: "#6b7280",
};

const MATERIAL_COLORS: Record<string, string> = {
  Copper: "#b45309", Zinc: "#0284c7", Uranium: "#92400e",
  Neodymium: "#be185d", Lithium: "#047857", "Iron Ore": "#374151",
  Aluminum: "#6d28d9", Nickel: "#065f46",
};

const STRENGTH_LABELS: Record<string, string> = {
  CONFIRMED_NAME: "Confirmed Contract",
  REVENUE_CONCENTRATION: "Revenue Concentration",
  INTENT_MOU: "MoU",
  INTENT_LOI: "LoI",
  INFERRED: "Inferred",
};

// ---------------------------------------------------------------------------
// Link Tooltip — shown on edge hover
// ---------------------------------------------------------------------------
function LinkTooltip({ link }: { link: GraphEdge | null }) {
  if (!link) return null;
  const isTop = link.contract_type === "TAKE_OR_PAY";
  return (
    <div className="absolute top-4 right-4 bg-gray-900 border border-gray-700 rounded-xl shadow-lg p-4 text-sm z-10 min-w-[220px] pointer-events-none">
      {isTop && (
        <div className="flex items-center gap-1.5 mb-2">
          <span className="text-green-400 text-base">🔒</span>
          <span className="text-green-400 font-bold text-xs uppercase tracking-widest">Take-or-Pay</span>
        </div>
      )}
      <div className="text-gray-300 font-semibold">
        {link.source as string} → {link.target as string}
      </div>
      {link.raw_material_type && (
        <div className="text-xs text-gray-400 mt-1">Material: {link.raw_material_type}</div>
      )}
      {link.contract_volume_numeric != null && (
        <div className="text-xs text-gray-400">Volume: {link.contract_volume_numeric.toLocaleString()} units</div>
      )}
      {link.contract_expiry_date && (
        <div className="text-xs text-gray-400">Expires: {link.contract_expiry_date}</div>
      )}
      {!isTop && (
        <div className="text-xs text-gray-500 mt-1">{link.relationship_strength.replace(/_/g, " ")}</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// God Mode — Domicile Override Panel
// ---------------------------------------------------------------------------
function GodModePanel({
  node,
  onClose,
  onSaved,
}: {
  node: GraphNode;
  onClose: () => void;
  onSaved: (ticker: string, newCountry: string) => void;
}) {
  const [country, setCountry] = useState(node.domicile_country ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async () => {
    const code = country.trim().toUpperCase();
    if (code.length < 2 || code.length > 3) {
      setError("Enter a 2–3 character ISO country code (e.g. US, CA, AU)");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/nexus/node/${node.ticker}/domicile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manual_country_code: code }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `HTTP ${res.status}`);
      }
      setSuccess(true);
      onSaved(node.ticker, code);
      setTimeout(onClose, 1200);
    } catch (err: any) {
      setError(err.message ?? "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl p-6 w-80">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-xs font-bold text-red-400 uppercase tracking-widest mb-0.5">
              ⚡ God Mode
            </div>
            <div className="text-white font-bold text-lg">{node.ticker}</div>
            <div className="text-gray-400 text-xs">{node.company_name}</div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Current value */}
        <div className="text-xs text-gray-500 mb-1">Domicile Country</div>
        <input
          value={country}
          onChange={(e) => { setCountry(e.target.value); setError(null); setSuccess(false); }}
          maxLength={3}
          placeholder="e.g. CA"
          className="w-full bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 uppercase tracking-widest focus:outline-none focus:border-blue-500"
        />
        {error && <div className="text-red-400 text-xs mt-1">{error}</div>}
        {success && <div className="text-green-400 text-xs mt-1">✓ Saved — geo-friction re-evaluating…</div>}

        <p className="text-gray-500 text-xs mt-2 mb-4">
          ISO-2 codes: US · CA · AU · GB · CN · ZA · CL · PE
        </p>

        <button
          onClick={handleSave}
          disabled={saving || success}
          className="w-full py-2 bg-red-700 hover:bg-red-600 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {saving ? "Saving…" : "Override & Re-evaluate"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Legend
// ---------------------------------------------------------------------------
function NexusLegend() {
  return (
    <div className="bg-white rounded-xl shadow p-4 text-xs space-y-3">
      <div className="font-semibold text-gray-700 text-sm">Legend</div>
      <div>
        <div className="font-medium text-gray-500 mb-1">Nodes</div>
        <div className="flex items-center gap-2 mb-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: NODE_COLORS.PRODUCER }} />
          <span>Upstream (Miner / Smelter)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: NODE_COLORS.CONSUMER }} />
          <span>Downstream (Manufacturer)</span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="w-3 h-3 rounded-full inline-block bg-red-500 ring-2 ring-red-400 ring-offset-1" />
          <span className="text-red-400">Active labour dispute</span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span
            className="w-3 h-3 rounded-full inline-block border-2 border-dashed"
            style={{ borderColor: "#f59e0b", background: "transparent" }}
          />
          <span className="text-yellow-500">Dilution Risk &gt; 75%</span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="w-3 h-3 rounded-full inline-block" style={{ background: "#d97706", boxShadow: "0 0 4px #fbbf24" }} />
          <span className="text-amber-500">M&amp;A Target (&gt;60%)</span>
        </div>
      </div>
      <div>
        <div className="font-medium text-gray-500 mb-1">Edge Strength</div>
        {Object.entries(STRENGTH_LABELS).map(([k, label]) => (
          <div key={k} className="flex items-center gap-2 mb-1">
            <svg width="24" height="8">
              <line
                x1="0" y1="4" x2="24" y2="4"
                strokeDasharray={k.startsWith("INTENT") || k === "INFERRED" ? "4 3" : undefined}
                stroke={k === "CONFIRMED_NAME" ? "#16a34a" : k === "REVENUE_CONCENTRATION" ? "#0284c7" : "#9ca3af"}
                strokeWidth={k === "CONFIRMED_NAME" ? 3 : k === "REVENUE_CONCENTRATION" ? 2 : 1}
              />
            </svg>
            <span>{label}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 mt-2 mb-1">
          <svg width="24" height="8">
            <line x1="0" y1="4" x2="24" y2="4" stroke="#22c55e" strokeWidth={6} />
          </svg>
          <span className="flex items-center gap-1">🔒 <span className="text-green-400">Take-or-Pay</span></span>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <svg width="24" height="8">
            <line x1="0" y1="4" x2="24" y2="4" stroke="#f97316" strokeWidth={3} />
          </svg>
          <span className="text-orange-400">Chokepoint stress</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Subscription Modal (Sprint 15)
// ---------------------------------------------------------------------------
function SubscriptionModal({
  node,
  onClose,
}: {
  node: GraphNode;
  onClose: () => void;
}) {
  const [threshold, setThreshold] = useState(75);
  const [existing, setExisting] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    apiFetch("/api/settings/alerts/subscriptions")
      .then((r) => (r.ok ? r.json() : []))
      .then((subs: Array<{ ticker: string; risk_threshold: number }>) => {
        const match = subs.find((s) => s.ticker === node.ticker);
        if (match) {
          setExisting(match.risk_threshold);
          setThreshold(match.risk_threshold);
        }
      })
      .catch(() => {});
  }, [node.ticker]);

  const handleSave = async () => {
    setSaving(true);
    setFeedback(null);
    try {
      const res = await apiFetch("/api/settings/alerts/subscriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: node.ticker, risk_threshold: threshold }),
      });
      if (!res.ok) throw new Error("Failed");
      setExisting(threshold);
      setFeedback(`✅ Larm sparat för ${node.ticker} vid ${threshold}% risk`);
    } catch {
      setFeedback("❌ Kunde inte spara prenumerationen");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    setFeedback(null);
    try {
      const res = await apiFetch(`/api/settings/alerts/subscriptions/${node.ticker}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed");
      setExisting(null);
      setFeedback(`🗑 Larm borttaget för ${node.ticker}`);
    } catch {
      setFeedback("❌ Kunde inte ta bort prenumerationen");
    } finally {
      setDeleting(false);
    }
  };

  const riskColor =
    threshold > 75 ? "text-red-400" : threshold > 40 ? "text-amber-400" : "text-green-400";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl p-6 w-80 text-white">
        <div className="flex justify-between items-center mb-4">
          <div>
            <div className="text-lg font-bold">{node.ticker}</div>
            <div className="text-xs text-gray-400">{node.company_name}</div>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-xl leading-none">&times;</button>
        </div>

        {existing !== null && (
          <div className="mb-3 text-xs px-3 py-1.5 rounded-lg bg-blue-900/50 border border-blue-700 text-blue-300">
            🔔 Aktivt larm vid {existing}% risk
          </div>
        )}

        <label className="block text-sm text-gray-300 mb-1">
          Larma mig när risken överstiger{" "}
          <span className={`font-bold ${riskColor}`}>{threshold}%</span>
        </label>
        <input
          type="range"
          min={1}
          max={100}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          className="w-full accent-blue-500 mb-4"
        />
        <div className="flex justify-between text-xs text-gray-500 -mt-3 mb-4">
          <span>1%</span><span>50%</span><span>100%</span>
        </div>

        {feedback && (
          <div className="mb-3 text-xs text-center text-gray-300 bg-gray-800 rounded-lg px-3 py-2">
            {feedback}
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded-lg text-sm font-semibold transition-colors"
          >
            {saving ? "Sparar..." : "🔔 Spara larm"}
          </button>
          {existing !== null && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="py-2 px-3 bg-red-700 hover:bg-red-600 disabled:opacity-50 rounded-lg text-sm transition-colors"
              title="Ta bort larm"
            >
              {deleting ? "..." : "🗑"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tooltip card
// ---------------------------------------------------------------------------
function NodeTooltip({ node }: { node: GraphNode | null }) {
  if (!node) return null;
  return (
    <div className="absolute top-4 left-4 bg-white rounded-xl shadow-lg p-4 text-sm z-10 min-w-[180px] pointer-events-none">
      <div className="font-bold text-gray-900 text-base">{node.ticker}</div>
      <div className="text-gray-600">{node.company_name}</div>
      <div className="mt-1">
        <span
          className="text-xs px-2 py-0.5 rounded-full font-semibold"
          style={{
            background: NODE_COLORS[node.company_type] + "22",
            color: NODE_COLORS[node.company_type],
          }}
        >
          {node.company_type}
        </span>
      </div>
      {node.primary_sector && (
        <div className="text-xs text-gray-400 mt-1">{node.primary_sector}</div>
      )}
      {node.domicile_country && (
        <div className="text-xs text-gray-500 mt-0.5">🌍 {node.domicile_country}</div>
      )}
      {node.dilution_risk_score != null && (
        <div
          className="text-xs font-semibold mt-1"
          style={{ color: node.dilution_risk_score > 75 ? "#ef4444" : node.dilution_risk_score > 40 ? "#f59e0b" : "#22c55e" }}
        >
          ⚠️ Dilution Risk: {Math.round(node.dilution_risk_score)}%
        </div>
      )}
      {node.buyout_probability_score != null && (
        <div
          className="text-xs font-semibold mt-1"
          style={{ color: node.buyout_probability_score > 60 ? "#d97706" : "#6b7280" }}
        >
          💰 M&amp;A Score: {Math.round(node.buyout_probability_score)}%
          {node.dilution_risk_score != null && node.buyout_probability_score > 60 && node.dilution_risk_score > 70 && (
            <span className="ml-1 text-amber-500 font-normal">↑ distressed asset</span>
          )}
        </div>
      )}
      <div className="text-xs text-gray-600 mt-1 italic">click: alarm · double-click: override country</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ForceDirectedGraph
// ---------------------------------------------------------------------------
function ForceDirectedGraph({
  graphData,
  selectedMaterial,
  showNonBinding,
  disputeTickers,
  geoMode,
  geoEdgeMap,
  maRadarMode,
  onNodeDoubleClick,
  onNodeClick,
}: {
  graphData: NexusGraphResponse;
  selectedMaterial: string;
  showNonBinding: boolean;
  disputeTickers: Set<string>;
  geoMode: boolean;
  geoEdgeMap: Map<string, GeoEdge>;
  maRadarMode: boolean;
  onNodeDoubleClick?: (node: GraphNode) => void;
  onNodeClick?: (node: GraphNode) => void;
}) {
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [hoveredLink, setHoveredLink] = useState<GraphEdge | null>(null);
  const fgRef = useRef<any>(null);
  const lastClickRef = useRef<{ id: string; time: number } | null>(null);
  const singleClickTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const filteredEdges = graphData.edges.filter((e) => {
    if (!showNonBinding && !e.is_binding) return false;
    if (selectedMaterial && e.raw_material_type !== selectedMaterial) return false;
    return true;
  });

  const visibleTickers = new Set<string>();
  filteredEdges.forEach((e) => {
    visibleTickers.add(e.source as string);
    visibleTickers.add(e.target as string);
  });

  const filteredNodes = graphData.nodes.filter((n) => visibleTickers.has(n.id));

  const fgNodes = filteredNodes.map((n) => ({ ...n, hasDispute: disputeTickers.has(n.id) }));
  const fgLinks = filteredEdges.map((e) => ({
    ...e,
    source: e.source,
    target: e.target,
  }));

  const drawLink = useCallback((link: any, ctx: CanvasRenderingContext2D) => {
    const start = link.source;
    const end = link.target;
    if (!start || !end || !start.x || !end.x) return;

    // Sprint 16 — Chokepoint Oracle: pulsing orange for elevated friction_cost
    const frictionCost = link.geopolitical_friction_cost as number | null;
    if (!geoMode && frictionCost != null && frictionCost > 0) {
      const alpha = 0.55 + Math.abs(Math.sin(Date.now() / 500)) * 0.45;
      ctx.beginPath();
      ctx.strokeStyle = `rgba(249, 115, 22, ${alpha.toFixed(2)})`;
      ctx.lineWidth = (link.line_width || 1) + 1.5;
      ctx.setLineDash([]);
      ctx.moveTo(start.x, start.y);
      ctx.lineTo(end.x, end.y);
      ctx.stroke();
      return;
    }

    const isTop = link.contract_type === "TAKE_OR_PAY";
    let color: string;
    let lineWidth = link.line_width || 1;

    if (isTop && !geoMode) {
      color = "#22c55e";
      lineWidth = Math.max(lineWidth, 6);
    } else if (geoMode) {
      const geoEdge = geoEdgeMap.get(link.id);
      color = geoEdge?.geo_color ?? GEO_STATUS_COLORS.UNKNOWN;
      lineWidth = 2;
    } else {
      const material = link.raw_material_type || "";
      color = MATERIAL_COLORS[material] || "#9ca3af";
    }

    ctx.beginPath();
    ctx.strokeStyle = link.is_binding ? color : color + "88";
    ctx.lineWidth = lineWidth;

    if (!link.is_binding && !geoMode && !isTop) {
      ctx.setLineDash([4, 3]);
    } else {
      ctx.setLineDash([]);
    }

    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.stroke();
    ctx.setLineDash([]);
  }, [geoMode, geoEdgeMap]);

  const handleNodeClick = useCallback((node: any) => {
    const now = Date.now();
    if (
      lastClickRef.current &&
      lastClickRef.current.id === node.id &&
      now - lastClickRef.current.time < 350
    ) {
      // Double-click detected: cancel pending single-click and fire double-click
      if (singleClickTimer.current) {
        clearTimeout(singleClickTimer.current);
        singleClickTimer.current = null;
      }
      lastClickRef.current = null;
      if (onNodeDoubleClick) onNodeDoubleClick(node as GraphNode);
    } else {
      lastClickRef.current = { id: node.id, time: now };
      // Schedule single-click after double-click window
      if (singleClickTimer.current) clearTimeout(singleClickTimer.current);
      singleClickTimer.current = setTimeout(() => {
        singleClickTimer.current = null;
        if (onNodeClick) onNodeClick(node as GraphNode);
      }, 360);
    }
  }, [onNodeDoubleClick, onNodeClick]);

  return (
    <div className="relative w-full h-full bg-gray-950 rounded-xl overflow-hidden">
      <NodeTooltip node={hoveredNode} />
      {!hoveredNode && <LinkTooltip link={hoveredLink} />}
      {onNodeDoubleClick && (
        <div className="absolute bottom-3 right-3 z-10 text-xs text-gray-600 pointer-events-none select-none">
          Double-click node to override country
        </div>
      )}
      <ForceGraph2D
        ref={fgRef}
        graphData={{ nodes: fgNodes, links: fgLinks }}
        nodeId="id"
        nodeColor={(n: any) => NODE_COLORS[n.company_type] || NODE_COLORS.UNKNOWN}
        nodeLabel={(n: any) => `${n.ticker} (${n.company_type})`}
        nodeRelSize={6}
        linkCanvasObjectMode={() => "replace"}
        linkCanvasObject={drawLink}
        onNodeClick={handleNodeClick}
        onNodeHover={(n: any) => { setHoveredNode(n || null); if (n) setHoveredLink(null); }}
        onLinkHover={(l: any) => setHoveredLink(l || null)}
        linkDirectionalParticles={(l: any) => l.contract_type === "TAKE_OR_PAY" ? 4 : 0}
        linkDirectionalParticleSpeed={0.02}
        linkDirectionalParticleColor={() => "#22c55e"}
        linkDirectionalParticleWidth={2}
        backgroundColor="#030712"
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.ticker;
          const fontSize = Math.max(10 / globalScale, 4);
          const r = 6;
          const hasDispute = node.hasDispute as boolean;

          if (hasDispute) {
            // Pulsing red halo — radius oscillates with time
            const pulse = r + 3 + Math.sin(Date.now() / 300) * 2;
            ctx.beginPath();
            ctx.arc(node.x, node.y, pulse, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(239, 68, 68, 0.25)";
            ctx.fill();
            ctx.beginPath();
            ctx.arc(node.x, node.y, pulse, 0, 2 * Math.PI);
            ctx.strokeStyle = "#ef4444";
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }

          // Sprint 10.9 — Dilution Risk warning ring (static, amber)
          const dilutionRisk = node.dilution_risk_score as number | null;
          if (dilutionRisk != null && dilutionRisk > 75) {
            ctx.beginPath();
            ctx.arc(node.x, node.y, r + 5, 0, 2 * Math.PI);
            ctx.strokeStyle = "#f59e0b";
            ctx.lineWidth = 2;
            ctx.setLineDash([3, 2]);
            ctx.stroke();
            ctx.setLineDash([]);
          }

          // Sprint 16 — M&A Radar: pulsing gold halo for buyout targets
          const buyoutScore = node.buyout_probability_score as number | null;
          if (maRadarMode && buyoutScore != null && buyoutScore > 60) {
            const pulse = r + 4 + Math.sin(Date.now() / 400) * 2;
            ctx.beginPath();
            ctx.arc(node.x, node.y, pulse, 0, 2 * Math.PI);
            ctx.fillStyle = "rgba(251, 191, 36, 0.18)";
            ctx.fill();
            ctx.beginPath();
            ctx.arc(node.x, node.y, pulse, 0, 2 * Math.PI);
            ctx.strokeStyle = "#fbbf24";
            ctx.lineWidth = 2;
            ctx.setLineDash([]);
            ctx.stroke();
          }

          const isMATarget = maRadarMode && buyoutScore != null && buyoutScore > 60;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
          ctx.fillStyle = hasDispute
            ? "#ef4444"
            : isMATarget
            ? "#d97706"
            : NODE_COLORS[node.company_type] || NODE_COLORS.UNKNOWN;
          ctx.fill();

          if (globalScale >= 1.2) {
            ctx.font = `${fontSize}px Inter, sans-serif`;
            ctx.fillStyle = hasDispute ? "#fca5a5" : "#f9fafb";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, node.x, node.y + r + 2);
          }
        }}
        onRenderFramePre={() => { /* triggers re-render for pulse animation */ }}
        width={undefined}
        height={undefined}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function NexusPage() {
  const [graphData, setGraphData] = useState<NexusGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMaterial, setSelectedMaterial] = useState("");
  const [showNonBinding, setShowNonBinding] = useState(true);
  const [disputeTickers, setDisputeTickers] = useState<Set<string>>(new Set());
  const [geoMode, setGeoMode] = useState(false);
  const [geoEdgeMap, setGeoEdgeMap] = useState<Map<string, GeoEdge>>(new Map());
  const [geoStatusCounts, setGeoStatusCounts] = useState<Record<string, number>>({});
  // God Mode state
  const [godModeNode, setGodModeNode] = useState<GraphNode | null>(null);
  // Sprint 15 — Subscription modal
  const [subscriptionNode, setSubscriptionNode] = useState<GraphNode | null>(null);
  // Sprint 16 — M&A Radar mode
  const [maRadarMode, setMaRadarMode] = useState(false);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (selectedMaterial) params.set("material", selectedMaterial);
      params.set("include_non_binding", String(showNonBinding));

      const [graphRes, disputeRes, geoRes] = await Promise.all([
        apiFetch(`/api/nexus/graph?${params.toString()}`),
        apiFetch(`/api/black-swan/labor-disputes/active-tickers`),
        apiFetch(`/api/trade-policy/nexus-geo-edges`),
      ]);
      if (!graphRes.ok) throw new Error("Failed to load nexus graph");
      setGraphData(await graphRes.json());
      if (disputeRes.ok) {
        const tickers: string[] = await disputeRes.json();
        setDisputeTickers(new Set(tickers));
      }
      if (geoRes.ok) {
        const geoData: GeoEdgesResponse = await geoRes.json();
        const edgeMap = new Map<string, GeoEdge>();
        geoData.edges.forEach((e) => edgeMap.set(e.id, e));
        setGeoEdgeMap(edgeMap);
        setGeoStatusCounts(geoData.status_counts);
      }
    } catch (err) {
      setError("Failed to load Nexus graph. Ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, [selectedMaterial, showNonBinding]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex-shrink-0">
        <div className="max-w-screen-2xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">The Nexus</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Global supply chain topology — upstream miners ↔ downstream manufacturers
            </p>
          </div>

          {/* Controls */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Material filter */}
            <select
              value={selectedMaterial}
              onChange={(e) => setSelectedMaterial(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none"
            >
              <option value="">All Materials</option>
              {graphData?.available_materials.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>

            {/* Non-binding toggle */}
            <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer select-none">
              <div
                onClick={() => setShowNonBinding(!showNonBinding)}
                className={`relative w-10 h-5 rounded-full transition-colors ${
                  showNonBinding ? "bg-blue-600" : "bg-gray-600"
                }`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
                  showNonBinding ? "translate-x-5" : "translate-x-0.5"
                }`} />
              </div>
              Show MoU / LoI
            </label>

            {/* Geopolitics Mode toggle */}
            <button
              onClick={() => setGeoMode(!geoMode)}
              className={`flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg border transition-colors ${
                geoMode
                  ? "bg-red-900 border-red-600 text-red-200"
                  : "bg-gray-800 border-gray-600 text-gray-300 hover:bg-gray-700"
              }`}
            >
              <span>🌐</span>
              {geoMode ? "Geo Mode ON" : "Geopolitics Mode"}
            </button>

            {/* M&A Radar Mode toggle */}
            <button
              onClick={() => setMaRadarMode(!maRadarMode)}
              className={`flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-lg border transition-colors ${
                maRadarMode
                  ? "bg-amber-900 border-amber-600 text-amber-200"
                  : "bg-gray-800 border-gray-600 text-gray-300 hover:bg-gray-700"
              }`}
            >
              <span>💰</span>
              {maRadarMode ? "M&A Radar ON" : "M&A Radar"}
            </button>

            <button
              onClick={loadGraph}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-500 disabled:opacity-50"
            >
              {loading ? "Loading…" : "↻ Refresh"}
            </button>
          </div>
        </div>

        {/* Stats bar */}
        {graphData && (
          <div className="max-w-screen-2xl mx-auto mt-3 flex flex-wrap gap-6 text-sm text-gray-400">
            <span><span className="text-white font-semibold">{graphData.node_count}</span> companies</span>
            <span><span className="text-white font-semibold">{graphData.edge_count}</span> relationships</span>
            <span><span className="text-green-400 font-semibold">{graphData.binding_edges}</span> confirmed contracts</span>
            <span><span className="text-amber-400 font-semibold">{graphData.intent_edges}</span> intent signals (MoU/LoI)</span>
            {geoMode && Object.entries(geoStatusCounts).length > 0 && (
              <span className="border-l border-gray-700 pl-6 flex gap-4">
                {geoStatusCounts["SANCTIONED"] && (
                  <span><span className="text-red-400 font-semibold">{geoStatusCounts["SANCTIONED"]}</span> sanctioned</span>
                )}
                {geoStatusCounts["TOXIC"] && (
                  <span><span className="text-red-500 font-semibold">{geoStatusCounts["TOXIC"]}</span> toxic</span>
                )}
                {geoStatusCounts["FRICTION"] && (
                  <span><span className="text-amber-400 font-semibold">{geoStatusCounts["FRICTION"]}</span> friction</span>
                )}
                {geoStatusCounts["SUBSIDISED"] && (
                  <span><span className="text-green-400 font-semibold">{geoStatusCounts["SUBSIDISED"]}</span> subsidised</span>
                )}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Main content */}
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <div className="w-52 flex-shrink-0 bg-gray-900 border-r border-gray-800 p-4 overflow-y-auto">
          <NexusLegend />
          {geoMode && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="font-semibold text-gray-400 text-xs mb-2">Sovereign Firewall</div>
              {([
                ["#4ade80", "Subsidised (IRA)"],
                ["#4ade80", "Compliant (Allied)"],
                ["#f59e0b", "Friction (Tariff/CBAM)"],
                ["#dc2626", "Toxic (>40% tariff)"],
                ["#dc2626", "Sanctioned / Blocked"],
                ["#6b7280", "Unknown"],
              ] as [string, string][]).map(([color, label]) => (
                <div key={label} className="flex items-center gap-2 mb-1 text-xs">
                  <span className="w-4 h-1.5 rounded-full inline-block" style={{ background: color }} />
                  <span className="text-gray-300">{label}</span>
                </div>
              ))}
            </div>
          )}
          {maRadarMode && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="font-semibold text-amber-400 text-xs mb-2">💰 M&amp;A Radar</div>
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ background: "#d97706", boxShadow: "0 0 5px #fbbf24" }} />
                  <span className="text-gray-300">Score &gt; 60%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full border border-amber-400" style={{ background: "transparent" }} />
                  <span className="text-gray-300">Pulsing gold halo</span>
                </div>
                <p className="text-gray-500 pt-1">High dilution + Take-or-Pay = prime target</p>
              </div>
            </div>
          )}
        </div>

        {/* Graph canvas */}
        <div className="flex-1 relative">
          {error && (
            <div className="absolute inset-0 flex items-center justify-center z-20">
              <div className="bg-red-950 border border-red-700 text-red-300 rounded-xl px-6 py-4 text-sm max-w-sm text-center">
                {error}
              </div>
            </div>
          )}

          {loading && !graphData && (
            <div className="absolute inset-0 flex items-center justify-center z-20 bg-gray-950/80">
              <div className="text-gray-400 text-sm animate-pulse">Building supply chain graph…</div>
            </div>
          )}

          {graphData && (
            <div className="absolute inset-0">
              <ForceDirectedGraph
                graphData={graphData}
                selectedMaterial={selectedMaterial}
                showNonBinding={showNonBinding}
                disputeTickers={disputeTickers}
                geoMode={geoMode}
                geoEdgeMap={geoEdgeMap}
                maRadarMode={maRadarMode}
                onNodeDoubleClick={(node) => setGodModeNode(node)}
                onNodeClick={(node) => setSubscriptionNode(node)}
              />
            </div>
          )}

          {/* God Mode panel */}
          {godModeNode && (
            <GodModePanel
              node={godModeNode}
              onClose={() => setGodModeNode(null)}
              onSaved={(ticker, newCountry) => {
                setGraphData((prev) =>
                  prev
                    ? {
                        ...prev,
                        nodes: prev.nodes.map((n) =>
                          n.ticker === ticker ? { ...n, domicile_country: newCountry } : n
                        ),
                      }
                    : prev
                );
              }}
            />
          )}

          {subscriptionNode && (
            <SubscriptionModal
              node={subscriptionNode}
              onClose={() => setSubscriptionNode(null)}
            />
          )}

          {graphData?.node_count === 0 && !loading && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
              No graph data yet. Trigger a Nexus Engine nightly run to populate nodes and edges.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
