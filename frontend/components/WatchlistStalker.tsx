"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/apiClient";

type StalkerStage = "idle" | "discovery" | "crawl" | "phi3" | "mistral" | "llama3" | "done" | "error" | "processing"; // PRD v10.0 Phase 10.3: Added "processing" for Celery

interface StalkerArticle {
  title: string;
  url: string;
  pub_date?: string;
  summary?: string;
  fetched_chars: number;
}

interface DebateStep {
  slm: string;
  reasoning: string;
  confidence: number;
}

interface StalkerResult {
  ticker: string;
  signal_type: string;
  confidence_score: number;
  recommendation: string;
  consensus_score: number;
  pydantic_passed: boolean;
  pydantic_errors: string[];
  debate_log: DebateStep[];
  elapsed_seconds: number;
  // Articles returned by the stalker pipeline; optional because legacy payloads omit them.
  articles?: StalkerArticle[];
}

const STAGES: { key: Exclude<StalkerStage, "idle" | "done" | "error">; label: string; hint: string }[] = [
  { key: "discovery", label: "1. Discovery",    hint: "Yahoo Finance RSS" },
  { key: "crawl",     label: "2. Crawl",        hint: "Crawl4AI parallel fetch" },
  { key: "phi3",      label: "3. Phi-3",        hint: "Extract structured JSON" },
  { key: "mistral",   label: "4. Mistral",      hint: "Geology expert debate" },
  { key: "llama3",    label: "5. Llama-3",      hint: "Risk manager debate" },
];

const stageOrder: StalkerStage[] = ["discovery", "crawl", "phi3", "mistral", "llama3", "done"];

interface AvailableModel {
  id: string;
  name: string;
  cost: number;
  available: boolean;
  description: string;
}

export default function WatchlistStalker() {
  const [ticker, setTicker] = useState("");
  const [stage, setStage] = useState<StalkerStage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StalkerResult | null>(null);
  const [articles, setArticles] = useState<StalkerArticle[]>([]);
  const [shareWithHive, setShareWithHive] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null); // PRD v10.0 Phase 10.3: Celery task ID
  const [pollCount, setPollCount] = useState(0); // PRD v10.0 Phase 10.4: Poll counter for timeout
  const startRef = useRef<number>(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  // Phase 13.2: Model selector state
  const [selectedModel, setSelectedModel] = useState("local_swarm");
  const [availableModels, setAvailableModels] = useState<AvailableModel[]>([]);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Phase 13.2: Fetch available models on mount
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await apiFetch("/api/intelligence/models/available");
        const data = await res.json();
        setAvailableModels(data.models);
        // Set default to first available model
        if (data.models.length > 0) {
          setSelectedModel(data.models[0].id);
        }
      } catch (e) {
        console.error("Failed to fetch available models:", e);
        // Fallback to local swarm if fetch fails
        setAvailableModels([
          { id: "local_swarm", name: "Local Swarm (Llama-3)", cost: 1, available: true, description: "Fast local analysis" }
        ]);
      }
    };
    fetchModels();
  }, [apiUrl]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // PRD v10.0 Phase 10.3: Poll for task status when using Celery
  // PRD v10.0 Phase 10.4: Added 5-minute timeout (60 attempts at 5 seconds)
  useEffect(() => {
    if (taskId && stage === "processing") {
      intervalRef.current = setInterval(async () => {
        try {
          const res = await apiFetch(`/api/watchlist/status/${taskId}`);
          const data = await res.json();
          
          if (data.status === "SUCCESS") {
            setStage("done");
            setResult(data.result);
            setTaskId(null);
            setPollCount(0);
            if (intervalRef.current) clearInterval(intervalRef.current);
          } else if (data.status === "FAILURE" || data.status === "FAILED_TIMEOUT") {
            setError(`Analysis failed: ${data.error}`);
            setStage("error");
            setTaskId(null);
            setPollCount(0);
            if (intervalRef.current) clearInterval(intervalRef.current);
          } else if (data.status === "PENDING") {
            setPollCount(prev => {
              const newCount = prev + 1;
              // PRD v10.0 Phase 10.4: Timeout after 60 attempts (5 minutes)
              if (newCount >= 60) {
                setError("Svärmen är extremt överbelastad just nu. Vi har sparat din förfrågan i bakgrunden och The Sentinel kommer att pinga dig på Discord/Telegram när din analys är klar.");
                setStage("error");
                setTaskId(null);
                if (intervalRef.current) clearInterval(intervalRef.current);
                return 0;
              }
              return newCount;
            });
          }
        } catch (err) {
          console.error("Failed to check task status:", err);
        }
      }, 5000); // Poll every 5 seconds
    }
    
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [taskId, stage, apiUrl]);

  // Auto-advance stage progress while we wait for the backend. Each stage
  // gets a heuristic duration; the final state is set by the API response.
  useEffect(() => {
    if (stage === "idle" || stage === "done" || stage === "error") return;
    const durations: Record<string, number> = {
      discovery: 2_000,
      crawl: 8_000,
      phi3: 25_000,
      mistral: 30_000,
      llama3: 35_000,
    };
    const t = setTimeout(() => {
      const idx = stageOrder.indexOf(stage);
      if (idx >= 0 && idx < stageOrder.length - 1) {
        setStage(stageOrder[idx + 1]);
      }
    }, durations[stage] ?? 5_000);
    return () => clearTimeout(t);
  }, [stage]);

  const runStalker = async () => {
    if (!ticker.trim()) return;
    try {
      setError(null);
      setStage("discovery");
      setArticles([]);
      setResult(null);
      setTaskId(null);
      startRef.current = Date.now();

      const res = await apiFetch(`/api/watchlist/stalk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          ticker, 
          max_articles: 3, 
          is_public: shareWithHive,
          ai_model: selectedModel  // Phase 13.2: Pass selected AI model
        }),
      });

      if (!res.ok) {
        throw new Error("Failed to trigger analysis");
      }

      const data = await res.json();

      // PRD v10.0 Phase 10.3: If task_id is returned, use polling
      if (data.task_id) {
        setTaskId(data.task_id);
        setStage("processing");
        return;
      }

      // Synchronous response (original behavior)
      setArticles(data.articles);
      setResult({
        ticker: data.ticker,
        signal_type: data.signal_type,
        confidence_score: data.confidence_score,
        recommendation: data.recommendation,
        consensus_score: data.consensus_score,
        pydantic_passed: data.pydantic_passed,
        pydantic_errors: data.pydantic_errors,
        debate_log: data.debate_log,
        elapsed_seconds: data.elapsed_seconds,
      });
      setStage("done");
    } catch (err) {
      console.error("Stalker error:", err);
      setError(err instanceof Error ? err.message : "Analysis failed");
      setStage("error");
    } finally {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  };

  const stageStatus = (s: Exclude<StalkerStage, "idle" | "done" | "error">) => {
    if (stage === "idle") return "pending";
    if (stage === "error") return "error";
    if (stage === "done") return "complete";
    const currentIdx = stageOrder.indexOf(stage);
    const thisIdx = stageOrder.indexOf(s);
    if (thisIdx < currentIdx) return "complete";
    if (thisIdx === currentIdx) return "active";
    return "pending";
  };

  const signalColor = (type: string) => {
    const t = (type || "").toUpperCase();
    if (t === "BUY") return "bg-buy text-white";
    if (t === "SELL" || t === "SHORT") return "bg-warning text-white";
    return "bg-gray-300 text-text";
  };

  return (
    <div className="bg-surface border border-gray-200 rounded-lg p-5">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-semibold text-text uppercase tracking-wider">
          Watchlist Stalker
        </h3>
        <span className="text-[10px] text-muted">On-demand Multi-SLM</span>
      </div>

      {/* Search bar */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && runStalker()}
          placeholder="e.g. BOL.ST"
          disabled={stage !== "idle" && stage !== "done" && stage !== "error"}
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm uppercase tracking-wider text-text focus:outline-none focus:ring-2 focus:ring-buy"
        />
        <button
          onClick={runStalker}
          disabled={!ticker.trim() || (stage !== "idle" && stage !== "done" && stage !== "error")}
          className="bg-buy text-white px-4 py-2 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-40"
        >
          Stalk
        </button>
      </div>

      {/* Phase 13.2: AI Model Selector */}
      <div className="mb-3">
        <label className="block text-xs font-medium text-text mb-2">
          AI Model
        </label>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          disabled={stage !== "idle" && stage !== "done" && stage !== "error"}
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-text focus:outline-none focus:ring-2 focus:ring-buy disabled:opacity-40"
        >
          {availableModels.map((model) => (
            <option key={model.id} value={model.id}>
              {model.name} - {model.cost} Credit{model.cost !== 1 ? 's' : ''}
            </option>
          ))}
        </select>
        <p className="text-[10px] text-muted mt-1">
          {availableModels.find(m => m.id === selectedModel)?.description}
        </p>
      </div>

      {/* Hive Mind opt-in toggle */}
      <div className="flex items-center gap-2 mb-4 p-2 bg-gray-50 rounded-md">
        <input
          type="checkbox"
          id="share-with-hive"
          checked={shareWithHive}
          onChange={(e) => setShareWithHive(e.target.checked)}
          disabled={stage !== "idle" && stage !== "done" && stage !== "error"}
          className="w-4 h-4 text-buy rounded focus:ring-buy"
        />
        <label
          htmlFor="share-with-hive"
          className="text-xs text-text cursor-pointer"
        >
          🐝 Share with The Hive Mind (Anonymous Swarm Intelligence)
        </label>
      </div>

      {/* Pipeline */}
      <div className="space-y-2 mb-4">
        {STAGES.map((s) => {
          const status = stageStatus(s.key);
          const dot =
            status === "complete"
              ? "bg-buy"
              : status === "active"
              ? "bg-accent animate-pulse"
              : status === "error"
              ? "bg-warning"
              : "bg-gray-300";
          const labelColor =
            status === "active" ? "text-text font-semibold" : status === "complete" ? "text-buy" : "text-muted";
          return (
            <div key={s.key} className="flex items-center gap-3">
              <span className={`inline-block w-2.5 h-2.5 rounded-full ${dot}`} />
              <span className={`text-sm ${labelColor}`}>{s.label}</span>
              <span className="text-[10px] text-muted ml-auto">{s.hint}</span>
            </div>
          );
        })}
      </div>

      {/* Status line */}
      {(() => {
        // Local elapsed counter (seconds since the stalker was triggered).
        const elapsed = startRef.current ? (Date.now() - startRef.current) / 1000 : 0;
        return (stage !== "idle" && stage !== "done") && (
          <div className="text-xs text-muted mb-3">
            {stage === "error" ? "Failed" : `Working... ${elapsed.toFixed(1)}s`}
          </div>
        );
      })()}
      {error && <div className="text-xs text-warning mb-3">{error}</div>}

      {/* Result */}
      {result && stage === "done" && (
        <div className="border-t border-gray-200 pt-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${signalColor(result.signal_type)}`}>
                {result.signal_type}
              </span>
              <span className="text-sm font-semibold text-text">{result.ticker}</span>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-buy tabular-nums">
                {result.confidence_score}
              </div>
              <div className="text-[10px] text-muted">confidence</div>
            </div>
          </div>

          <p className="text-sm text-text">{result.recommendation}</p>

          <div className="flex justify-between text-[11px] text-muted">
            <span>Consensus {Math.round(result.consensus_score * 100)}%</span>
            <span>{(result.articles?.length ?? 0)} articles · {result.elapsed_seconds.toFixed(1)}s</span>
          </div>

          {/* Sources */}
          {(result.articles?.length ?? 0) > 0 && (
            <div className="space-y-1">
              {result.articles!.map((a: StalkerArticle, i: number) => (
                <a
                  key={i}
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-buy hover:underline truncate"
                  title={a.title}
                >
                  • {a.title || a.url}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
