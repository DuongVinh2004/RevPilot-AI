import React, { useState } from "react";
import { useSSE } from "../../hooks/useSSE";
import { InvestigationNodeCard, DAGNode } from "./InvestigationNodeCard";
import { CausalImpactChart } from "../charts/CausalImpactChart";
import {
  Radio,
  Users,
  Terminal,
  Play,
  Pause,
  StopCircle,
  Clock,
  Sparkles,
  ShieldCheck,
} from "lucide-react";

const initialNodes: DAGNode[] = [
  {
    node_id: "node_01_scope",
    label: "Scope & Entitlement Verification",
    status: "COMPLETED",
    progress_pct: 100,
    message: "Entitlements verified for tenant. Metric scope locked.",
    duration_ms: 140,
  },
  {
    node_id: "node_02_evidence",
    label: "Evidence Ledger Extraction",
    status: "COMPLETED",
    progress_pct: 100,
    message: "Retrieved 4 tamper-evident citations across billing & support logs.",
    duration_ms: 320,
  },
  {
    node_id: "node_03_causal",
    label: "Causal Estimand & Sensitivity Analysis",
    status: "COMPLETED",
    progress_pct: 100,
    message: "Doubly Robust AIPW point estimate: +0.066 (95% CI: [0.036, 0.096], E-value: 2.45).",
    duration_ms: 480,
  },
  {
    node_id: "node_04_decision",
    label: "Decision Optimization & Policy Check",
    status: "COMPLETED",
    progress_pct: 100,
    message: "Recommended action: ISSUE_SERVICE_CREDIT_VOUCHER with expected utility +$14,200.",
    duration_ms: 210,
  },
];

export const LiveInvestigationRoom: React.FC = () => {
  const [investigationId, setInvestigationId] = useState<string>("inv_01h8abcde12345");
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(true);
  const [nodes, setNodes] = useState<DAGNode[]>(initialNodes);

  // Connect to SSE stream
  const endpoint = isLiveStreaming ? `/api/v1/investigations/${investigationId}/stream` : null;
  const { messages, isConnected, error } = useSSE(endpoint);

  const startStream = () => {
    setIsLiveStreaming(true);
  };

  const stopStream = () => {
    setIsLiveStreaming(false);
  };

  return (
    <div className="space-y-6">
      {/* Stream Status Header & Analyst Presence */}
      <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                  isConnected
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                }`}
              >
                <Radio className={`w-3 h-3 ${isConnected ? "animate-pulse" : ""}`} />
                {isConnected ? "LIVE SSE STREAM ACTIVE" : "STREAM DISCONNECTED"}
              </span>
              <span className="font-mono text-xs text-slate-400">
                Temporal Workflow: tenant/tnt_dev_001/investigation/{investigationId}
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-100 mt-2">
              Live Autonomous Investigation & Causal Study Room
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Real-time multi-agent DAG execution. Invariant INV-ACT-001 strictly enforced: read-only capability catalog.
            </p>
          </div>

          {/* Active Analysts Presence Badge */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 px-3 py-1.5 rounded-lg text-xs">
              <Users className="w-4 h-4 text-indigo-400" />
              <span className="text-slate-300">
                Collaborating: <strong>3 Analysts Active</strong>
              </span>
              <div className="flex -space-x-1.5 ml-1">
                <span className="w-5 h-5 rounded-full bg-indigo-600 text-[10px] flex items-center justify-center font-bold text-white border border-slate-900">
                  DV
                </span>
                <span className="w-5 h-5 rounded-full bg-emerald-600 text-[10px] flex items-center justify-center font-bold text-white border border-slate-900">
                  AL
                </span>
                <span className="w-5 h-5 rounded-full bg-amber-600 text-[10px] flex items-center justify-center font-bold text-white border border-slate-900">
                  OP
                </span>
              </div>
            </div>

            {/* Stream Toggle */}
            {isLiveStreaming ? (
              <button
                onClick={stopStream}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 transition"
              >
                <Pause className="w-3.5 h-3.5" /> Pause Feed
              </button>
            ) : (
              <button
                onClick={startStream}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 transition"
              >
                <Play className="w-3.5 h-3.5" /> Resume Feed
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="mt-4 p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
            {error}
          </div>
        )}
      </div>

      {/* Main Grid: DAG Nodes (Left) & Causal Inference / Log (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: DAG Nodes */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              Investigation Workflow Execution DAG
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Budget: $0.42 / $2.00 USD
            </span>
          </div>

          <div className="space-y-3">
            {nodes.map((node, i) => (
              <InvestigationNodeCard key={node.node_id} node={node} isCurrent={i === 3} />
            ))}
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>
              All investigation evidence citations are sealed with cryptographic SHA-256 digests.
              Chain-of-thought is excluded to preserve audit privacy (INV-SEC-002).
            </span>
          </div>
        </div>

        {/* Right Column: Causal Chart & Live Terminal Stream */}
        <div className="space-y-6">
          <CausalImpactChart />

          {/* Live Terminal Log Stream */}
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 shadow-inner">
            <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800 text-xs text-slate-400">
              <span className="flex items-center gap-1.5 font-mono">
                <Terminal className="w-3.5 h-3.5 text-indigo-400" />
                Live Agent Telemetry Stream (SSE)
              </span>
              <span className="text-[10px] font-mono text-slate-500">
                {messages.length} events logged
              </span>
            </div>

            <div className="h-48 overflow-y-auto space-y-1.5 font-mono text-[11px] text-slate-300 pr-1">
              {messages.length === 0 ? (
                <div className="text-slate-500 py-4 text-center">
                  Waiting for live telemetry packets from worker...
                </div>
              ) : (
                messages.map((msg, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-slate-500 flex-shrink-0">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </span>
                    <span className="text-indigo-400 font-bold flex-shrink-0">
                      [{msg.event.toUpperCase()}]
                    </span>
                    <span className="text-slate-200">
                      {typeof msg.data === "object" ? JSON.stringify(msg.data) : msg.data}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
